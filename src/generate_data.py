import json
import numpy as np
import pandas as pd
from core import ROOT, features

rng = np.random.default_rng(42)
profiles, rows = {}, []
for i in range(600):
    uid = f'U{i:04d}'
    profile = {'median_amount': int(rng.integers(300, 2500)),
               'district': str(rng.choice(['Dhaka', 'Sylhet', 'Chattogram', 'Rajshahi'])),
               'known_devices': [f'D{i}'], 'known_recipients': [f'R{i}-{j}' for j in range(4)],
               'start_hour': 7, 'end_hour': 23}
    profiles[uid] = profile
    # Profiles represent an earlier, trusted enrollment period. They do not use future events.
    for j in range(40):
        attack = bool(rng.random() < .08)
        # Legitimate travel/new phones and subtle attacks create overlapping classes.
        unusual = rng.random() < (.68 if attack else .08)
        median = profile['median_amount']
        amount = max(10, round(float(rng.lognormal(np.log(median), .8)) * (2.2 if attack else 1), 2))
        balance = max(amount, float(rng.uniform(3000, 35000)))
        event = {'amount': amount, 'balance_before': balance,
                 'device_id': 'NEW' if rng.random() < (.70 if attack else .08) else profile['known_devices'][0],
                 'recipient_id': 'NEW' if rng.random() < (.75 if attack else .18) else profile['known_recipients'][0],
                 'district': 'Other' if unusual else profile['district'],
                 'hour': int(rng.integers(0, 7)) if rng.random() < (.40 if attack else .05) else int(rng.integers(7, 24)),
                 'transactions_10min': int(rng.poisson(2.5 if attack else .4)),
                 'failed_pin_attempts': int(rng.poisson(1.2 if attack else .08))}
        rows.append({'user_id': uid, 'transaction_id': f'{uid}-{j}', **event,
                     **features(event, profile), 'is_account_takeover': int(attack)})
(ROOT / 'data').mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(ROOT / 'data/transactions.csv', index=False)
(ROOT / 'data/profiles.json').write_text(json.dumps(profiles, indent=2))
print(f'Created {len(rows)} events and {len(profiles)} synthetic profiles.')
