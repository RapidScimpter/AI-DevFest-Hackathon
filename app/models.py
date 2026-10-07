from datetime import datetime, timezone
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(32), unique=True, index=True)   # mobile number or staff username
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16), default='customer')        # customer | analyst | admin
    password_hash: Mapped[str] = mapped_column(String(100))
    pin_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(24), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Wallet(Base):
    __tablename__ = 'wallets'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger)                         # paisa (1/100 BDT), virtual money


class Event(Base):
    """Behavioural history: seeded synthetic events plus this wallet's own requests."""
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    timestamp: Mapped[datetime] = mapped_column(DateTime)                    # local wallet time
    amount: Mapped[float] = mapped_column(Float)
    txn_type: Mapped[str] = mapped_column(String(16))
    device_id: Mapped[str] = mapped_column(String(80))
    recipient_id: Mapped[str] = mapped_column(String(40))
    district: Mapped[str] = mapped_column(String(32))
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0)
    transfer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    __table_args__ = (Index('ix_events_user_ts', 'user_id', 'timestamp'),)


class Transfer(Base):
    __tablename__ = 'transfers'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    recipient: Mapped[str] = mapped_column(String(40))
    txn_type: Mapped[str] = mapped_column(String(16), default='send')
    status: Mapped[str] = mapped_column(String(24), index=True)              # Awaiting confirmation | Under review | Completed | Cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome: Mapped[str] = mapped_column(String(32), default='')             # '', confirmed_fraud, legitimate, customer_cancelled
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    review: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    response: Mapped[str] = mapped_column(String(80), default='')
    note: Mapped[str] = mapped_column(Text, default='')


class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(40))
    evidence: Mapped[str] = mapped_column(Text)
    message_key: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    reporter_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Consent(Base):
    __tablename__ = 'consents'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    permission: Mapped[str] = mapped_column(String(16))                      # device | location | camera
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'permission'),)


class TrustedDevice(Base):
    __tablename__ = 'trusted_devices'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    device_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'device_id'),)


class AuditLog(Base):
    """Append-only, hash-chained record of security-relevant actions."""
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor_role: Mapped[str] = mapped_column(String(16), default='')
    action: Mapped[str] = mapped_column(String(48), index=True)
    entity: Mapped[str] = mapped_column(String(24), default='')
    entity_id: Mapped[str] = mapped_column(String(40), default='')
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(48), default='')
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
