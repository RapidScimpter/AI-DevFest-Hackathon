"""Virtual ledger, transfer state machine and the live scoring context."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import delete, func, select
from .. import audit
from ..config import settings
from ..ml.scoring import score
from ..models import AuditLog, Consent, Event, Transfer, TrustedDevice, User, Wallet, utcnow
from ..policy import assess
from ..reports import normalize_number, report_count
from ..security import check_secret

PENDING = ('Awaiting confirmation', 'Under review')
TYPES = {'send': 'Send money', 'cash_out': 'Cash out', 'merchant_pay': 'Merchant payment'}
PERMISSIONS = {'device': 'Device identifier', 'location': 'Location', 'camera': 'Camera'}
# Division centroids used to turn consented coordinates into a coarse district.
DISTRICTS = {'Dhaka': (23.81, 90.41), 'Chattogram': (22.36, 91.78), 'Sylhet': (24.89, 91.87), 'Rajshahi': (24.37, 88.60),
             'Khulna': (22.85, 89.54), 'Barishal': (22.70, 90.35), 'Rangpur': (25.74, 89.28), 'Mymensingh': (24.75, 90.41)}
PIN_WINDOW_MINUTES = 30


def local_now():
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, microsecond=0)


def consents(db, user_id):
    rows = {c.permission: c for c in db.scalars(select(Consent).where(Consent.user_id == user_id))}
    return {p: {'label': label, 'granted': bool(rows[p].granted) if p in rows else False,
                'updated_at': rows[p].updated_at.isoformat(timespec='seconds') + 'Z' if p in rows else None} for p, label in PERMISSIONS.items()}


def summary(db, user_id):
    balance = db.get(Wallet, user_id).balance
    reserved = db.scalar(select(func.coalesce(func.sum(Transfer.amount), 0)).where(Transfer.user_id == user_id, Transfer.status.in_(PENDING)))
    return {'balance': balance / 100, 'reserved': reserved / 100, 'available': (balance - reserved) / 100}


def history(db, user_id, before=None, limit=60):
    q = select(Event).where(Event.user_id == user_id)
    if before is not None:
        q = q.where(Event.timestamp < before)
    rows = db.scalars(q.order_by(Event.timestamp.desc(), Event.id.desc()).limit(limit)).all()[::-1]
    return [{'timestamp': r.timestamp, 'amount': r.amount, 'txn_type': r.txn_type, 'device_id': r.device_id, 'recipient_id': r.recipient_id,
             'district': r.district, 'failed_pin_attempts': r.failed_pin_attempts} for r in rows]


def saved_recipients(db, user_id, n=6):
    counts = Counter(e['recipient_id'] for e in history(db, user_id))
    return [{'id': r, 'uses': c} for r, c in counts.most_common(n)]


def failed_pins(db, user_id):
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=PIN_WINDOW_MINUTES)).isoformat(timespec='milliseconds')
    return db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == user_id, AuditLog.action == 'pin.failed', AuditLog.ts >= cutoff)) or 0


def trusted(db, user_id):
    return {d.device_id for d in db.scalars(select(TrustedDevice).where(TrustedDevice.user_id == user_id))}


def nearest_district(lat, lon):
    return min(DISTRICTS, key=lambda d: (DISTRICTS[d][0] - lat) ** 2 + (DISTRICTS[d][1] - lon) ** 2)


def build_context(db, user, device_id=None, coords=None, demo=None):
    """Device and location are used only with the customer's consent."""
    prior = history(db, user.id)
    granted = {p for p, c in consents(db, user.id).items() if c['granted']}
    usual_device = Counter(e['device_id'] for e in prior).most_common(1)[0][0] if prior else 'unknown'
    home = Counter(e['district'] for e in prior).most_common(1)[0][0] if prior else 'Unknown'
    unavailable = []
    if 'device' in granted and device_id:
        device = device_id[:80]
    else:
        device = usual_device; unavailable.append('device')
    if 'location' in granted and coords:
        district = nearest_district(*coords)
    else:
        district = home; unavailable.append('location')
    pins = failed_pins(db, user.id)
    if settings.demo_mode and demo:                       # presenter overrides, never active in production settings
        if demo.get('new_device'): device, unavailable = 'DEMO-UNKNOWN-DEVICE', [u for u in unavailable if u != 'device']
        if demo.get('district') in DISTRICTS: district, unavailable = demo['district'], [u for u in unavailable if u != 'location']
        pins += max(0, min(int(demo.get('failed_pins') or 0), 5))
    return {'device_id': device, 'district': district, 'failed_pin_attempts': pins, 'unavailable': unavailable}


def resolve_recipient(db, user, recipient):
    recipient = recipient.strip()
    if any(r['id'] == recipient for r in saved_recipients(db, user.id, 50)):
        return recipient
    number = normalize_number(recipient)
    if number == user.login:
        raise ValueError('You cannot send money to your own wallet.')
    return number


def _analyse(db, user, event, unavailable):
    prior = history(db, user.id, before=event['timestamp'])
    analysis = score(event, prior, trusted(db, user.id), unavailable)
    return analysis, assess(analysis, report_count(db, event['recipient_id']))


def request_transfer(db, user, recipient, amount, txn_type, ctx, ip=''):
    if txn_type not in TYPES: raise ValueError('Choose a valid transaction type.')
    paisa = round(float(amount) * 100)
    if paisa <= 0: raise ValueError('Enter a positive amount.')
    recipient = resolve_recipient(db, user, recipient)
    db.get(Wallet, user.id, with_for_update=True)
    available = summary(db, user.id)['available']
    if paisa / 100 > available: raise ValueError('Amount exceeds your available balance.')
    now = local_now()
    last = db.scalar(select(func.max(Event.timestamp)).where(Event.user_id == user.id))
    if last and now <= last: now = last + timedelta(seconds=1)
    event = {'timestamp': now, 'amount': paisa / 100, 'balance_before': available, 'txn_type': txn_type, 'recipient_id': recipient,
             'device_id': ctx['device_id'], 'district': ctx['district'], 'failed_pin_attempts': ctx['failed_pin_attempts']}
    analysis, review = _analyse(db, user, event, ctx['unavailable'])
    t = Transfer(user_id=user.id, amount=paisa, recipient=recipient, txn_type=txn_type, status='Awaiting confirmation',
                 analysis=analysis, review=review, flagged=review['requires_review'], evidence={'balance_before': available})
    db.add(t); db.flush()
    db.add(Event(user_id=user.id, transfer_id=t.id, **{k: v for k, v in event.items() if k != 'balance_before'}))
    audit.record(db, user, 'transfer.requested', 'transfer', t.id, {'amount': paisa / 100, 'recipient': recipient, 'type': txn_type,
                 'probability': analysis['probability'], 'flagged': t.flagged, 'unavailable': ctx['unavailable']}, ip)
    db.commit()
    return t


def _rescore(db, user, t):
    """Re-evaluate with the latest reports and PIN failures, so later evidence still counts."""
    ev = db.scalar(select(Event).where(Event.transfer_id == t.id))
    if not ev:
        return
    ev.failed_pin_attempts = max(ev.failed_pin_attempts, failed_pins(db, user.id))
    event = {'timestamp': ev.timestamp, 'amount': ev.amount, 'balance_before': t.evidence.get('balance_before', ev.amount), 'txn_type': ev.txn_type,
             'recipient_id': ev.recipient_id, 'device_id': ev.device_id, 'district': ev.district, 'failed_pin_attempts': ev.failed_pin_attempts}
    t.analysis, t.review = _analyse(db, user, event, t.analysis.get('unavailable', []))
    t.flagged = t.flagged or t.review['requires_review']


def _settle(db, t):
    wallet = db.get(Wallet, t.user_id, with_for_update=True)
    if wallet.balance < t.amount: raise ValueError('Insufficient balance.')
    wallet.balance -= t.amount
    payee = db.scalar(select(User).where(User.login == t.recipient, User.role == 'customer'))
    if payee:                                              # wallet-to-wallet transfer inside the platform
        db.get(Wallet, payee.id, with_for_update=True).balance += t.amount
    t.status = 'Completed'


def _release(db, t):
    db.execute(delete(Event).where(Event.transfer_id == t.id))   # cancelled requests do not shape the profile
    t.status = 'Cancelled'


def get_transfer(db, tid, user_id=None):
    t = db.get(Transfer, tid)
    if not t or (user_id is not None and t.user_id != user_id):
        raise LookupError('Transfer not found.')
    return t


def confirm(db, user, tid, pin, ip=''):
    t = get_transfer(db, tid, user.id)
    if t.status != 'Awaiting confirmation': raise ValueError('This transfer is not awaiting confirmation.')
    if not check_secret(pin, user.pin_hash):
        audit.record(db, user, 'pin.failed', 'transfer', t.id, {}, ip)
        db.commit()
        raise PermissionError('Incorrect wallet PIN.')
    _rescore(db, user, t)
    t.response = 'Customer confirmed with PIN'
    if t.review['requires_review']:
        t.status, t.review_started_at = 'Under review', utcnow()
    else:
        _settle(db, t); t.decided_at = utcnow()
    audit.record(db, user, 'transfer.confirmed', 'transfer', t.id, {'status': t.status, 'probability': t.analysis.get('probability')}, ip)
    db.commit()
    return t


def cancel(db, user, tid, not_me=False, ip=''):
    t = get_transfer(db, tid, user.id)
    if t.status not in PENDING: raise ValueError('This transfer has already been finalized.')
    _release(db, t)
    t.decided_at = utcnow()
    t.response = 'Customer reported: not my transaction' if not_me else 'Customer cancelled request'
    t.outcome = 'confirmed_fraud' if not_me else 'customer_cancelled'
    audit.record(db, user, 'transfer.cancelled', 'transfer', t.id, {'not_me': not_me, 'flagged': t.flagged}, ip)
    db.commit()
    return t


def decide(db, analyst, tid, action, note, confirmed_fraud=False, ip=''):
    t = get_transfer(db, tid)
    if t.status != 'Under review': raise ValueError('Only transfers under review can be decided.')
    if action not in ('approve', 'reject'): raise ValueError('Choose approve or reject.')
    if len(note.strip()) < 5: raise ValueError('Reviewer notes are required.')
    if action == 'approve':
        _settle(db, t); t.outcome = 'legitimate'
    else:
        _release(db, t); t.outcome = 'confirmed_fraud' if confirmed_fraud else 'rejected_unconfirmed'
    t.decided_at, t.decided_by, t.note = utcnow(), analyst.id, note.strip()
    audit.record(db, analyst, f'transfer.{action}d' if action == 'approve' else 'transfer.rejected', 'transfer', t.id,
                 {'customer_id': t.user_id, 'amount': t.amount / 100, 'outcome': t.outcome, 'note': t.note}, ip)
    db.commit()
    return t


def iso(dt):
    return dt.isoformat(timespec='seconds') + 'Z' if dt else None


def serialize(t, staff=False, user=None):
    data = {'id': t.id, 'amount': t.amount / 100, 'recipient': t.recipient, 'type': TYPES.get(t.txn_type, t.txn_type), 'status': t.status,
            'created_at': iso(t.created_at), 'decided_at': iso(t.decided_at), 'flagged': t.flagged, 'response': t.response,
            'note': t.note if t.status in ('Completed', 'Cancelled') or staff else '', 'photo_check': bool(t.evidence.get('photo_check')),
            'review': {k: t.review.get(k) for k in ('status', 'level', 'requires_review', 'follow_up', 'observations', 'probability', 'report_count', 'source_note')}}
    if staff:
        data.update(analysis=t.analysis, outcome=t.outcome, review_started_at=iso(t.review_started_at), evidence=t.evidence,
                    customer={'id': user.id, 'name': user.name, 'login': user.login, 'segment': user.segment} if user else None)
    return data
