import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
import pandas as pd
from src.core import ROOT, features
from src.history import prepare

rng = np.random.default_rng(42)
rows, profiles = [], {}
for i in range(200):
    uid=f'U{i:04d}'
    median=int(rng.integers(300,2500))
    district=str(rng.choice(['Dhaka','Sylhet','Chattogram','Rajshahi']))
    timestamp=pd.Timestamp('2026-09-01 09:00:00')
    user_rows=[]
    for j in range(90):
        attack=j>=20 and rng.random()<.08
        burst = j>=20 and rng.random() < (.65 if attack else .12)
        timestamp += pd.Timedelta(minutes=int(rng.integers(1,4) if burst else rng.integers(20,200)))
        if not 7<=timestamp.hour<=23 and rng.random() > (.30 if attack else .04): timestamp=timestamp.normalize()+pd.Timedelta(days=1,hours=9)
        unusual = j>=20 and rng.random()<(.65 if attack else .10)
        amount=max(10,round(float(rng.lognormal(np.log(median),.75))*(2.8 if attack else 1),2))
        event={'user_id':uid,'transaction_id':f'{uid}-{j}', 'timestamp':timestamp.isoformat(),
            'amount':amount,'balance_before':max(amount,float(rng.uniform(3000,35000))),
            'device_id':'NEW_DEVICE' if j>=20 and rng.random()<(.7 if attack else .08) else f'D{i}',
            'recipient_id':'NEW_RECIPIENT' if j>=20 and rng.random()<(.7 if attack else .12) else f'R{i}-{int(rng.integers(0,4))}',
            'district':'Other' if unusual else district,
            'failed_pin_attempts':int(rng.poisson(1.4 if attack else .08)),
            'is_account_takeover':int(attack),'is_warmup':int(j<20)}
        if j>=20:
            enriched,profile,_=prepare(event,pd.DataFrame(user_rows))
            event.update(features(enriched,profile))
        user_rows.append(event)
    rows.extend(user_rows)
    next_event={**user_rows[-1],'timestamp':(timestamp+pd.Timedelta(minutes=30)).isoformat()}
    _,profile,_=prepare(next_event,pd.DataFrame(user_rows));profiles[uid]=profile
(ROOT/'data').mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(ROOT/'data/transactions.csv',index=False)
(ROOT/'data/profiles.json').write_text(json.dumps(profiles,indent=2))
print(f'Created {len(rows)} timestamped events for {len(profiles)} customers (20 warm-up events each).')
