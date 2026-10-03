"""Opt-in judge fixtures. All contacts are synthetic, non-dialable demo IDs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.reports import add_report
FIXTURES=[
 ('00000000001','Text message','Spam / unwanted contact','[SYNTHETIC DEMO] Repeated unwanted promotional messages.'),
 ('00000000002','Text message','Suspected scam / fraud','[SYNTHETIC DEMO] Your wallet is blocked. Send your OTP immediately to unlock it.'),
 ('00000000002','Call','Impersonation','[SYNTHETIC DEMO] Caller claimed to be wallet support and requested the customer PIN.'),
 ('00000000002','Text message','Suspected scam / fraud','[SYNTHETIC DEMO] You won a prize. Send money as a processing fee to claim it.'),
 ('00000000003','Text message','Impersonation','[SYNTHETIC DEMO] Install AnyDesk and share your screen to verify your wallet.'),
 ('00000000003','Call','Suspected scam / fraud','[SYNTHETIC DEMO] Caller requested remote access to fix an alleged account issue.')]
if __name__=='__main__':
 created=0
 for number,channel,category,text in FIXTURES:
  created+=int(add_report(number,channel,category,text)['created'])
 print(f'Added {created} synthetic reports. Re-running does not duplicate identical fixtures.')
 print('00000000001: one-report caution; 00000000002: three-report concern; 00000000003: two-report concern.')
 print('00000000004: no seeded reports (not a guarantee of safety). These are non-dialable demo identifiers.')
