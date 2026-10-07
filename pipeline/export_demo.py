"""Pick one held-out synthetic customer per segment as a demo wallet history.

Run:  python -m pipeline.export_demo
"""
import json
import pandas as pd
from app.config import ROOT

COLUMNS = ['user_id', 'segment', 'timestamp', 'amount', 'balance_before', 'txn_type', 'device_id', 'recipient_id', 'district', 'failed_pin_attempts']


def main():
    data = pd.read_csv(ROOT / 'data/transactions.csv', usecols=COLUMNS + ['is_fraud'])
    test = set(json.loads((ROOT / 'models/splits.json').read_text())['test_users'])
    stats = data[data.user_id.isin(test)].groupby('user_id').agg(segment=('segment', 'first'), n=('amount', 'size'), fraud=('is_fraud', 'sum'),
                                                                   devices=('device_id', 'nunique'), districts=('district', 'nunique'))
    clean = stats[(stats.fraud == 0) & (stats.n >= 45) & (stats.devices <= 2) & (stats.districts == 1)]
    chosen = [clean[clean.segment == s].index[0] for s in ['student', 'salaried', 'merchant', 'remittance', 'freelancer', 'senior']]
    out = data[data.user_id.isin(chosen)][COLUMNS].groupby('user_id').tail(120)
    out.to_csv(ROOT / 'data/demo_history.csv', index=False)
    print(out.groupby(['user_id', 'segment']).size().to_string())


if __name__ == '__main__':
    main()
