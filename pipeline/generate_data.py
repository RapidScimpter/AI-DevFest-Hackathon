"""Synthetic MFS transaction generator.

Six customer segments with distinct habits, legitimate anomalies (travel, device
upgrades, large purchases, merchant bursts) and five labelled attack patterns.
A sixth, unseen pattern is written to a separate stream for drift evaluation.

Run:  python -m pipeline.generate_data
"""
import numpy as np
import pandas as pd
from app.config import ROOT
from app.ml.features import FEATURES, build

SEED, N_USERS, N_DRIFT_USERS, DAYS, WARMUP = 42, 3000, 200, 120, 20
START = pd.Timestamp('2026-05-01')
DISTRICTS = ['Dhaka', 'Chattogram', 'Sylhet', 'Rajshahi', 'Khulna', 'Barishal', 'Rangpur', 'Mymensingh']
# share, median range, sigma, events/day, peak hour, hour sd, regular recipients, P(new recipient), txn-type mix (send, cash_out, merchant_pay), P(legit burst)
SEGMENTS = {
    'student':    (.24, (120, 600),   .70, 1.5, 19, 3.5, (4, 10),  .06, (.55, .10, .35), .03),
    'salaried':   (.26, (700, 3000),  .75, 1.2, 15, 3.5, (5, 12),  .05, (.50, .20, .30), .03),
    'merchant':   (.14, (1500, 9000), .85, 3.0, 14, 3.0, (10, 30), .12, (.60, .30, .10), .15),
    'remittance': (.12, (2000, 9000), .60, 0.5, 12, 2.5, (2, 5),   .03, (.30, .60, .10), .01),
    'freelancer': (.12, (800, 6000), 1.10, 0.8, 21, 4.0, (4, 12),  .08, (.55, .25, .20), .04),
    'senior':     (.12, (300, 2500),  .60, 0.4, 11, 2.0, (2, 5),   .02, (.50, .35, .15), .01),
}
TYPES = ['send', 'cash_out', 'merchant_pay']
ATTACKS = {'account_takeover': .27, 'rapid_burst': .15, 'social_engineering': .26, 'sim_swap': .19, 'mule_smurfing': .13}
NOVEL = 'low_and_slow'


def episode(kind, rng, t, u, bal):
    """Return attack events as (timestamp, amount, type, device, recipient, district, failed_pins)."""
    m, home, own = u['median'], u['district'], u['device']
    away = str(rng.choice([d for d in DISTRICTS if d != home]))
    mule = lambda: f"X{rng.integers(10**7)}"
    night = lambda ts: ts.normalize() + pd.Timedelta(hours=int(rng.integers(1, 5)), minutes=int(rng.integers(60)))
    out = []
    if kind == 'account_takeover':
        if rng.random() < .5: t = night(t) + pd.Timedelta(days=1)
        dev, dist, r = f'A{rng.integers(10**7)}', away if rng.random() < .6 else home, mule()
        pins = int(rng.choice([0, 1, 2, 3], p=[.3, .2, .2, .3]))
        left = bal
        for k in range(int(rng.integers(1, 4))):
            amt = left * rng.uniform(.35, .9)
            out.append((t, amt, 'cash_out' if rng.random() < .4 else 'send', dev, r, dist, pins if k == 0 else 0))
            left -= amt; t += pd.Timedelta(minutes=int(rng.integers(1, 7)))
    elif kind == 'rapid_burst':
        dev = own if rng.random() < .5 else f'A{rng.integers(10**7)}'
        rs = [mule() for _ in range(int(rng.integers(1, 4)))]
        left = bal
        for _ in range(int(rng.integers(4, 10))):
            amt = min(m * rng.uniform(.8, 3), left * .5)
            if amt < 20: break
            out.append((t, amt, 'send', dev, str(rng.choice(rs)), home, 0))
            left -= amt; t += pd.Timedelta(seconds=int(rng.integers(20, 150)))
    elif kind == 'social_engineering':
        r = mule()
        amt = min(max(m * rng.uniform(3, 12), bal * rng.uniform(.3, .8)), bal * .98)
        out.append((t, amt, 'send', own, r, home, 0))
        if rng.random() < .25:
            out.append((t + pd.Timedelta(minutes=int(rng.integers(5, 20))), (bal - amt) * rng.uniform(.3, .8), 'send', own, r, home, 0))
    elif kind == 'sim_swap':
        if rng.random() < .6: t = t.normalize() + pd.Timedelta(hours=int(rng.integers(22, 27)), minutes=int(rng.integers(60)))
        dev, r, left = f'A{rng.integers(10**7)}', mule(), bal
        for k in range(int(rng.integers(1, 3))):
            amt = left * rng.uniform(.6, .98)
            out.append((t, amt, 'cash_out', dev, r, home, int(rng.random() < .3) if k == 0 else 0))
            left -= amt; t += pd.Timedelta(minutes=int(rng.integers(2, 10)))
    elif kind == 'mule_smurfing':
        left = bal + m * rng.uniform(15, 40)          # illicit funds arrive first
        for _ in range(int(rng.integers(5, 13))):
            amt = min(m * rng.uniform(1, 4), left * .6)
            out.append((t, amt, 'send', own, mule(), home, 0))
            left -= amt; t += pd.Timedelta(minutes=int(rng.integers(2, 10)))
    elif kind == NOVEL:
        dev, r = f'A{rng.integers(10**7)}', mule()
        for _ in range(2):                             # tiny probes that "age" the device and recipient
            out.append((t, m * rng.uniform(.05, .15), 'send', dev, r, home, 0))
            t += pd.Timedelta(minutes=int(rng.integers(20, 60)))
        for _ in range(int(rng.integers(3, 6))):
            out.append((t, min(m * rng.uniform(1.2, 2.2), bal * .3), 'send', dev, r, home, 0))
            t += pd.Timedelta(minutes=int(rng.integers(15, 40)))
    return [(ts, max(round(float(a), 2), 10.0), *rest) for ts, a, *rest in out]


def simulate(uid, rng, attack_kinds):
    names, weights = list(SEGMENTS), [s[0] for s in SEGMENTS.values()]
    seg = str(rng.choice(names, p=weights))
    _, med_rng, sigma, rate, peak, hsd, n_rcp, p_new, mix, p_burst = SEGMENTS[seg]
    u = {'median': float(rng.integers(*med_rng)), 'district': str(rng.choice(DISTRICTS, p=[.35, .2, .1, .08, .08, .06, .07, .06])),
         'device': f'D-{uid}'}
    regulars = [f'R-{uid}-{k}' for k in range(int(rng.integers(*n_rcp)))]
    zipf = np.array([1 / (k + 1) for k in range(len(regulars))])
    devices, second = [u['device']], f'D-{uid}-b'
    upgrade_day = int(rng.integers(30, DAYS)) if rng.random() < .15 else -1
    trip = (int(rng.integers(25, DAYS - 8)), int(rng.integers(3, 8)), str(rng.choice([d for d in DISTRICTS if d != u['district']]))) if rng.random() < .25 else None
    peak += rng.normal(0, 1.5)

    legit = []
    for day in range(DAYS):
        date = START + pd.Timedelta(days=day)
        payday = seg == 'salaried' and date.day in (25, 26, 27, 28, 1, 2)
        for _ in range(rng.poisson(rate * (1.6 if payday else 1))):
            hour = float(np.clip(rng.normal(peak, hsd), 6.5, 26.5)) % 24
            legit.append(date + pd.Timedelta(hours=hour))
    legit.sort()
    if len(legit) < WARMUP + 15:
        return None, seg
    # Legitimate bursts: a few follow-up payments within minutes.
    extra = []
    for ts in legit[WARMUP:]:
        if rng.random() < p_burst:
            t = ts
            for _ in range(int(rng.integers(2, 5))):
                t = t + pd.Timedelta(seconds=int(rng.integers(40, 200))); extra.append(t)
    times = sorted(legit + extra)
    slots = sorted(rng.choice(np.arange(WARMUP + 5, len(times)), size=len(attack_kinds), replace=False)) if attack_kinds else []

    rows, bal, n_new = [], u['median'] * rng.uniform(5, 40), 0

    def add(ts, amount, typ, dev, rcp, dist, pins, attack=''):
        nonlocal bal
        if bal < amount * 1.05:
            bal = amount + u['median'] * rng.uniform(2, 25)   # cash-in
        rows.append({'user_id': uid, 'segment': seg, 'timestamp': ts, 'amount': round(float(amount), 2),
                     'balance_before': round(float(bal), 2), 'txn_type': typ, 'device_id': dev, 'recipient_id': rcp,
                     'district': dist, 'failed_pin_attempts': pins, 'is_fraud': int(bool(attack)), 'attack_type': attack})
        bal -= amount

    last_attack_end = pd.Timestamp.min
    for i, ts in enumerate(times):
        if slots and i == slots[0]:
            slots.pop(0); kind = attack_kinds.pop(0)
            for ev in episode(kind, rng, ts, u, bal):
                amount = min(ev[1], bal * .99) if kind != 'mule_smurfing' else ev[1]
                add(ev[0], max(amount, 10), *ev[2:], attack=kind)
                last_attack_end = ev[0]
            continue
        if ts <= last_attack_end:
            continue
        day = (ts - START).days
        if upgrade_day >= 0 and day >= upgrade_day:
            dev = f'D-{uid}-new'
        else:
            dev = second if rng.random() < .03 else u['device']
        dist = trip[2] if trip and trip[0] <= day < trip[0] + trip[1] else u['district']
        if rng.random() < p_new:
            rcp = f'N-{uid}-{n_new}'; n_new += 1
            if rng.random() < .5: regulars.append(rcp); zipf = np.append(zipf, zipf[-1])
        else:
            rcp = str(rng.choice(regulars, p=zipf / zipf.sum()))
        amount = max(10, rng.lognormal(np.log(u['median']), sigma))
        if rng.random() < .02: amount *= rng.uniform(3, 8)        # large legitimate purchase
        pins = int(rng.choice([0, 1, 2], p=[.966, .03, .004]))
        add(ts, amount, str(rng.choice(TYPES, p=mix)), dev, rcp, dist, pins)
    rows.sort(key=lambda r: r['timestamp'])
    return rows, seg


def featurise(rows):
    out = []
    for j, ev in enumerate(rows):
        row = {**ev, 'transaction_id': f"{ev['user_id']}-{j}", 'is_warmup': int(j < WARMUP)}
        if j >= WARMUP:
            feats, seq, _ = build(ev, rows[:j])
            row.update(feats); row['tokens'] = ' '.join(map(str, seq))
        out.append(row)
    return out


def generate(n_users, prefix, rng, novel=False):
    kinds, probs = list(ATTACKS), list(ATTACKS.values())
    data, uid = [], 0
    while len({r['user_id'] for r in data}) < n_users:
        name = f'{prefix}{uid:04d}'; uid += 1
        if novel:
            attacks = [NOVEL]
        else:
            x = rng.random()
            attacks = [str(k) for k in rng.choice(kinds, size=2 if x < .08 else 1 if x < .42 else 0, p=probs)]
        rows, _ = simulate(name, rng, attacks)
        if rows:
            data.extend(featurise(rows))
    return pd.DataFrame(data)


def main():
    rng = np.random.default_rng(SEED)
    (ROOT / 'data').mkdir(exist_ok=True)
    main_df = generate(N_USERS, 'U', rng)
    main_df.to_csv(ROOT / 'data/transactions.csv', index=False)
    drift_df = generate(N_DRIFT_USERS, 'V', rng, novel=True)
    drift_df.to_csv(ROOT / 'data/drift_stream.csv', index=False)
    live = main_df[main_df.is_warmup == 0]
    print(f'{len(main_df):,} events for {main_df.user_id.nunique()} customers; fraud rate after warm-up {live.is_fraud.mean():.2%}')
    print(live.groupby('segment').size().to_string()); print(live[live.is_fraud == 1].groupby('attack_type').size().to_string())
    print(f'Drift stream: {len(drift_df):,} events, {int(drift_df.is_fraud.sum())} unseen-pattern fraud events')
    assert set(FEATURES) - {'seq_nll'} <= set(main_df.columns)


if __name__ == '__main__':
    main()
