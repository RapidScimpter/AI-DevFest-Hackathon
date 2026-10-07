"""Live scoring: calibrated fraud probability, likely attack pattern and readable signals."""
from functools import lru_cache
import joblib
import pandas as pd
from ..config import ROOT, settings
from .features import FEATURES, MIN_HISTORY, build
from .sequence import SequenceModel

PATTERNS = {'account_takeover': 'Account takeover', 'rapid_burst': 'Rapid transaction burst', 'social_engineering': 'Social-engineering (customer persuaded to pay)',
            'sim_swap': 'SIM swap / new-device cash-out', 'mule_smurfing': 'Mule account / smurfing'}


@lru_cache
def artifacts():
    art = joblib.load(ROOT / 'models/fraud.joblib')
    art['sequence'] = SequenceModel(art['seq']['log_start'], art['seq']['log_trans'])
    return art


def signals(f):
    out = []
    if f['new_device']: out.append('Device is unfamiliar')
    elif f['device_age'] <= 3: out.append('Device was first seen very recently')
    if f['new_recipient']: out.append('Recipient is unfamiliar')
    if f['location_change']: out.append('Location differs from the usual district')
    if f['unusual_hour']: out.append('Outside the usual hours for this wallet')
    if f['amount_ratio'] > 3: out.append(f"Amount is {f['amount_ratio']:.1f} times the recent median")
    if f['transactions_10min'] >= 3: out.append(f"{f['transactions_10min']} earlier transfers in the last 10 minutes")
    if f['new_recipients_60min'] >= 3: out.append(f"{f['new_recipients_60min']} new recipients within an hour")
    if f['balance_drain_ratio'] > .7: out.append('Transfer uses over 70% of the available balance')
    if f['recent_failed_pins']: out.append('Recent failed PIN attempts')
    if f['seq_nll'] > 5: out.append('The order of recent actions is unusual for this wallet')
    return out


def score(event: dict, prior: list[dict], trusted_devices=(), unavailable=()) -> dict:
    """`event` and `prior` use the keys documented in features.build. Never reads labels."""
    if len(prior) < MIN_HISTORY:
        amount, balance = float(event['amount']), float(event['balance_before'])
        return {'probability': None, 'band': 'Limited history', 'features': {'balance_drain_ratio': min(amount / balance, 1.0)},
                'signals': [f'Fewer than {MIN_HISTORY} earlier transactions: the behavioural model is not used yet'],
                'pattern': None, 'unavailable': list(unavailable), 'profile': {'events_used': len(prior)}}
    art = artifacts()
    feats, seq, profile = build(event, prior, trusted_devices)
    feats['seq_nll'] = art['sequence'].nll(seq)
    row = pd.DataFrame([feats], columns=FEATURES)
    prob = float(art['calibrator'].predict(art['model'].predict_proba(row)[:, 1])[0])
    band = 'High' if prob >= settings.high_threshold else 'Elevated' if prob >= settings.review_threshold else 'Low'
    pattern = None
    if prob >= settings.review_threshold:
        probs = art['type_model'].predict_proba(row)[0]
        best = probs.argmax()
        pattern = {'name': PATTERNS.get(art['type_model'].classes_[best], art['type_model'].classes_[best]), 'share': round(float(probs[best]), 2)}
    return {'probability': round(prob, 4), 'band': band, 'features': {k: round(float(v), 4) for k, v in feats.items()},
            'signals': signals(feats) or ['No selected warning signals'], 'pattern': pattern,
            'unavailable': list(unavailable), 'profile': {k: v for k, v in profile.items() if k != 'known_devices'}}
