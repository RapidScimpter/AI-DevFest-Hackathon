"""Train the calibrated LightGBM fraud model, sequence model, attack-pattern model and drift references.

Run:  python -m pipeline.train_fraud
"""
import json
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit
from app.config import ROOT, settings
from app.ml.drift import psi, reference_bins
from app.ml.features import FEATURES
from app.ml.sequence import SequenceModel

REVIEW, HIGH = settings.review_threshold, settings.high_threshold


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    total, table = 0.0, []
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
            table.append({'bin': f'{edges[b]:.1f}-{edges[b + 1]:.1f}', 'events': int(m.sum()),
                          'mean_predicted': float(p[m].mean()), 'observed_fraud_rate': float(y[m].mean())})
    return float(total), table


def at(y, p, thr):
    pred = p >= thr
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {'threshold': thr, 'precision': float(precision_score(y, pred, zero_division=0)), 'recall': float(recall_score(y, pred, zero_division=0)),
            'false_positive_rate': float(fp / (fp + tn)), 'confusion_matrix': [[int(tn), int(fp)], [int(fn), int(tp)]]}


def main():
    data = pd.read_csv(ROOT / 'data/transactions.csv')
    data = data[data.is_warmup == 0].reset_index(drop=True)
    data['attack_type'] = data.attack_type.fillna('')
    seqs = data.tokens.str.split().map(lambda s: [int(x) for x in s])

    rest, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42).split(data, groups=data.user_id))
    tr, cal = next(GroupShuffleSplit(n_splits=1, test_size=.20, random_state=7).split(data.iloc[rest], groups=data.user_id.iloc[rest]))
    train, calib = rest[tr], rest[cal]
    users = lambda idx: set(data.user_id.iloc[idx])
    assert users(train).isdisjoint(users(calib)) and users(train).isdisjoint(users(test)) and users(calib).isdisjoint(users(test))

    # Behavioural sequence model: fitted on legitimate training sequences only.
    legit_train = data.index.isin(train) & (data.is_fraud == 0)
    seq_model = SequenceModel.fit(seqs[legit_train])
    data['seq_nll'] = seqs.map(seq_model.nll)

    X, y = data[FEATURES], data.is_fraud.values
    model = LGBMClassifier(n_estimators=350, learning_rate=.05, num_leaves=31, min_child_samples=30, subsample=.8, subsample_freq=1,
                           colsample_bytree=.8, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1)
    model.fit(X.iloc[train], y[train])
    raw = model.predict_proba(X)[:, 1]
    # Calibration on customers the booster never saw, so the output can be read as a probability.
    iso = IsotonicRegression(out_of_bounds='clip', y_min=0, y_max=1).fit(raw[calib], y[calib])
    prob = iso.predict(raw)

    yt, pt = y[test], prob[test]
    ece_raw, _ = ece(yt, raw[test])
    ece_cal, table = ece(yt, pt)
    t = data.iloc[test]
    metrics = {
        'model': 'LightGBM gradient boosting + isotonic calibration',
        'events': {'train': len(train), 'calibration': len(calib), 'test': len(test), 'test_fraud': int(yt.sum()),
                   'customers': int(data.user_id.nunique())},
        'average_precision': float(average_precision_score(yt, pt)), 'roc_auc': float(roc_auc_score(yt, pt)),
        'calibration': {'brier_uncalibrated': float(brier_score_loss(yt, raw[test])), 'brier_calibrated': float(brier_score_loss(yt, pt)),
                        'ece_uncalibrated': ece_raw, 'ece_calibrated': ece_cal, 'reliability': table,
                        'base_rate': float(yt.mean())},
        'review': at(yt, pt, REVIEW), 'high': at(yt, pt, HIGH),
        'recall_by_attack': {k: {'events': int(len(g)), 'recall': float((g.p >= REVIEW).mean())}
                             for k, g in t.assign(p=pt)[t.is_fraud == 1].groupby('attack_type')},
        'false_positive_rate_by_segment': {k: float((g.p >= REVIEW).mean()) for k, g in t.assign(p=pt)[t.is_fraud == 0].groupby('segment')},
        'feature_importance': dict(sorted(zip(FEATURES, (model.booster_.feature_importance('gain') / model.booster_.feature_importance('gain').sum()).round(4).tolist()),
                                          key=lambda kv: -kv[1])),
        'note': 'Synthetic customers only; train, calibration and test customers are disjoint. Not production accuracy.',
    }
    # Baselines on the same held-out events.
    rf = RandomForestClassifier(n_estimators=160, max_depth=10, min_samples_leaf=8, random_state=42, n_jobs=-1).fit(X.iloc[train], y[train])
    rf_p = rf.predict_proba(X.iloc[test])[:, 1]
    rule = ((t.new_device == 1) & (t.amount_ratio > 3)).values
    metrics['baselines'] = {
        'random_forest': {'average_precision': float(average_precision_score(yt, rf_p)), 'brier': float(brier_score_loss(yt, rf_p)), **at(yt, rf_p, REVIEW)},
        'rule': {'rule': 'New device AND amount above 3 times prior median', **at(yt, rule.astype(float), .5)}}
    no_seq = [f for f in FEATURES if f != 'seq_nll']
    ablate = LGBMClassifier(**{**model.get_params()}).fit(X.iloc[train][no_seq], y[train])
    metrics['sequence_ablation'] = {'average_precision_without_seq_nll': float(average_precision_score(yt, ablate.predict_proba(X.iloc[test][no_seq])[:, 1])),
                                    'average_precision_with_seq_nll': float(average_precision_score(yt, model.predict_proba(X.iloc[test])[:, 1]))}

    # Attack-pattern model: which known pattern does a suspicious event resemble?
    fraud_train = train[y[train] == 1]
    fraud_test = test[y[test] == 1]
    type_model = LGBMClassifier(n_estimators=150, learning_rate=.08, num_leaves=15, min_child_samples=10, random_state=42, verbose=-1)
    type_model.fit(X.iloc[fraud_train], data.attack_type.iloc[fraud_train])
    metrics['attack_pattern_model'] = {'accuracy': float((type_model.predict(X.iloc[fraud_test]) == data.attack_type.iloc[fraud_test]).mean()),
                                       'classes': list(type_model.classes_)}

    # Drift references and an offline test against an attack pattern absent from training.
    reference = {'all': {f: reference_bins(X.iloc[train][f]) for f in FEATURES}, 'fraud': {f: reference_bins(X.iloc[fraud_train][f], 5) for f in FEATURES},
                 'score': reference_bins(prob[train])}
    drift = pd.read_csv(ROOT / 'data/drift_stream.csv')
    drift = drift[(drift.is_warmup == 0) & (drift.is_fraud == 1)].reset_index(drop=True)
    drift['seq_nll'] = drift.tokens.str.split().map(lambda s: seq_model.nll([int(x) for x in s]))
    dp = iso.predict(model.predict_proba(drift[FEATURES])[:, 1])
    psi_new = {f: psi(reference['fraud'][f], drift[f]) for f in FEATURES}
    psi_known = {f: psi(reference['fraud'][f], X.iloc[fraud_test][f]) for f in FEATURES}
    metrics['drift_simulation'] = {
        'scenario': 'Unseen "low and slow" pattern: tiny probe payments age a new device and recipient, then spaced mid-size transfers.',
        'events': int(len(drift)), 'recall_known_patterns': metrics['review']['recall'], 'recall_unseen_pattern': float((dp >= REVIEW).mean()),
        'mean_feature_psi_known': float(np.mean(list(psi_known.values()))), 'mean_feature_psi_unseen': float(np.mean(list(psi_new.values()))),
        'top_shifted_features': dict(sorted(psi_new.items(), key=lambda kv: -kv[1])[:6])}

    (ROOT / 'models').mkdir(exist_ok=True)
    joblib.dump({'model': model, 'calibrator': iso, 'type_model': type_model, 'features': FEATURES, 'reference': reference,
                 'seq': {'log_start': seq_model.log_start, 'log_trans': seq_model.log_trans}}, ROOT / 'models/fraud.joblib')
    (ROOT / 'models/splits.json').write_text(json.dumps({'test_users': sorted(users(test))}))
    (ROOT / 'models/metrics.json').write_text(json.dumps(metrics, indent=2))
    print(json.dumps({k: v for k, v in metrics.items() if k != 'feature_importance'}, indent=1))


if __name__ == '__main__':
    main()
