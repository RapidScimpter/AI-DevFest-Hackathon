import pandas as pd
from .core import features, score

def prepare(event, history):
    """Strictly prior same-customer events. Never reads attack labels."""
    timestamp = pd.Timestamp(event['timestamp'])
    data = history.copy()
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    prior = data[(data.user_id == event['user_id']) & (data.timestamp < timestamp)].sort_values('timestamp')
    if len(prior) < 10:
        raise ValueError('At least 10 earlier customer transactions are needed for a behavioral profile.')
    baseline = prior.tail(50)
    hours = baseline.timestamp.dt.hour
    profile = {'median_amount':float(baseline.amount.median()),
        'district':str(baseline.district.mode().iloc[0]),
        'known_devices':baseline.device_id.unique().tolist(),
        'known_recipients':baseline.recipient_id.unique().tolist(),
        'start_hour':int(hours.quantile(.05)), 'end_hour':int(hours.quantile(.95))}
    enriched = {**event, 'hour':timestamp.hour,
                'transactions_10min':int((prior.timestamp >= timestamp - pd.Timedelta(minutes=10)).sum())}
    return enriched, profile, prior

def score_from_history(model, event, history):
    enriched, profile, prior = prepare(event, history)
    return score(model, enriched, profile), profile, prior
