"""Commercial administration. Global responses use explicit non-clinical fields."""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models as m
from .core.access import access_state, utc
from .core.database import get_db
from .core.security import current_user, hasher, platform_admin
from .services.serialization import row

router = APIRouter()

Role = Literal["admin", "physiotherapist", "platform_admin"]

Plan = Literal["trial", "monthly", "quarterly", "annual", "custom", "lifetime"]

Status = Literal["trial", "active", "suspended", "expired", "cancelled"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def required_values(self):
        for name in ("name", "role", "is_active", "plan_code", "subscription_status"):
            if name in self.model_fields_set and getattr(self, name, None) is None:
                raise ValueError(name + " não aceita null")
        return self


class ClinicPatch(Input):
    name: str | None = Field(None, min_length=2, max_length=160)
    is_active: bool | None = None
    plan_code: Plan | None = None
    subscription_status: Status | None = None
    access_starts_at: AwareDatetime | None = None
    access_expires_at: AwareDatetime | None = None
    suspension_reason: str | None = Field(None, max_length=2000)
    max_users: int | None = Field(None, ge=1, le=100000)


class ClinicCreate(ClinicPatch):
    name: str = Field(min_length=2, max_length=160)


class Extension(Input):
    days: Literal[7, 30, 90, 365] = 30
    trial: bool = False


class UserPatch(Input):
    is_active: bool | None = None
    access_expires_at: AwareDatetime | None = None
    suspension_reason: str | None = Field(None, max_length=2000)
    role: Role | None = None


class UserCreate(Input):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=12, max_length=128)
    role: Role = "physiotherapist"
    clinic_id: str | None = None


def event(db, actor, action, target, changes=None):
    if actor.role != "platform_admin":
        action = action.replace("platform.", "clinic.", 1)
    db.add(
        m.AuditLog(
            clinic_id=actor.clinic_id,
            actor_id=actor.id,
            action=action,
            resource_id=target,
            changes=changes or {},
        )
    )


def user_view(u, clinic):

    fields = [
        "id",
        "clinic_id",
        "name",
        "email",
        "role",
        "is_active",
        "access_expires_at",
        "suspended_at",
        "suspension_reason",
        "last_login_at",
        "created_at",
        "updated_at",
    ]
    result = {
        f: utc(getattr(u, f)) if isinstance(getattr(u, f), datetime) else getattr(u, f)
        for f in fields
    }
    result["access"] = access_state(u, clinic)
    return result


def clinic_view(c):

    fields = [
        "id",
        "name",
        "is_active",
        "plan_code",
        "subscription_status",
        "access_starts_at",
        "access_expires_at",
        "suspended_at",
        "suspension_reason",
        "max_users",
        "created_at",
        "updated_at",
    ]
    result = {
        f: utc(getattr(c, f)) if isinstance(getattr(c, f), datetime) else getattr(c, f)
        for f in fields
    }
    proxy = m.User(role="physiotherapist", is_active=True)
    result["access"] = access_state(proxy, c)
    return result


def managed_actor(request: Request, user: m.User = Depends(current_user)):

    if request.url.path.startswith("/platform/") and user.role != "platform_admin":
        raise HTTPException(403, "Acesso restrito à plataforma.")
    if user.role not in ("admin", "platform_admin"):
        raise HTTPException(403, "Acesso restrito à administração.")
    return user


def lock_clinic(db, identifier):

    clinic = db.scalar(
        select(m.Clinic)
        .where(m.Clinic.id == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not clinic:
        raise HTTPException(404, "Clínica não encontrada.")
    return clinic


def check_capacity(db, clinic, exclude=None):

    query = (
        select(func.count())
        .select_from(m.User)
        .where(m.User.clinic_id == clinic.id, m.User.is_active.is_(True))
    )
    if exclude:
        query = query.where(m.User.id != exclude)
    if clinic.max_users is not None and db.scalar(query) >= clinic.max_users:
        raise HTTPException(409, "Limite de usuários ativos da clínica atingido.")


@router.get("/platform/clinics")
def clinics(
    q: str = "", actor: m.User = Depends(platform_admin), db: Session = Depends(get_db)
):

    query = select(m.Clinic).order_by(m.Clinic.name)
    if q:
        query = query.where(m.Clinic.name.ilike("%" + q + "%"))
    return [clinic_view(c) for c in db.scalars(query)]


@router.post("/platform/clinics", status_code=201)
def create_clinic(
    body: ClinicCreate,
    actor: m.User = Depends(platform_admin),
    db: Session = Depends(get_db),
):

    data = body.model_dump(exclude_unset=True)
    start = data.get("access_starts_at")
    end = data.get("access_expires_at")
    if start and end and start >= end:
        raise HTTPException(422, "Início deve anteceder vencimento.")
    c = m.Clinic(**data)
    db.add(c)
    db.flush()
    if not c.is_active or c.subscription_status == "suspended":
        c.suspended_at = m.now()
    event(
        db,
        actor,
        "platform.clinic_created",
        c.id,
        body.model_dump(mode="json", exclude_unset=True),
    )
    db.commit()
    return clinic_view(c)


@router.patch("/platform/clinics/{identifier}")
def update_clinic(
    identifier: str,
    body: ClinicPatch,
    actor: m.User = Depends(platform_admin),
    db: Session = Depends(get_db),
):

    c = lock_clinic(db, identifier)
    before = c.is_active and c.subscription_status not in ("suspended", "cancelled")
    data = body.model_dump(exclude_unset=True)
    start = data.get("access_starts_at", c.access_starts_at)
    end = data.get("access_expires_at", c.access_expires_at)
    if start and end and utc(start) >= utc(end):
        raise HTTPException(422, "Início deve anteceder vencimento.")
    for key, value in data.items():
        setattr(c, key, value)
    blocked = not c.is_active or c.subscription_status in (
        "suspended",
        "cancelled",
        "expired",
    )
    c.suspended_at = (
        m.now() if not c.is_active or c.subscription_status == "suspended" else None
    )
    if not blocked:
        c.suspension_reason = None
    if blocked:
        db.execute(
            delete(m.Session).where(
                m.Session.user_id.in_(
                    select(m.User.id).where(
                        m.User.clinic_id == c.id, m.User.role != "platform_admin"
                    )
                )
            )
        )
    action = (
        "platform.clinic_suspended"
        if blocked
        else (
            "platform.clinic_reactivated" if not before else "platform.clinic_updated"
        )
    )
    event(db, actor, action, c.id, body.model_dump(mode="json", exclude_unset=True))
    if c.subscription_status == "expired" or (
        c.access_expires_at and utc(c.access_expires_at) <= m.now()
    ):
        event(db, actor, "platform.subscription_expired", c.id)
    db.commit()
    return clinic_view(c)


@router.post("/platform/clinics/{identifier}/extend")
def extend(
    identifier: str,
    body: Extension,
    actor: m.User = Depends(platform_admin),
    db: Session = Depends(get_db),
):

    c = lock_clinic(db, identifier)
    base = m.now() if body.trial else max(m.now(), utc(c.access_expires_at) or m.now())
    c.access_expires_at = base + timedelta(days=7 if body.trial else body.days)
    c.access_starts_at = m.now() if body.trial else c.access_starts_at
    c.is_active = True
    c.subscription_status = "trial" if body.trial else "active"
    if body.trial:
        c.plan_code = "trial"
    c.suspended_at = None
    c.suspension_reason = None
    event(
        db,
        actor,
        "platform.subscription_extended",
        c.id,
        {
            "days": 7 if body.trial else body.days,
            "expires_at": c.access_expires_at.isoformat(),
        },
    )
    db.commit()
    return clinic_view(c)


@router.get("/platform/users")
@router.get("/admin/users")
def users(
    q: str = "",
    clinic_id: str | None = None,
    status: str | None = None,
    actor: m.User = Depends(managed_actor),
    db: Session = Depends(get_db),
):

    query = (
        select(m.User, m.Clinic)
        .join(m.Clinic, m.User.clinic_id == m.Clinic.id)
        .order_by(m.User.name)
    )
    if actor.role == "admin":
        query = query.where(
            m.User.clinic_id == actor.clinic_id, m.User.role != "platform_admin"
        )
    if clinic_id:
        query = query.where(m.User.clinic_id == clinic_id)
    if q:
        query = query.where(
            m.User.name.ilike("%" + q + "%") | m.User.email.ilike("%" + q + "%")
        )
    values = [user_view(u, c) for u, c in db.execute(query)]
    return [
        v
        for v in values
        if not status
        or (status == "active" and v["access"]["allowed"])
        or v["access"]["code"] == status
    ]


@router.post("/platform/users", status_code=201)
@router.post("/admin/users", status_code=201)
def create_user(
    body: UserCreate,
    actor: m.User = Depends(managed_actor),
    db: Session = Depends(get_db),
):

    if actor.role != "platform_admin" and (
        body.role == "platform_admin"
        or (body.clinic_id and body.clinic_id != actor.clinic_id)
    ):
        raise HTTPException(403, "Permissão ou clínica não autorizada.")
    clinic = lock_clinic(db, body.clinic_id or actor.clinic_id)
    check_capacity(db, clinic)
    if db.scalar(select(m.User.id).where(m.User.email == body.email.lower())):
        raise HTTPException(409, "Não foi possível cadastrar este e-mail.")
    u = m.User(
        name=body.name,
        email=body.email.lower(),
        role=body.role,
        clinic_id=clinic.id,
        password_hash=hasher.hash(body.password),
    )
    db.add(u)
    db.flush()
    if u.role != "platform_admin":
        db.add(m.Professional(user_id=u.id))
    event(
        db,
        actor,
        "platform.user_created",
        u.id,
        {"clinic_id": clinic.id, "role": u.role},
    )
    db.commit()
    return user_view(u, clinic)


@router.patch("/platform/users/{identifier}")
@router.patch("/admin/users/{identifier}")
def update_user(
    identifier: str,
    body: UserPatch,
    actor: m.User = Depends(managed_actor),
    db: Session = Depends(get_db),
):

    # Serialize platform account changes by locking all global admins in stable order.
    globals = list(
        db.scalars(
            select(m.User)
            .where(m.User.role == "platform_admin")
            .order_by(m.User.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    u = db.get(m.User, identifier, populate_existing=True)
    if not u or (
        actor.role == "admin"
        and (u.clinic_id != actor.clinic_id or u.role == "platform_admin")
    ):
        raise HTTPException(404, "Usuário não encontrado.")
    if actor.role != "platform_admin" and body.role == "platform_admin":
        raise HTTPException(403, "Permissão não autorizada.")
    if u.role == "platform_admin" and (
        body.is_active is False or (body.role and body.role != "platform_admin")
    ):
        if not any(v.id != u.id and v.is_active for v in globals):
            raise HTTPException(
                409, "Não é permitido remover o último platform_admin ativo."
            )
    clinic = lock_clinic(db, u.clinic_id)
    if body.is_active is True and not u.is_active:
        check_capacity(db, clinic, u.id)
    old_active = u.is_active
    old_role = u.role
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(u, key, value)
    u.suspended_at = None if u.is_active else m.now()
    if u.is_active:
        u.suspension_reason = None
    if not u.is_active or old_role != u.role:
        db.execute(delete(m.Session).where(m.Session.user_id == u.id))
    if old_role != u.role:
        event(
            db,
            actor,
            "platform.user_role_changed",
            u.id,
            {"before": old_role, "after": u.role},
        )
    action = (
        "platform.user_suspended"
        if not u.is_active
        else (
            "platform.user_reactivated"
            if not old_active
            else "platform.user_access_updated"
        )
    )
    event(db, actor, action, u.id, body.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return user_view(u, clinic)


@router.get("/platform/dashboard")
def dashboard(actor: m.User = Depends(platform_admin), db: Session = Depends(get_db)):

    cs = [clinic_view(c) for c in db.scalars(select(m.Clinic))]
    us = [
        user_view(u, c)
        for u, c in db.execute(
            select(m.User, m.Clinic).join(m.Clinic, m.User.clinic_id == m.Clinic.id)
        )
    ]
    return {
        "clinics": len(cs),
        "active_clinics": sum(c["access"]["allowed"] for c in cs),
        "expired_subscriptions": sum(
            c["access"]["code"] == "subscription_expired" for c in cs
        ),
        "expiring_7": sum(
            c["access"]["allowed"]
            and c["access"]["days_remaining"] is not None
            and c["access"]["days_remaining"] <= 7
            for c in cs
        ),
        "expiring_30": sum(
            c["access"]["allowed"]
            and c["access"]["days_remaining"] is not None
            and c["access"]["days_remaining"] <= 30
            for c in cs
        ),
        "active_users": sum(u["access"]["allowed"] for u in us),
        "suspended_users": sum(
            u["access"]["code"] in ("account_disabled", "clinic_suspended") for u in us
        ),
        "expired_users": sum(
            u["access"]["code"] in ("user_access_expired", "subscription_expired")
            for u in us
        ),
    }


@router.get("/platform/audit")
def logs(
    actor: m.User = Depends(platform_admin),
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=1000),
):

    return [
        {**row(a), "created_at": utc(a.created_at)}
        for a in db.scalars(
            select(m.AuditLog)
            .where(m.AuditLog.action.like("platform.%"))
            .order_by(m.AuditLog.created_at.desc())
            .limit(limit)
        )
    ]


@router.get("/platform/clinics/{identifier}")
def clinic_detail(
    identifier: str,
    actor: m.User = Depends(platform_admin),
    db: Session = Depends(get_db),
):
    clinic = db.get(m.Clinic, identifier)
    if not clinic:
        raise HTTPException(404, "Clínica não encontrada.")
    return clinic_view(clinic)
