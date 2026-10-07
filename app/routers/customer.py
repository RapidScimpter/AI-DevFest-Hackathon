import csv
import hashlib
import io
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import audit, reports
from ..db import get_db
from ..ml.nlp import screen_message
from ..models import Consent, Transfer, TrustedDevice, User, utcnow
from ..security import check_secret, client_ip, current_user, require_role
from ..services import wallet as svc

router = APIRouter(prefix='/api', tags=['customer'])
customer = require_role('customer')


class TransferIn(BaseModel):
    recipient: str = Field(min_length=3, max_length=40)
    amount: float = Field(gt=0, le=10_000_000)
    txn_type: str = 'send'
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    demo: dict | None = None


class Pin(BaseModel):
    pin: str = Field(pattern=r'^\d{4,6}$')


class Cancel(BaseModel):
    not_me: bool = False


class Photo(BaseModel):
    image: str = Field(min_length=100, max_length=3_000_000)


class Grant(BaseModel):
    granted: bool


class Check(BaseModel):
    number: str
    message: str = Field(default='', max_length=4000)


class ReportIn(BaseModel):
    number: str
    channel: str
    category: str
    evidence: str


def device_of(request: Request):
    return (request.headers.get('x-device-id') or '').strip()[:80] or None


@router.get('/wallet')
def wallet(request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    transfers = db.scalars(select(Transfer).where(Transfer.user_id == user.id).order_by(Transfer.id.desc()).limit(40)).all()
    device, consents = device_of(request), svc.consents(db, user.id)
    known = {e['device_id'] for e in svc.history(db, user.id)} | svc.trusted(db, user.id)
    return {'summary': svc.summary(db, user.id), 'transfers': [svc.serialize(t) for t in transfers], 'saved_recipients': svc.saved_recipients(db, user.id),
            'consents': consents, 'types': svc.TYPES, 'districts': list(svc.DISTRICTS),
            'device': {'shared': consents['device']['granted'] and bool(device), 'trusted': bool(device) and device in known}}


@router.post('/transfers', status_code=201)
def create_transfer(body: TransferIn, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    coords = (body.latitude, body.longitude) if body.latitude is not None and body.longitude is not None else None
    ctx = svc.build_context(db, user, device_of(request), coords, body.demo)
    return svc.serialize(svc.request_transfer(db, user, body.recipient, body.amount, body.txn_type, ctx, client_ip(request)))


@router.post('/transfers/{tid}/confirm')
def confirm(tid: int, body: Pin, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    return svc.serialize(svc.confirm(db, user, tid, body.pin, client_ip(request)))


@router.post('/transfers/{tid}/cancel')
def cancel(tid: int, body: Cancel, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    return svc.serialize(svc.cancel(db, user, tid, body.not_me, client_ip(request)))


@router.post('/transfers/{tid}/photo-check')
def photo_check(tid: int, body: Photo, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    """Optional live photo for a held transfer. Only a fingerprint is kept; no face matching is performed."""
    if not svc.consents(db, user.id)['camera']['granted']:
        raise HTTPException(403, 'Camera permission has not been granted.')
    t = svc.get_transfer(db, tid, user.id)
    if t.status != 'Under review': raise ValueError('A photo check is only available while a transfer is under review.')
    if not body.image.startswith('data:image/'): raise ValueError('Send a captured image.')
    t.evidence = {**t.evidence, 'photo_check': {'sha256': hashlib.sha256(body.image.encode()).hexdigest(), 'bytes': len(body.image), 'at': svc.iso(utcnow())}}
    audit.record(db, user, 'transfer.photo_check', 'transfer', t.id, {}, client_ip(request))
    db.commit()
    return svc.serialize(t)


@router.get('/statement.csv')
def statement(user: User = Depends(customer), db: Session = Depends(get_db)):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['Reference', 'Created (UTC)', 'Type', 'Recipient', 'Amount (BDT)', 'Status'])
    for t in db.scalars(select(Transfer).where(Transfer.user_id == user.id).order_by(Transfer.id.desc())):
        writer.writerow([t.id, svc.iso(t.created_at), svc.TYPES.get(t.txn_type), t.recipient, f'{t.amount / 100:.2f}', t.status])
    return Response(out.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="surokkha-statement.csv"'})


@router.post('/devices/trust')
def trust_device(body: Pin, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    device = device_of(request)
    if not device or not svc.consents(db, user.id)['device']['granted']:
        raise HTTPException(400, 'Allow the device identifier permission first.')
    if not check_secret(body.pin, user.pin_hash):
        audit.record(db, user, 'pin.failed', 'device', device, {}, client_ip(request)); db.commit()
        raise HTTPException(403, 'Incorrect wallet PIN.')
    if not db.scalar(select(TrustedDevice).where(TrustedDevice.user_id == user.id, TrustedDevice.device_id == device)):
        db.add(TrustedDevice(user_id=user.id, device_id=device))
        audit.record(db, user, 'device.trusted', 'device', device, {}, client_ip(request))
    db.commit()
    return {'trusted': True}


@router.put('/consents/{permission}')
def set_consent(permission: str, body: Grant, request: Request, user: User = Depends(customer), db: Session = Depends(get_db)):
    if permission not in svc.PERMISSIONS:
        raise HTTPException(404, 'Unknown permission.')
    row = db.scalar(select(Consent).where(Consent.user_id == user.id, Consent.permission == permission))
    if not row:
        row = Consent(user_id=user.id, permission=permission); db.add(row)
    row.granted, row.updated_at = body.granted, utcnow()
    audit.record(db, user, 'consent.granted' if body.granted else 'consent.revoked', 'consent', permission, {}, client_ip(request))
    db.commit()
    return svc.consents(db, user.id)


@router.post('/contacts/check')
def check_contact(body: Check, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Queries are not stored. The message is scored by the trained classifier."""
    found = reports.lookup(db, body.number, body.message)
    nlp = screen_message(body.message)
    n = len(found['number_reports'])
    if n >= 2: status, level = 'Repeated reports: elevated concern (unverified)', 'danger'
    elif n or found['matching_text_reports']: status, level = 'Community report found: use caution (unverified)', 'caution'
    elif nlp.get('flagged'): status, level = 'This message looks like a scam', 'danger' if nlp['scam_probability'] >= .8 else 'caution'
    elif nlp['signals']: status, level = 'Warning signs found: investigate', 'caution'
    else: status, level = 'No reports or warning signs found (not a guarantee of safety)', 'safe'
    return {**found, 'status': status, 'level': level, 'message': nlp}


@router.post('/contacts/report', status_code=201)
def report_contact(body: ReportIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report, created = reports.add_report(db, body.number, body.channel, body.category, body.evidence, user.id)
    if created:
        audit.record(db, user, 'report.submitted', 'report', report.id, {'number': report.number, 'category': report.category}, client_ip(request))
    db.commit()
    return {'id': report.id, 'created': created, 'number': report.number}
