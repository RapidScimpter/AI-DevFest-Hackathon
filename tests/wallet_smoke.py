import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
from src.wallet_store import summary,request_transfer,transition
with tempfile.TemporaryDirectory() as temp:
 db=Path(temp)/'wallet.sqlite3'
 event={'amount':500,'recipient_id':'R1','timestamp':'2026-10-03T10:00:00'}
 request=request_transfer('U1',event,{}, {'follow_up':[]},db)
 assert summary('U1',db)['available']==29500
 assert transition(request,'U1','confirm',db=db)=='Completed'
 try:transition(request,'U1','confirm',db=db);raise AssertionError('Duplicate settlement accepted')
 except ValueError:pass
 assert summary('U1',db)['balance']==29500
 held=request_transfer('U1',event,{}, {'follow_up':['Review']},db)
 assert transition(held,'U1','confirm',db=db)=='Under review'
 transition(held,'U1','reject','Review complete',db)
 assert summary('U1',db)['available']==29500
 try:request_transfer('U1',{**event,'amount':40000},{},{'follow_up':[]},db);raise AssertionError('Overspending accepted')
 except ValueError:pass
 print('Wallet reservation, settlement, duplicate-action and overspending checks passed.')
