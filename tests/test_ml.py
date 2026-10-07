import json
from datetime import datetime, timedelta
from app.config import ROOT
from app.ml.drift import psi, reference_bins
from app.ml.features import FEATURES, build
from app.ml.scoring import score


def history(n=30):
    start = datetime(2026, 9, 1, 10)
    return [{'timestamp': start + timedelta(hours=7 * i), 'amount': 500 + 10 * (i % 5), 'txn_type': 'send', 'device_id': 'D1',
             'recipient_id': f'R{i % 4}', 'district': 'Dhaka', 'failed_pin_attempts': 0} for i in range(n)]


def test_features_use_only_the_past():
    rows = history()
    event = {**rows[20], 'balance_before': 20000}
    feats, seq, profile = build(event, rows[:20])
    poisoned = [{**r, 'amount': 999999, 'device_id': 'EVIL'} for r in rows[20:]]
    assert build(event, rows[:20])[0] == feats and all(r['timestamp'] >= event['timestamp'] for r in poisoned)
    assert feats['new_device'] == 0 and feats['new_recipient'] == 0 and len(seq) == 5
    assert set(feats) | {'seq_nll'} == set(FEATURES)


def test_burst_and_takeover_score_higher_than_routine():
    rows = history()
    t = rows[-1]['timestamp'] + timedelta(hours=7)
    routine = score({'timestamp': t, 'amount': 520, 'balance_before': 20000, 'txn_type': 'send', 'device_id': 'D1', 'recipient_id': 'R1',
                     'district': 'Dhaka', 'failed_pin_attempts': 0}, rows)
    takeover = score({'timestamp': t.replace(hour=3), 'amount': 18000, 'balance_before': 20000, 'txn_type': 'cash_out', 'device_id': 'X', 'recipient_id': 'M',
                      'district': 'Sylhet', 'failed_pin_attempts': 3}, rows)
    burst = rows + [{'timestamp': t + timedelta(seconds=40 * i), 'amount': 900, 'txn_type': 'send', 'device_id': 'D1', 'recipient_id': f'M{i}',
                     'district': 'Dhaka', 'failed_pin_attempts': 0} for i in range(5)]
    rapid = score({'timestamp': t + timedelta(seconds=240), 'amount': 900, 'balance_before': 15000, 'txn_type': 'send', 'device_id': 'D1',
                   'recipient_id': 'M9', 'district': 'Dhaka', 'failed_pin_attempts': 0}, burst)
    assert routine['probability'] < .05 < .7 <= takeover['probability']
    assert rapid['probability'] >= .3 and rapid['pattern']


def test_calibration_and_drift_are_reported():
    m = json.loads((ROOT / 'models/metrics.json').read_text())
    assert m['calibration']['ece_calibrated'] < .01
    assert m['average_precision'] > m['baselines']['random_forest']['average_precision']
    assert m['drift_simulation']['mean_feature_psi_unseen'] > .25 > m['drift_simulation']['mean_feature_psi_known']
    ref = reference_bins(range(1000))
    assert psi(ref, range(1000)) < .01 < .25 < psi(ref, range(800, 1000))
