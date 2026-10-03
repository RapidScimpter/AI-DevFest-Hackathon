import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from src.decision import assess
from src.wallet_store import request_transfer,transition,summary
f={'new_device':0,'location_change':0,'new_recipient':0,'amount_ratio':1,'failed_pin_attempts':0,'transactions_10min':0,'balance_drain_ratio':.1,'unusual_hour':0}
low={'score':5,'features':f,'signals':[]}
high={**low,'score':75}
with patch('src.decision.lookup_reports',return_value={'number_reports':[]}):
 assert not assess(low,'01712345678')['requires_review']
 assert assess(high,'01712345678')['requires_review']
with patch('src.decision.lookup_reports',return_value={'number_reports':[{},{}]}):
 assert assess(low,'01712345678')['requires_review']
with tempfile.TemporaryDirectory() as t:
 db=Path(t)/'wallet.db'
 event={'amount':500,'recipient_id':'01712345678','timestamp':'2026-10-03T15:00:00'}
 with patch('src.decision.lookup_reports',return_value={'number_reports':[]}):
  tid=request_transfer('U1',event,low,{},db)
 # New reports arriving after submission must be considered at confirmation.
 with patch('src.decision.lookup_reports',return_value={'number_reports':[{},{}]}):
  assert transition(tid,'U1','confirm',db=db)=='Under review'
  assert summary('U1',db)['balance']==30000
  assert summary('U1',db)['reserved']==500
 print('ML routing, repeated-report concerns and confirmation bypass protection passed.')
