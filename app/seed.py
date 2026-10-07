"""Create demo accounts, wallet histories and sample reports.

Run:  python -m app.seed            (safe to run again; existing accounts are kept)
"""
import pandas as pd
from sqlalchemy import select
from . import audit, reports
from .config import ROOT
from .db import SessionLocal, init_db
from .models import Consent, Event, User, Wallet
from .security import hash_secret
from .services.wallet import local_now

CUSTOMER_PASSWORD, CUSTOMER_PIN = 'Demo#2026', '2468'
STAFF = [('analyst', 'Demo Analyst', 'analyst', 'Analyst#2026'), ('admin', 'Demo Admin', 'admin', 'Admin#2026!')]
NAMES = {'student': 'Tanvir (student)', 'salaried': 'Nusrat (salaried)', 'merchant': 'Karim Store (merchant)',
         'remittance': 'Rahima (remittance family)', 'freelancer': 'Arif (freelancer)', 'senior': 'Abdul (senior)'}
BALANCE = {'student': 20_000, 'salaried': 80_000, 'merchant': 300_000, 'remittance': 120_000, 'freelancer': 150_000, 'senior': 60_000}
SAMPLE_REPORTS = [('00000000001', 'Call', 'Impersonation', 'Caller claimed to be wallet support and asked for my OTP.'),
                  ('00000000002', 'Call', 'Suspected scam / fraud', 'Caller said my account was blocked and asked me to send money.'),
                  ('00000000002', 'Text message', 'Suspected scam / fraud', 'Your account is suspended. Send 500 taka processing fee to reopen it.'),
                  ('00000000002', 'Text message', 'Impersonation', 'Message pretending to be from head office asking for PIN.')]


def main():
    init_db()
    history = pd.read_csv(ROOT / 'data/demo_history.csv', parse_dates=['timestamp'])
    history['timestamp'] = history.timestamp.dt.floor('s')
    with SessionLocal() as db:
        for login, name, role, password in STAFF:
            if not db.scalar(select(User).where(User.login == login)):
                db.add(User(login=login, name=name, role=role, password_hash=hash_secret(password)))
        order = ['student', 'salaried', 'merchant', 'remittance', 'freelancer', 'senior']
        for i, segment in enumerate(order, start=1):
            phone = f'+88017000000{i:02d}'
            if db.scalar(select(User).where(User.login == phone)):
                continue
            rows = history[history.segment == segment].sort_values('timestamp')
            user = User(login=phone, name=NAMES[segment], role='customer', segment=segment,
                        password_hash=hash_secret(CUSTOMER_PASSWORD), pin_hash=hash_secret(CUSTOMER_PIN))
            db.add(user); db.flush()
            db.add(Wallet(user_id=user.id, balance=BALANCE[segment] * 100))
            db.add_all(Consent(user_id=user.id, permission=p, granted=p == 'device') for p in ('device', 'location', 'camera'))
            # Shift the synthetic timeline by whole days so it ends yesterday and keeps its time-of-day pattern.
            shift = pd.Timedelta(days=(pd.Timestamp(local_now()).normalize() - rows.timestamp.max().normalize()).days - 1)
            db.add_all(Event(user_id=user.id, timestamp=(r.timestamp + shift).to_pydatetime(), amount=float(r.amount), txn_type=r.txn_type,
                             device_id=r.device_id, recipient_id=r.recipient_id, district=r.district, failed_pin_attempts=int(r.failed_pin_attempts))
                       for r in rows.itertuples())
            audit.record(db, None, 'seed.customer_created', 'user', user.id, {'segment': segment, 'events': len(rows)})
        for number, channel, category, evidence in SAMPLE_REPORTS:
            reports.add_report(db, number, channel, category, evidence)
        db.commit()
    print('Demo accounts ready.\n  Customers: 01700000001 … 01700000006   password', CUSTOMER_PASSWORD, '  wallet PIN', CUSTOMER_PIN)
    print('  Staff: analyst /', STAFF[0][3], '   admin /', STAFF[1][3])
    print('  Reported test numbers: 00000000001 (1 report), 00000000002 (3 reports). Non-dialable demo identifiers.')


if __name__ == '__main__':
    main()
