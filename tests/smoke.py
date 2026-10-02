import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import joblib
from src.core import ROOT
from src.history import prepare, score_from_history
from src.review import investigate

history=pd.read_csv(ROOT/'data/transactions.csv')
u=history[history.user_id=='U0000']
event=u.iloc[35].to_dict()
enriched,profile,prior=prepare(event,history)
assert all(pd.to_datetime(prior.timestamp)<pd.Timestamp(event['timestamp']))
changed=history.copy()
mask=pd.to_datetime(changed.timestamp)>=pd.Timestamp(event['timestamp'])
changed.loc[mask,'amount']=999999
changed['is_account_takeover']=1-changed.is_account_takeover
other,other_profile,_=prepare(event,changed)
assert profile==other_profile
assert enriched['transactions_10min']==other['transactions_10min']
# Editing a submitted count must not override the actual timestamp-derived count.
assert prepare({**event,'transactions_10min':999},history)[0]['transactions_10min']==enriched['transactions_10min']
travel={'new_device':1,'location_change':1,'failed_pin_attempts':0,'transactions_10min':0,'balance_drain_ratio':.1,'new_recipient':0,'amount_ratio':1}
assert investigate(travel,{'travel_verified':True,'device_verified':True})['status']=='Legitimate context verified (demo)'
assert investigate({**travel,'failed_pin_attempts':3},{'travel_verified':True,'device_verified':True})['status']=='Further investigation needed'
model=joblib.load(ROOT/'models/model.joblib')
result,_,_=score_from_history(model,event,history)
assert 0<=result['score']<=100
print('Passed: prior-only history, future/label isolation, automatic counts, context policy and scoring.')
