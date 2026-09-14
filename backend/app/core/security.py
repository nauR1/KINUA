import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from ..models import Clinic, Session, User
from .access import enforce_access
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

    clinic = db.get(Clinic, user.clinic_id)
    if clinic and clinic.is_demo:
        # Coordinate all demo requests with reset; recheck session after the lock.
        clinic = db.scalar(
            select(Clinic)
            .where(Clinic.id == clinic.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        user = db.get(User, session.user_id, populate_existing=True)
        if not user or not db.get(Session, digest(token), populate_existing=True):
            raise HTTPException(401, "Sessão da demonstração encerrada.")
    enforce_access(user, clinic)

    if user.role == "platform_admin" and not (
        request.url.path.startswith("/platform/")
        or request.url.path.startswith("/auth/")
    ):
        raise HTTPException(403, "Administração global não concede acesso clínico.")

    return user


def platform_admin(user: User = Depends(current_user)) -> User:

    if user.role != "platform_admin":
        raise HTTPException(403, "Acesso restrito à administração da plataforma.")

    return user


def admin(user: User = Depends(current_user)) -> User:

    if user.role != "admin":
        raise HTTPException(403, "Acesso restrito ao administrador.")

    return user
