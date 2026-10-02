from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ['amount_ratio', 'new_device', 'new_recipient', 'location_change',
            'unusual_hour', 'transactions_10min', 'balance_drain_ratio', 'failed_pin_attempts']

def features(event, profile):
    amount, balance = float(event['amount']), float(event['balance_before'])
    if amount <= 0 or balance <= 0 or amount > balance:
        raise ValueError('Amount must be positive and no greater than the available balance.')
    return {
        'amount_ratio': amount / max(float(profile['median_amount']), 1),
        'new_device': int(event['device_id'] not in profile['known_devices']),
        'new_recipient': int(event['recipient_id'] not in profile['known_recipients']),
        'location_change': int(event['district'] != profile['district']),
        'unusual_hour': int(not profile['start_hour'] <= int(event['hour']) <= profile['end_hour']),
        'transactions_10min': int(event['transactions_10min']),
        'balance_drain_ratio': amount / balance,
        'failed_pin_attempts': int(event['failed_pin_attempts']),
    }

def score(model, event, profile):
    row = features(event, profile)
    value = float(model.predict_proba(pd.DataFrame([row], columns=FEATURES))[0, 1])
    band = 'High' if value >= .70 else 'Medium' if value >= .40 else 'Low'
    reasons = []
    for key, text in [('new_device', 'Device is unfamiliar'), ('new_recipient', 'Recipient is unfamiliar'),
                      ('location_change', 'District differs from the profile'), ('unusual_hour', 'Outside usual hours')]:
        if row[key]: reasons.append(text)
    if row['amount_ratio'] > 3: reasons.append(f"Amount is {row['amount_ratio']:.1f} times the historical median")
    if row['transactions_10min'] >= 3: reasons.append('Several recent transactions')
    if row['balance_drain_ratio'] > .7: reasons.append('Transfer uses over 70% of available balance')
    if row['failed_pin_attempts']: reasons.append('Recent failed PIN attempts')
    return {'score': round(value * 100, 1), 'band': band,
            'action': 'Simulated step-up verification' if band != 'Low' else 'Continue with normal checks',
            'signals': reasons or ['No selected warning signals'], 'features': row}
