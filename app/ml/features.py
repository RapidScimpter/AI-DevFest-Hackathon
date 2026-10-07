"""Feature engineering shared by training and live scoring.

Every feature is derived from the current event plus strictly earlier events of the
same customer. Labels are never read here.
"""
from __future__ import annotations

import math
from collections import Counter
from statistics import median

FEATURES = [
    'amount_ratio', 'log_amount_z', 'balance_drain_ratio', 'amount_trend',
    'new_device', 'device_age', 'new_recipient', 'recipient_count',
    'location_change', 'unusual_hour', 'hour_rarity',
    'failed_pin_attempts', 'recent_failed_pins',
    'transactions_1min', 'transactions_10min', 'transactions_60min',
    'amount_60min_ratio', 'new_recipients_60min', 'small_run', 'gap_ratio',
    'is_cash_out', 'seq_nll',
]
WINDOW = 50          # earlier events used for the behavioural profile
MIN_HISTORY = 10     # below this the behavioural model is not used
SEQ_LEN = 5          # tokens (4 earlier + current) scored by the sequence model
N_TOKENS = 48


def token(amount, med, gap_s, new_rcp, new_dev):
    """Discretise one event into a behavioural state for sequence modelling."""
    a = 0 if amount < .5 * med else 1 if amount < 2 * med else 2 if amount < 4 * med else 3
    g = 0 if gap_s < 180 else 1 if gap_s < 3600 else 2
    return ((a * 3 + g) * 2 + int(new_rcp)) * 2 + int(new_dev)


def build(event: dict, prior: list[dict], trusted_devices=()) -> tuple[dict, list[int], dict]:
    """Return (features without seq_nll, token sequence, profile).

    `prior` must be ascending by timestamp and contain only earlier events.
    """
    base = prior[-WINDOW:]
    if len(base) < MIN_HISTORY:
        raise ValueError(f'At least {MIN_HISTORY} earlier transactions are needed for a behavioural profile.')
    ts, amount = event['timestamp'], float(event['amount'])
    balance = float(event['balance_before'])
    if amount <= 0 or balance <= 0:
        raise ValueError('Amount and balance must be positive.')

    amounts = [float(p['amount']) for p in base]
    med = max(median(amounts), 1.0)
    logs = [math.log(max(a, 1)) for a in amounts]
    mu = sum(logs) / len(logs)
    sd = math.sqrt(sum((x - mu) ** 2 for x in logs) / len(logs))
    home = Counter(p['district'] for p in base).most_common(1)[0][0]
    dev_counts = Counter(p['device_id'] for p in base)
    rcp_counts = Counter(p['recipient_id'] for p in base)
    known_dev = set(dev_counts) | set(trusted_devices)
    hour = ts.hour
    near = sum(1 for p in base if min((p['timestamp'].hour - hour) % 24, (hour - p['timestamp'].hour) % 24) <= 1)
    hour_rarity = near / len(base)
    gaps = [(base[i]['timestamp'] - base[i - 1]['timestamp']).total_seconds() for i in range(1, len(base))]
    med_gap = max(median(gaps), 60.0)
    gap = max((ts - base[-1]['timestamp']).total_seconds(), 0.0)

    tx1 = tx10 = tx60 = 0
    sum60 = amount
    window_rcp = {event['recipient_id']}
    cut = len(base)
    for i in range(len(base) - 1, -1, -1):
        delta = (ts - base[i]['timestamp']).total_seconds()
        if delta > 3600:
            break
        cut = i
        tx60 += 1
        sum60 += amounts[i]
        window_rcp.add(base[i]['recipient_id'])
        tx10 += delta <= 600
        tx1 += delta <= 60
    older_rcp = {p['recipient_id'] for p in base[:cut]}
    small_run = 0
    for i in range(len(base) - 1, cut - 1, -1):
        if amounts[i] < 4 * med and base[i]['recipient_id'] not in older_rcp:
            small_run += 1
        else:
            break
    last3 = amounts[-3:]

    new_dev = int(event['device_id'] not in known_dev)
    new_rcp = int(event['recipient_id'] not in rcp_counts)
    feats = {
        'amount_ratio': amount / med,
        'log_amount_z': (math.log(max(amount, 1)) - mu) / (sd + .25),
        'balance_drain_ratio': min(amount / balance, 1.0),
        'amount_trend': amount / max(sum(last3) / len(last3), 1.0),
        'new_device': new_dev,
        'device_age': 0 if new_dev else dev_counts.get(event['device_id'], WINDOW),
        'new_recipient': new_rcp,
        'recipient_count': rcp_counts.get(event['recipient_id'], 0),
        'location_change': int(event['district'] != home),
        'unusual_hour': int(hour_rarity < .03),
        'hour_rarity': hour_rarity,
        'failed_pin_attempts': int(event.get('failed_pin_attempts', 0)),
        'recent_failed_pins': int(event.get('failed_pin_attempts', 0)) + sum(int(p.get('failed_pin_attempts', 0)) for p in base[-5:]),
        'transactions_1min': tx1, 'transactions_10min': tx10, 'transactions_60min': tx60,
        'amount_60min_ratio': sum60 / med,
        'new_recipients_60min': len(window_rcp - older_rcp),
        'small_run': small_run,
        'gap_ratio': math.log10((gap + 1) / med_gap),
        'is_cash_out': int(event.get('txn_type') == 'cash_out'),
    }

    # Behavioural state sequence: the four most recent earlier events, then this one.
    first_rcp, first_dev = {}, {}
    for i, p in enumerate(base):
        first_rcp.setdefault(p['recipient_id'], i)
        first_dev.setdefault(p['device_id'], i)
    seq = []
    for i in range(max(1, len(base) - (SEQ_LEN - 1)), len(base)):
        p = base[i]
        seq.append(token(amounts[i], med, gaps[i - 1],
                         first_rcp[p['recipient_id']] == i, first_dev[p['device_id']] == i))
    seq.append(token(amount, med, gap, new_rcp, new_dev))
    profile = {'median_amount': med, 'district': home, 'known_devices': sorted(known_dev),
               'known_recipients': len(rcp_counts), 'events_used': len(base)}
    return feats, seq, profile
