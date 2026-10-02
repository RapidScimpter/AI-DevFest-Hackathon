import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, confusion_matrix
from core import ROOT, FEATURES

data = pd.read_csv(ROOT / 'data/transactions.csv')
if 'is_warmup' not in data: raise ValueError('Regenerate timestamped data before training.')
data = data[data.is_warmup == 0].reset_index(drop=True)
train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42).split(data, groups=data.user_id))
assert set(data.iloc[train].user_id).isdisjoint(data.iloc[test].user_id)
model = RandomForestClassifier(n_estimators=160, max_depth=10, min_samples_leaf=8,
                               random_state=42, n_jobs=-1)
model.fit(data.iloc[train][FEATURES], data.iloc[train].is_account_takeover)
y = data.iloc[test].is_account_takeover
prob = model.predict_proba(data.iloc[test][FEATURES])[:, 1]
# Prototype review threshold: deliberately fixed, not optimized using test labels.
pred = prob >= .40
tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
metrics = {'precision': precision_score(y, pred, zero_division=0),
           'recall': recall_score(y, pred, zero_division=0), 'f1': f1_score(y, pred, zero_division=0),
           'pr_auc_average_precision': average_precision_score(y, prob),
           'false_positive_rate': float(fp / (fp + tn)),
           'confusion_matrix': [[int(tn), int(fp)], [int(fn), int(tp)]],
           'test_events': len(test), 'review_threshold': .40,
           'note': 'Strictly prior history; held-out synthetic users only. Not production accuracy.'}
baseline = ((data.iloc[test].new_device == 1) & (data.iloc[test].amount_ratio > 3)).astype(int)
bn, bf, bfn, btp = confusion_matrix(y, baseline, labels=[0,1]).ravel()
metrics['rule_baseline'] = {'rule':'New device AND amount above 3 times prior median',
 'precision':precision_score(y,baseline,zero_division=0), 'recall':recall_score(y,baseline,zero_division=0),
 'false_positive_rate':float(bf/(bf+bn))}
(ROOT / 'models').mkdir(exist_ok=True)
joblib.dump(model, ROOT / 'models/model.joblib')
(ROOT / 'models/metrics.json').write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
