"""Tamper-evident audit trail. Each entry stores the SHA-256 of the previous entry."""
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import select
from .models import AuditLog

GENESIS = '0' * 64


def _digest(prev, ts, actor_id, role, action, entity, entity_id, detail, ip):
    body = json.dumps([prev, ts, actor_id, role, action, entity, entity_id, detail, ip], sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(body.encode()).hexdigest()


def record(db, actor, action, entity='', entity_id='', detail=None, ip=''):
    """Add an entry to the session; the caller commits it with the action it describes."""
    db.flush()
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev = last.hash if last else GENESIS
    ts = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
    actor_id, role = (actor.id, actor.role) if actor is not None else (None, '')
    detail, entity_id = detail or {}, str(entity_id)
    entry = AuditLog(ts=ts, actor_id=actor_id, actor_role=role, action=action, entity=entity, entity_id=entity_id, detail=detail, ip=ip or '',
                     prev_hash=prev, hash=_digest(prev, ts, actor_id, role, action, entity, entity_id, detail, ip or ''))
    db.add(entry); db.flush()
    return entry


def verify(db):
    """Recompute the whole chain. Returns (ok, entries checked, id of first broken entry)."""
    prev, n = GENESIS, 0
    for e in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        if e.prev_hash != prev or e.hash != _digest(prev, e.ts, e.actor_id, e.actor_role, e.action, e.entity, e.entity_id, e.detail, e.ip):
            return False, n, e.id
        prev, n = e.hash, n + 1
    return True, n, None
