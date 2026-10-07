"""Decision policy. Combines the calibrated model probability, behavioural rules and
unverified number reports. Kept separate from the model so it can be reviewed and changed."""
from .config import settings


def assess(analysis: dict, report_count: int = 0) -> dict:
    f = analysis.get('features', {})
    prob = analysis.get('probability')
    reasons, observations = [], []
    if prob is not None and prob >= settings.review_threshold:
        text = f'This transfer looks {min(prob, .99):.0%} likely to be fraud, based on how you normally use your wallet.'
        if analysis.get('pattern'):
            text += f" It matches a known pattern: {analysis['pattern']['name'].lower()}."
        reasons.append(text)
    if f.get('recent_failed_pins', 0) >= 3: reasons.append('The wrong PIN was entered several times just before this')
    if f.get('transactions_10min', 0) >= 3: reasons.append('Several transfers were made within a few minutes')
    if f.get('balance_drain_ratio', 0) > .7 and (prob is None or f.get('new_recipient')): reasons.append('It sends most of your money to someone you have not paid before')
    if f.get('new_recipient') and f.get('amount_ratio', 0) > 3 and f.get('new_device'): reasons.append('A large amount is going to a new person from a device your wallet does not recognise')
    if f.get('new_device') and f.get('location_change'): reasons.append('The request comes from an unknown device in a place you do not usually use')
    if report_count >= 2:
        reasons.append(f'Other people have reported this number {report_count} times for scams or spam (reports are not verified)')
    elif report_count == 1:
        observations.append('One person has reported this number. Check who you are really paying.')
    if f.get('amount_ratio', 0) > 3: observations.append(f"This is about {f['amount_ratio']:.0f} times more than you usually send.")
    if f.get('new_recipient'): observations.append('You have not paid this person before.')
    if f.get('new_device') and not f.get('location_change'): observations.append('You are using a device your wallet has not seen before.')
    if prob is None: observations.append('Your wallet is new, so only basic checks apply for now.')
    for name in analysis.get('unavailable', []):
        observations.append(f'{name.capitalize()} check skipped: you have not allowed that permission.')
    level = 'danger' if (prob or 0) >= settings.high_threshold or len(reasons) >= 2 else 'caution' if reasons or observations else 'safe'
    return {'status': 'Review required' if reasons else 'Caution: check details' if observations else 'No elevated concern detected',
            'level': level, 'requires_review': bool(reasons), 'follow_up': list(dict.fromkeys(reasons)), 'observations': observations,
            'report_count': report_count, 'probability': prob,
            'source_note': 'Calibrated behavioural model plus a separate rule and report policy. Reports are unverified submissions.'}
