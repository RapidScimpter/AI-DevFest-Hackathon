import re
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import audit
from ..config import settings
from ..db import get_db
from ..models import Consent, User, Wallet, utcnow
from ..reports import normalize_number
from ..security import COOKIE, check_secret, client_ip, current_user, hash_secret, issue_token

router = APIRouter(prefix='/api/auth', tags=['auth'])


class Login(BaseModel):
    login: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str
    password: str = Field(min_length=8, max_length=128)
    pin: str = Field(pattern=r'^\d{4,6}$')


def login_id(value: str) -> str:
    value = value.strip()
    try:
        return normalize_number(value)
    except ValueError:
        return value.lower()


def public(user: User):
    return {'id': user.id, 'name': user.name, 'login': user.login, 'role': user.role, 'segment': user.segment, 'demo_mode': settings.demo_mode}


def start_session(response: Response, user: User):
    response.set_cookie(COOKIE, issue_token(user), max_age=settings.token_minutes * 60, httponly=True, samesite='strict',
                        secure=settings.cookie_secure, path='/')


@router.post('/register', status_code=201)
def register(body: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        phone = normalize_number(body.phone)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not re.fullmatch(r'\+8801[3-9]\d{8}', phone):
        raise HTTPException(400, 'Enter a valid Bangladesh mobile number.')
    if not (re.search(r'[A-Za-z]', body.password) and re.search(r'\d', body.password)):
        raise HTTPException(400, 'Password needs at least one letter and one number.')
    if db.scalar(select(User).where(User.login == phone)):
        raise HTTPException(409, 'An account already exists for this number.')
    user = User(login=phone, name=body.name.strip(), role='customer', password_hash=hash_secret(body.password), pin_hash=hash_secret(body.pin))
    db.add(user); db.flush()
    db.add(Wallet(user_id=user.id, balance=settings.opening_balance * 100))
    db.add_all(Consent(user_id=user.id, permission=p, granted=False) for p in ('device', 'location', 'camera'))
    audit.record(db, user, 'auth.registered', 'user', user.id, {}, client_ip(request))
    db.commit()
    start_session(response, user)
    return public(user)


@router.post('/login')
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    ip, ident = client_ip(request), login_id(body.login)
    user = db.scalar(select(User).where(User.login == ident))
    now = utcnow()
    if user and user.locked_until and user.locked_until > now:
        audit.record(db, user, 'auth.login_blocked', 'user', user.id, {}, ip); db.commit()
        raise HTTPException(429, 'Too many failed attempts. Try again later.')
    if not user or not user.is_active or not check_secret(body.password, user.password_hash):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= settings.max_failed_logins:
                user.locked_until, user.failed_logins = now + timedelta(minutes=settings.lockout_minutes), 0
        audit.record(db, user, 'auth.login_failed', 'user', user.id if user else '', {'login': ident[:32]}, ip)
        db.commit()
        raise HTTPException(401, 'Incorrect number or password.')
    user.failed_logins, user.locked_until = 0, None
    audit.record(db, user, 'auth.login', 'user', user.id, {'device': request.headers.get('x-device-id', '')[:80]}, ip)
    db.commit()
    start_session(response, user)
    return public(user)


@router.post('/logout')
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    audit.record(db, user, 'auth.logout', 'user', user.id, {}, client_ip(request)); db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


@router.get('/me')
def me(user: User = Depends(current_user)):
    return public(user)


@router.get('/demo')
def demo_accounts():
    """Public account shortcuts are disabled; customers sign in normally."""
    return []
