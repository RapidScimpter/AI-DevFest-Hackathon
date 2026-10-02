def investigate(features, context):
    """Demo decision policy, separate from the ML score. Context is never a label."""
    travel = context.get('travel_verified', False)
    device = context.get('device_verified', False)
    unresolved = []
    if features['location_change'] and not travel: unresolved.append('Confirm travel with the customer through a trusted channel')
    if features['new_device'] and not device: unresolved.append('Verify the new device through an existing trusted channel')
    strong = []
    if features['failed_pin_attempts'] >= 3: strong.append('Repeated failed PIN attempts')
    if features['transactions_10min'] >= 3: strong.append('Rapid transfer activity')
    if features['balance_drain_ratio'] > .7: strong.append('Large balance withdrawal')
    if features['new_recipient'] and features['amount_ratio'] > 3: strong.append('Large transfer to an unfamiliar recipient')
    if strong:
        status = 'Further investigation needed'
        action = 'Review transaction details and verify customer authorization'
    elif unresolved:
        status = 'Context check needed'
        action = 'Confirm the explanation before deciding'
    elif features['location_change'] or features['new_device']:
        status = 'Legitimate context verified (demo)'
        action = 'Continue normal security checks'
    else:
        status = 'Routine activity'
        action = 'Continue normal security checks'
    return {'status':status, 'action':action, 'follow_up':strong + unresolved,
            'explanations':(['Travel verified through a trusted channel (simulated)'] if travel else []) +
                           (['New device verified through a trusted channel (simulated)'] if device else [])}
