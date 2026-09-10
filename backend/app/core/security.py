import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from ..models import Session, User
from .database import get_db

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get("biometria_session", "")
    session = db.get(Session, digest(token)) if token else None
    if not session or utc(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Sessão inválida.")
    return user


def admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Acesso restrito ao administrador.")
    return user
