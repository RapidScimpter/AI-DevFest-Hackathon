"""Password hashing, session tokens and role checks."""
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User

COOKIE = 'surokkha_session'


def hash_secret(value: str) -> str:
    return bcrypt.hashpw(value.encode()[:72], bcrypt.gensalt()).decode()


def check_secret(value: str, hashed: str | None) -> bool:
    return bool(hashed) and bcrypt.checkpw(value.encode()[:72], hashed.encode())


def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user.id), 'role': user.role, 'iat': now, 'exp': now + timedelta(minutes=settings.token_minutes)},
                      settings.secret_key, algorithm='HS256')


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    header = request.headers.get('authorization', '')
    if not token and header.lower().startswith('bearer '):
        token = header[7:]
    try:
        claims = jwt.decode(token or '', settings.secret_key, algorithms=['HS256'])
    except jwt.PyJWTError:
        raise HTTPException(401, 'Please sign in.')
    user = db.get(User, int(claims['sub']))
    if not user or not user.is_active:
        raise HTTPException(401, 'Please sign in.')
    return user


def require_role(*roles):
    """Dependency factory: only the listed roles may call the endpoint."""
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, 'Your role does not have access to this resource.')
        return user
    return check


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ''
