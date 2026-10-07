import json
from statistics import mean, median
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .. import audit
from ..config import ROOT, settings
from ..db import get_db
from ..ml.drift import level, psi
from ..ml.features import FEATURES
from ..ml.scoring import artifacts
from ..models import AuditLog, Report, Transfer, User, Wallet, utcnow
from ..security import client_ip, hash_secret, require_role
from ..services import wallet as svc

router = APIRouter(prefix='/api', tags=['analyst'])
staff = require_role('analyst', 'admin')
admin = require_role('admin')
MIN_POPULATION, MIN_FRAUD = 50, 20


class Decision(BaseModel):
    action: str
    note: str = Field(min_length=5, max_length=2000)
    confirmed_fraud: bool = False


class StaffUser(BaseModel):
    login: str = Field(pattern=r'^[a-z][a-z0-9_.]{2,31}$')
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=10, max_length=128)
    role: str = Field(pattern=r'^(analyst|admin)$')


def _percentile(values, q):
    values = sorted(values)
    return values[min(int(q * len(values)), len(values) - 1)]


@router.get('/analyst/overview')
def overview(user: User = Depends(staff), db: Session = Depends(get_db)):
    rows = db.scalars(select(Transfer)).all()
    by_status = {}
    for t in rows:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    stopped_analyst = [t for t in rows if t.status == 'Cancelled' and t.decided_by]
    stopped_customer = [t for t in rows if t.status == 'Cancelled' and t.flagged and not t.decided_by]
    decided = [t for t in rows if t.decided_by and t.review_started_at]
    times = [(t.decided_at - t.review_started_at).total_seconds() for t in decided]
    queue = [t for t in rows if t.status == 'Under review']
    now = utcnow()
    approved = sum(t.outcome == 'legitimate' for t in decided)
    return {
        'transfers': len(rows), 'by_status': by_status, 'flagged': sum(t.flagged for t in rows),
        'prevented_value': {'total': sum(t.amount for t in stopped_analyst + stopped_customer) / 100,
                            'stopped_by_analyst': sum(t.amount for t in stopped_analyst) / 100, 'analyst_cases': len(stopped_analyst),
                            'cancelled_by_customer_after_warning': sum(t.amount for t in stopped_customer) / 100, 'customer_cases': len(stopped_customer),
                            'note': 'Value of flagged transfers that did not complete. Virtual money.'},
        'review_time': {'decisions': len(times), 'mean_seconds': mean(times) if times else None, 'median_seconds': median(times) if times else None,
                        'p90_seconds': _percentile(times, .9) if times else None},
        'queue': {'waiting': len(queue), 'oldest_waiting_seconds': max(((now - t.review_started_at).total_seconds() for t in queue), default=None),
                  'value_on_hold': sum(t.amount for t in queue) / 100},
        'alert_outcomes': {'approved_as_legitimate': approved, 'stopped': len(decided) - approved,
                           'confirmed_fraud': sum(t.outcome == 'confirmed_fraud' for t in rows)},
        'customers': db.scalar(select(func.count()).select_from(User).where(User.role == 'customer')),
        'thresholds': {'review': settings.review_threshold, 'high': settings.high_threshold}}


@router.get('/analyst/transfers')
def transfers(status: str = '', user: User = Depends(staff), db: Session = Depends(get_db)):
    q = select(Transfer, User).join(User, User.id == Transfer.user_id)
    if status:
        q = q.where(Transfer.status == status)
    return [svc.serialize(t, True, u) for t, u in db.execute(q.order_by(Transfer.id.desc()).limit(200))]


@router.post('/analyst/transfers/{tid}/decision')
def decision(tid: int, body: Decision, request: Request, user: User = Depends(staff), db: Session = Depends(get_db)):
    t = svc.decide(db, user, tid, body.action, body.note, body.confirmed_fraud, client_ip(request))
    return svc.serialize(t, True, db.get(User, t.user_id))


@router.get('/analyst/customers')
def customers(user: User = Depends(staff), db: Session = Depends(get_db)):
    out = []
    for u, w in db.execute(select(User, Wallet).join(Wallet, Wallet.user_id == User.id).order_by(User.id)):
        out.append({'id': u.id, 'name': u.name, 'login': u.login, 'segment': u.segment, **svc.summary(db, u.id),
                    'consents': {p: c['granted'] for p, c in svc.consents(db, u.id).items()}})
    return out


@router.get('/analyst/reports')
def all_reports(user: User = Depends(staff), db: Session = Depends(get_db)):
    return [{'id': r.id, 'number': r.number, 'channel': r.channel, 'category': r.category, 'evidence': r.evidence, 'created_at': svc.iso(r.created_at)}
            for r in db.scalars(select(Report).order_by(Report.id.desc()).limit(200))]


@router.get('/analyst/model')
def model(user: User = Depends(staff)):
    return {'fraud': json.loads((ROOT / 'models/metrics.json').read_text()), 'messages': json.loads((ROOT / 'models/nlp_metrics.json').read_text())}


@router.get('/analyst/drift')
def drift(user: User = Depends(staff), db: Session = Depends(get_db)):
    """Compare recent live activity with the training reference to spot changing scam methods."""
    ref = artifacts()['reference']
    rows = [t for t in db.scalars(select(Transfer).order_by(Transfer.id.desc()).limit(1000)) if t.analysis.get('probability') is not None]

    def compare(sample, reference, minimum):
        if len(sample) < minimum:
            return {'events': len(sample), 'minimum': minimum, 'status': 'not enough data', 'features': []}
        values = sorted(((f, psi(reference[f], [t.analysis['features'][f] for t in sample])) for f in FEATURES), key=lambda kv: -kv[1])
        avg = sum(v for _, v in values) / len(values)
        return {'events': len(sample), 'minimum': minimum, 'status': level(avg), 'mean_psi': round(avg, 3),
                'features': [{'feature': f, 'psi': round(v, 3), 'status': level(v)} for f, v in values[:8]]}

    fraud = [t for t in rows if t.outcome == 'confirmed_fraud']
    missed = [t for t in fraud if t.analysis['probability'] < settings.review_threshold]
    return {'population': compare(rows, ref['all'], MIN_POPULATION), 'confirmed_fraud': compare(fraud, ref['fraud'], MIN_FRAUD),
            'missed_by_model': {'confirmed_fraud': len(fraud), 'scored_below_threshold': len(missed),
                                'share': round(len(missed) / len(fraud), 3) if fraud else None},
            'simulation': json.loads((ROOT / 'models/metrics.json').read_text())['drift_simulation'],
            'guide': 'PSI below 0.10 is stable, 0.10 to 0.25 a moderate shift, above 0.25 a major shift. A rising share of confirmed fraud that the model scored low means scammers have changed method and the model needs retraining.'}


@router.get('/analyst/audit')
def audit_log(action: str = '', limit: int = 200, user: User = Depends(staff), db: Session = Depends(get_db)):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action.like(f'{action}%'))
    entries = db.scalars(q.order_by(AuditLog.id.desc()).limit(min(max(limit, 1), 1000))).all()
    names = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_({e.actor_id for e in entries if e.actor_id})))}
    ok, checked, broken = audit.verify(db)
    return {'chain': {'intact': ok, 'entries_checked': checked, 'first_broken_id': broken},
            'entries': [{'id': e.id, 'ts': e.ts, 'actor': names.get(e.actor_id, 'unknown'), 'role': e.actor_role, 'action': e.action, 'entity': e.entity,
                         'entity_id': e.entity_id, 'detail': e.detail, 'ip': e.ip, 'hash': e.hash[:12]} for e in entries]}


@router.post('/admin/users', status_code=201)
def create_staff(body: StaffUser, request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.login == body.login)):
        raise HTTPException(409, 'That username is taken.')
    new = User(login=body.login, name=body.name, role=body.role, password_hash=hash_secret(body.password))
    db.add(new); db.flush()
    audit.record(db, user, 'admin.user_created', 'user', new.id, {'role': body.role, 'login': body.login}, client_ip(request))
    db.commit()
    return {'id': new.id, 'login': new.login, 'role': new.role}
