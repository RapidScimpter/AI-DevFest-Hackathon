from .review import investigate
from .reports import lookup_reports

def assess(analysis, recipient):
    """Explicit policy combines ML and unverified reports without changing ML score."""
    f=analysis.get('features',{})
    base=investigate(f,{}) if f else {'follow_up':[],'explanations':[]}
    reasons=list(base['follow_up'])
    observations=[]
    model_score=float(analysis.get('score',0))
    if model_score>=40:
        reasons.append('The behavioral model detected an elevated pattern of concern. Additional review is required.')
    if f.get('amount_ratio',0)>3: observations.append(f"This amount is {f['amount_ratio']:.1f} times your recent median transfer.")
    if f.get('new_recipient'):observations.append('This recipient has not appeared in your recent transfer history.')
    if f.get('transactions_10min',0):observations.append(f"You have {f['transactions_10min']} earlier transfer attempts in the last 10 minutes.")
    try: reports=lookup_reports(recipient)['number_reports']
    except ValueError:reports=[]  # Legacy internal saved-contact IDs are not phone numbers.
    count=len(reports)
    if count>=2:reasons.append(f'This number has {count} locally submitted spam/scam reports. Review the recipient before proceeding.')
    elif count==1:observations.append('This number has one unverified local report. Independently verify the recipient.')
    concern='Review required' if reasons else ('Caution — check details' if observations else 'No elevated concern detected')
    return {'status':concern,'action':'Keep the transfer pending for review' if reasons else 'Review the details before confirming',
            'follow_up':list(dict.fromkeys(reasons)), 'observations':observations,'explanations':base.get('explanations',[]),
            'requires_review':bool(reasons),'model_score':model_score,'report_count':count,
            'source_note':'Behavioral ML plus a separate report policy. Reports are unverified submissions, not independent-victim counts.'}
