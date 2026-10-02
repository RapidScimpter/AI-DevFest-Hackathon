import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
import json
import joblib
from src.core import ROOT, score
p = json.loads((ROOT / 'data/profiles.json').read_text())['U0000']
m = joblib.load(ROOT / 'models/model.joblib')
e = dict(amount=p['median_amount'], balance_before=30000, device_id=p['known_devices'][0],
         recipient_id=p['known_recipients'][0], district=p['district'], hour=14,
         transactions_10min=0, failed_pin_attempts=0)
normal = score(m, e, p)
attack = score(m, {**e, 'amount': 20000, 'device_id':'UNKNOWN', 'recipient_id':'UNKNOWN',
                  'district':'Other', 'hour':2, 'transactions_10min':4, 'failed_pin_attempts':3}, p)
assert attack['score'] > normal['score']
try:
    score(m, {**e, 'amount':40000}, p)
    raise AssertionError('Invalid balance accepted')
except ValueError: pass
print('Smoke checks passed:', normal['score'], attack['score'])
