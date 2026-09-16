from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    if old not in content:
        raise RuntimeError(f"Pattern not found in {path}: {old[:120]!r}")
    if content.count(old) != 1:
        raise RuntimeError(f"Pattern is not unique in {path}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


write(
    "backend/app/core/access.py",
    '''"""One UTC access policy, shared by login, requests and administration."""

import math
from datetime import datetime, timezone

from fastapi import HTTPException


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value
    )


def access_state(user, clinic, now=None):
    now = utc(now) if now else datetime.now(timezone.utc)
    user_expiry = utc(user.access_expires_at)
    user_start = utc(getattr(user, "access_starts_at", None))
    plan = None
    code = None
    expiry = user_expiry

    if user.role == "platform_admin":
        if not user.is_active:
            code = "account_disabled"
        expiry = None
    else:
        plan = ("demo" if clinic.is_demo else clinic.plan_code) if clinic else None
        lifetime = bool(clinic and not clinic.is_demo and clinic.plan_code == "lifetime")
        clinic_expiry = (
            utc(clinic.access_expires_at)
            if clinic and not clinic.is_demo and not lifetime
            else None
        )
        inherited_start = (
            utc(clinic.access_starts_at)
            if clinic and not clinic.is_demo and not lifetime
            else None
        )
        starts_at = user_start or inherited_start
        expiry = min([d for d in [user_expiry, clinic_expiry] if d], default=None)

        if not clinic or not clinic.is_active or (
            not clinic.is_demo and clinic.subscription_status == "suspended"
        ):
            code = "clinic_suspended"
        elif not user.is_active:
            code = "account_disabled"
        elif user_expiry and now >= user_expiry:
            code = "user_access_expired"
        elif clinic.is_demo:
            if user_start and now < user_start:
                code = "access_not_started"
        elif clinic.subscription_status == "cancelled":
            code = "subscription_cancelled"
        elif clinic.subscription_status == "expired" or (
            clinic_expiry and now >= clinic_expiry
        ):
            code = "subscription_expired"
        elif starts_at and now < starts_at:
            code = "access_not_started"

    return {
        "allowed": code is None,
        "is_demo": bool(clinic and clinic.is_demo),
        "code": code,
        "plan": plan,
        "expires_at": expiry.isoformat() if expiry else None,
        "days_remaining": max(0, math.ceil((expiry - now).total_seconds() / 86400))
        if expiry
        else None,
    }


def enforce_access(user, clinic):
    state = access_state(user, clinic)
    if not state["allowed"]:
        raise HTTPException(403, state)
    return state
''',
)

replace_once(
    "backend/app/models.py",
    '''class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="physiotherapist")

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
''',
    '''class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="physiotherapist")

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    access_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''class UserPatch(Input):
    is_active: bool | None = None
    access_expires_at: AwareDatetime | None = None
    suspension_reason: str | None = Field(None, max_length=2000)
    role: Role | None = None


class UserCreate(Input):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
    )
    password: str = Field(min_length=12, max_length=128)
    role: Role = "physiotherapist"
    clinic_id: str | None = None
''',
    '''class UserPatch(Input):
    is_active: bool | None = None
    access_starts_at: AwareDatetime | None = None
    access_expires_at: AwareDatetime | None = None
    suspension_reason: str | None = Field(None, max_length=2000)
    role: Role | None = None


class UserCreate(Input):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$"
    )
    password: str = Field(min_length=12, max_length=128)
    role: Role = "physiotherapist"
    clinic_id: str | None = None
    is_active: bool = True
    access_starts_at: AwareDatetime | None = None
    access_expires_at: AwareDatetime | None = None
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''        "role",
        "is_active",
        "access_expires_at",
        "suspended_at",
''',
    '''        "role",
        "is_active",
        "access_starts_at",
        "access_expires_at",
        "suspended_at",
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''    data = body.model_dump(exclude_unset=True)
    start = data.get("access_starts_at")
    end = data.get("access_expires_at")
    if start and end and start >= end:
        raise HTTPException(422, "Início deve anteceder vencimento.")
    c = m.Clinic(**data)
''',
    '''    data = body.model_dump(exclude_unset=True)
    if data.get("plan_code") == "lifetime":
        data["access_expires_at"] = None
    start = data.get("access_starts_at")
    end = data.get("access_expires_at")
    if start and end and utc(start) >= utc(end):
        raise HTTPException(422, "Início deve anteceder vencimento.")
    c = m.Clinic(**data)
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''    data = body.model_dump(exclude_unset=True)
    start = data.get("access_starts_at", c.access_starts_at)
    end = data.get("access_expires_at", c.access_expires_at)
    if start and end and utc(start) >= utc(end):
''',
    '''    data = body.model_dump(exclude_unset=True)
    if data.get("plan_code", c.plan_code) == "lifetime":
        data["access_expires_at"] = None
    start = data.get("access_starts_at", c.access_starts_at)
    end = data.get("access_expires_at", c.access_expires_at)
    if start and end and utc(start) >= utc(end):
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''    c = lock_clinic(db, identifier)
    base = m.now() if body.trial else max(m.now(), utc(c.access_expires_at) or m.now())
    c.access_expires_at = base + timedelta(days=7 if body.trial else body.days)
    c.access_starts_at = m.now() if body.trial else c.access_starts_at
    c.is_active = True
    c.subscription_status = "trial" if body.trial else "active"
    if body.trial:
        c.plan_code = "trial"
''',
    '''    c = lock_clinic(db, identifier)
    if body.trial:
        c.access_expires_at = m.now() + timedelta(days=7)
        c.access_starts_at = m.now()
        c.plan_code = "trial"
    elif c.plan_code == "lifetime":
        c.access_expires_at = None
    else:
        base = max(m.now(), utc(c.access_expires_at) or m.now())
        c.access_expires_at = base + timedelta(days=body.days)
    c.is_active = True
    c.subscription_status = "trial" if body.trial else "active"
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''        {
            "days": 7 if body.trial else body.days,
            "expires_at": c.access_expires_at.isoformat(),
        },
''',
    '''        {
            "days": 7 if body.trial else body.days,
            "expires_at": c.access_expires_at.isoformat()
            if c.access_expires_at
            else None,
        },
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''    clinic = lock_clinic(db, body.clinic_id or actor.clinic_id)
    if clinic.is_demo and body.role == "platform_admin":
        raise HTTPException(403, "Administrador global não pertence à demonstração.")
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
''',
    '''    clinic = lock_clinic(db, body.clinic_id or actor.clinic_id)
    if clinic.is_demo and body.role == "platform_admin":
        raise HTTPException(403, "Administrador global não pertence à demonstração.")
    if body.is_active:
        check_capacity(db, clinic)
    if db.scalar(select(m.User.id).where(m.User.email == body.email.lower())):
        raise HTTPException(409, "Não foi possível cadastrar este e-mail.")
    if (
        body.access_starts_at
        and body.access_expires_at
        and utc(body.access_starts_at) >= utc(body.access_expires_at)
    ):
        raise HTTPException(422, "Início deve anteceder vencimento.")
    u = m.User(
        name=body.name,
        email=body.email.lower(),
        role=body.role,
        clinic_id=clinic.id,
        password_hash=hasher.hash(body.password),
        is_active=body.is_active,
        access_starts_at=body.access_starts_at,
        access_expires_at=body.access_expires_at,
    )
''',
)

replace_once(
    "backend/app/api_admin.py",
    '''    if body.is_active is True and not u.is_active:
        check_capacity(db, clinic, u.id)
    old_active = u.is_active
    old_role = u.role
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(u, key, value)
''',
    '''    if body.is_active is True and not u.is_active:
        check_capacity(db, clinic, u.id)
    data = body.model_dump(exclude_unset=True)
    start = data.get("access_starts_at", u.access_starts_at)
    end = data.get("access_expires_at", u.access_expires_at)
    if start and end and utc(start) >= utc(end):
        raise HTTPException(422, "Início deve anteceder vencimento.")
    old_active = u.is_active
    old_role = u.role
    for key, value in data.items():
        setattr(u, key, value)
''',
)

write(
    "backend/migrations/versions/9e160926_user_access_start.py",
    '''"""Add optional per-user access start override."""

import sqlalchemy as sa
from alembic import op

revision = "9e1609260000"
down_revision = "8d402b230000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("access_starts_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("users", "access_starts_at")
''',
)

insert_tests = '''\n\ndef _fresh_login(email: str):
    with TestClient(
        app,
        headers={"X-Requested-With": "Biometria", "Origin": "http://localhost:3000"},
    ) as fresh:
        return fresh.post(
            "/auth/login",
            json={"email": email, "password": "Test-password-123"},
        )


def _platform_user(platform, clinic_id: str, email: str, **overrides):
    body = {
        "name": "Access Regression",
        "email": email,
        "password": "Test-password-123",
        "role": "physiotherapist",
        "clinic_id": clinic_id,
    }
    body.update(overrides)
    response = platform.post("/platform/users", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_new_user_lifetime_without_override_logs_in_immediately(platform):
    future = m.now() + timedelta(days=1)
    clinic = platform.post(
        "/platform/clinics",
        json={
            "name": "Lifetime immediate access",
            "plan_code": "lifetime",
            "subscription_status": "active",
            "access_starts_at": future.isoformat(),
            "access_expires_at": (future + timedelta(days=30)).isoformat(),
        },
    )
    assert clinic.status_code == 201
    clinic = clinic.json()
    assert clinic["access_expires_at"] is None
    user = _platform_user(
        platform,
        clinic["id"],
        "lifetime-immediate@test.local",
        access_starts_at=None,
        access_expires_at=None,
    )
    assert user["access_starts_at"] is None
    assert user["access"]["allowed"] is True
    assert _fresh_login("lifetime-immediate@test.local").status_code == 200


def test_new_user_monthly_inherits_clinic_window(platform):
    now = m.now()
    clinic = platform.post(
        "/platform/clinics",
        json={
            "name": "Monthly inherited access",
            "plan_code": "monthly",
            "subscription_status": "active",
            "access_starts_at": (now - timedelta(days=1)).isoformat(),
            "access_expires_at": (now + timedelta(days=30)).isoformat(),
        },
    ).json()
    user = _platform_user(platform, clinic["id"], "monthly-inherit@test.local")
    assert user["access_starts_at"] is None
    assert user["access"]["allowed"] is True
    assert _fresh_login("monthly-inherit@test.local").status_code == 200


def test_user_explicit_start_blocks_then_allows_same_account(platform):
    clinic = platform.post(
        "/platform/clinics",
        json={"name": "Explicit user start", "plan_code": "lifetime"},
    ).json()
    user = _platform_user(
        platform,
        clinic["id"],
        "future-user@test.local",
        access_starts_at=(m.now() + timedelta(days=1)).isoformat(),
    )
    denied = _fresh_login("future-user@test.local")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "access_not_started"
    updated = platform.patch(
        "/platform/users/" + user["id"],
        json={"access_starts_at": (m.now() - timedelta(seconds=1)).isoformat()},
    )
    assert updated.status_code == 200
    assert updated.json()["access"]["allowed"] is True
    assert _fresh_login("future-user@test.local").status_code == 200


def test_access_policy_distinguishes_user_and_clinic_blocks(platform):
    clinic = platform.post(
        "/platform/clinics",
        json={"name": "Access state ordering", "plan_code": "monthly"},
    ).json()
    user = _platform_user(platform, clinic["id"], "states@test.local")

    assert platform.patch(
        "/platform/users/" + user["id"], json={"is_active": False}
    ).status_code == 200
    denied = _fresh_login("states@test.local")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "account_disabled"

    assert platform.patch(
        "/platform/users/" + user["id"], json={"is_active": True}
    ).status_code == 200
    assert platform.patch(
        "/platform/clinics/" + clinic["id"],
        json={"subscription_status": "suspended"},
    ).status_code == 200
    denied = _fresh_login("states@test.local")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "clinic_suspended"

    assert platform.patch(
        "/platform/clinics/" + clinic["id"],
        json={"subscription_status": "active", "is_active": True},
    ).status_code == 200
    assert platform.patch(
        "/platform/users/" + user["id"],
        json={"access_expires_at": (m.now() - timedelta(seconds=1)).isoformat()},
    ).status_code == 200
    denied = _fresh_login("states@test.local")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "user_access_expired"


def test_access_start_timezone_boundary_is_compared_once():
    local = timezone(timedelta(hours=-3))
    user = m.User(
        role="physiotherapist",
        is_active=True,
        access_starts_at=datetime(2026, 9, 16, 0, 30, tzinfo=local),
    )
    clinic = m.Clinic(
        is_active=True,
        plan_code="monthly",
        subscription_status="active",
    )
    before = datetime(2026, 9, 16, 3, 29, 59, tzinfo=timezone.utc)
    boundary = datetime(2026, 9, 16, 3, 30, tzinfo=timezone.utc)
    assert access_state(user, clinic, before)["code"] == "access_not_started"
    assert access_state(user, clinic, boundary)["code"] is None


def test_platform_admin_and_demo_access_regressions():
    global_admin = m.User(role="platform_admin", is_active=True)
    blocked_clinic = m.Clinic(
        is_active=False,
        plan_code="monthly",
        subscription_status="suspended",
        access_starts_at=NOW + timedelta(days=1),
    )
    assert access_state(global_admin, blocked_clinic, NOW)["allowed"] is True

    demo_user = m.User(role="physiotherapist", is_active=True)
    demo = m.Clinic(
        is_demo=True,
        is_active=True,
        plan_code="trial",
        subscription_status="expired",
        access_starts_at=NOW + timedelta(days=1),
        access_expires_at=NOW - timedelta(days=1),
    )
    assert access_state(demo_user, demo, NOW)["allowed"] is True


def test_user_access_start_requires_timezone(platform):
    clinic = platform.post(
        "/platform/clinics",
        json={"name": "Aware user dates", "plan_code": "lifetime"},
    ).json()
    response = platform.post(
        "/platform/users",
        json={
            "name": "Naive date",
            "email": "naive-date@test.local",
            "password": "Test-password-123",
            "clinic_id": clinic["id"],
            "access_starts_at": "2026-09-16T00:30:00",
        },
    )
    assert response.status_code == 422
'''
replace_once(
    "backend/tests/test_access_admin.py",
    "\n\nclass FakeS3:\n",
    insert_tests + "\n\nclass FakeS3:\n",
)

write(
    "frontend/lib/access-datetime.ts",
    '''export function toUtcIso(
  value: FormDataEntryValue | string | null,
): string | null {
  const raw = value === null ? "" : String(value).trim();
  if (!raw) return null;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) throw new Error("Data inválida.");
  return parsed.toISOString();
}

export function toDatetimeLocal(value: string | null): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
''',
)

write(
    "frontend/tests/access-datetime.test.ts",
    '''import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { toDatetimeLocal, toUtcIso } from "../lib/access-datetime";

const originalTimezone = process.env.TZ;

beforeAll(() => {
  process.env.TZ = "America/Bahia";
});

afterAll(() => {
  process.env.TZ = originalTimezone;
});

describe("access datetime serialization", () => {
  it("keeps empty access start as inheritance", () => {
    expect(toUtcIso("")).toBeNull();
    expect(toUtcIso(null)).toBeNull();
  });

  it("round-trips a local datetime without applying the offset twice", () => {
    const local = "2026-09-16T09:45";
    expect(toDatetimeLocal(toUtcIso(local))).toBe(local);
  });

  it("keeps the local calendar day near midnight in Bahia", () => {
    expect(toUtcIso("2026-09-16T00:30")).toBe("2026-09-16T03:30:00.000Z");
    expect(toDatetimeLocal("2026-09-16T03:30:00.000Z")).toBe(
      "2026-09-16T00:30",
    );
  });
});
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''import { api, post } from "@/lib/api";
import KinuaLogo from "./brand/KinuaLogo";
''',
    '''import { api, post } from "@/lib/api";
import { toDatetimeLocal, toUtcIso } from "@/lib/access-datetime";
import KinuaLogo from "./brand/KinuaLogo";
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''  is_active: boolean;
  access_expires_at: string | null;
  last_login_at: string | null;
''',
    '''  is_active: boolean;
  access_starts_at: string | null;
  access_expires_at: string | null;
  last_login_at: string | null;
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''const inputDate = (v: string | null) =>
  v
    ? new Date(new Date(v).getTime() - new Date(v).getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16)
    : "";
const iso = (v: FormDataEntryValue | null) =>
  v ? new Date(String(v)).toISOString() : null;
''',
    '''const inputDate = toDatetimeLocal;
const iso = toUtcIso;
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''    access.code === "subscription_cancelled"
      ? "CANCELADO"
      : access.code?.includes("expired")
        ? "EXPIRADO"
        : !access.allowed
          ? "SUSPENSO"
''',
    '''    access.code === "subscription_cancelled"
      ? "CANCELADO"
      : access.code?.includes("expired")
        ? "EXPIRADO"
        : access.code === "access_not_started"
          ? "NÃO INICIADO"
          : !access.allowed
            ? "SUSPENSO"
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''          role: f.get("role"),
          is_active: f.get("is_active") === "true",
          access_expires_at: iso(f.get("access_expires_at")),
          suspension_reason: f.get("suspension_reason") || null,
''',
    '''          role: f.get("role"),
          is_active: f.get("is_active") === "true",
          access_starts_at: iso(f.get("access_starts_at")),
          access_expires_at: iso(f.get("access_expires_at")),
          suspension_reason: f.get("suspension_reason") || null,
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''          password: f.get("password"),
          role: f.get("role"),
          ...(platform ? { clinic_id: f.get("clinic_id") } : {}),
''',
    '''          password: f.get("password"),
          role: f.get("role"),
          is_active: true,
          access_starts_at: iso(f.get("access_starts_at")),
          access_expires_at: iso(f.get("access_expires_at")),
          ...(platform ? { clinic_id: f.get("clinic_id") } : {}),
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''            <option value="user_access_expired">Expiração individual</option>
            <option value="subscription_expired">Assinatura expirada</option>
            <option value="clinic_suspended">Clínica suspensa</option>
''',
    '''            <option value="user_access_expired">Expiração individual</option>
            <option value="subscription_expired">Assinatura expirada</option>
            <option value="access_not_started">Acesso ainda não iniciado</option>
            <option value="clinic_suspended">Clínica suspensa</option>
''',
)

replace_once(
    "frontend/components/PlatformAdmin.tsx",
    '''          <label>
            Permissão
            <select
              name="role"
              defaultValue={selected?.role || "physiotherapist"}
            >
              <option value="physiotherapist">Fisioterapeuta</option>
              <option value="admin">Administrador da clínica</option>
              {platform && (
                <option value="platform_admin">Administrador global</option>
              )}
            </select>
          </label>
          {selected && (
            <>
              <label>
                Estado
                <select
                  name="is_active"
                  defaultValue={String(selected.is_active)}
                >
                  <option value="true">Ativo</option>
                  <option value="false">Suspenso</option>
                </select>
              </label>
              <label>
                Expiração individual (vazio segue clínica)
                <input
                  name="access_expires_at"
                  type="datetime-local"
                  defaultValue={inputDate(selected.access_expires_at)}
                />
              </label>
              <label>
                Motivo da suspensão
                <input name="suspension_reason" maxLength={2000} />
              </label>
            </>
          )}
''',
    '''          <label>
            Permissão
            <select
              name="role"
              defaultValue={selected?.role || "physiotherapist"}
            >
              <option value="physiotherapist">Fisioterapeuta</option>
              <option value="admin">Administrador da clínica</option>
              {platform && (
                <option value="platform_admin">Administrador global</option>
              )}
            </select>
          </label>
          <label>
            Início individual (vazio segue clínica)
            <input
              name="access_starts_at"
              type="datetime-local"
              defaultValue={inputDate(selected?.access_starts_at || null)}
            />
          </label>
          <label>
            Expiração individual (vazio segue clínica)
            <input
              name="access_expires_at"
              type="datetime-local"
              defaultValue={inputDate(selected?.access_expires_at || null)}
            />
          </label>
          {selected && (
            <>
              <label>
                Estado
                <select
                  name="is_active"
                  defaultValue={String(selected.is_active)}
                >
                  <option value="true">Ativo</option>
                  <option value="false">Suspenso</option>
                </select>
              </label>
              <label>
                Motivo da suspensão
                <input name="suspension_reason" maxLength={2000} />
              </label>
            </>
          )}
''',
)

replace_once(
    "frontend/e2e/access.spec.ts",
    '''import { test, expect, Page } from "@playwright/test";
test("platform administration, trial, tenant workflow, suspension, expiry and extension", async ({
''',
    '''import { test, expect, Page } from "@playwright/test";

test.use({ timezoneId: "America/Bahia" });

test("platform administration, trial, tenant workflow, suspension, expiry and extension", async ({
''',
)

replace_once(
    "frontend/e2e/access.spec.ts",
    '''  await page.getByLabel("Nome da clínica").fill(clinicName);
  await page
    .getByRole("button", { name: "Salvar clínica", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: clinicName });
  await row.getByRole("button", { name: "Gerenciar clínica" }).click();
  await page.getByRole("button", { name: "Teste 7 dias", exact: true }).click();
  await expect(row.getByText("TESTE", { exact: true })).toBeVisible();
''',
    '''  await page.getByLabel("Nome da clínica").fill(clinicName);
  await page.getByLabel("Plano", { exact: true }).selectOption("lifetime");
  await page
    .getByRole("button", { name: "Salvar clínica", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: clinicName });
  await expect(row.getByText("ILIMITADO", { exact: true })).toBeVisible();
''',
)

replace_once(
    "frontend/e2e/access.spec.ts",
    '''  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  expect((await createdUser).status()).toBe(201);
  await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible({
''',
    '''  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  const createdUserResponse = await createdUser;
  expect(createdUserResponse.status()).toBe(201);
  expect(createdUserResponse.request().postDataJSON()).toMatchObject({
    access_starts_at: null,
    access_expires_at: null,
  });
  await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible({
''',
)

future_flow = '''\n  const futureEmail = "future" + suffix + "@qa.local";
  await page.getByLabel("Nome", { exact: true }).fill("Future QA " + suffix);
  await page.getByLabel("E-mail", { exact: true }).fill(futureEmail);
  await page.getByLabel("Senha inicial").fill(password);
  await page
    .getByRole("combobox", { name: "Clínica", exact: true })
    .selectOption(clinic.id);
  await page
    .getByLabel("Início individual (vazio segue clínica)")
    .fill("2099-01-15T00:30");
  const futureCreated = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/platform/users") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Cadastrar usuário" }).click();
  const futureResponse = await futureCreated;
  expect(futureResponse.status()).toBe(201);
  expect(futureResponse.request().postDataJSON().access_starts_at).toBe(
    "2099-01-15T03:30:00.000Z",
  );
  const futureMembers = await (
    await page.request.get("/api/platform/users?q=" + futureEmail)
  ).json();
  const futureUser = futureMembers[0];
  const futureContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL,
    timezoneId: "America/Bahia",
  });
  const futurePage = await futureContext.newPage();
  await login(futurePage, futureEmail);
  await expect(
    futurePage.getByRole("heading", { name: "Seu acesso ainda não iniciou" }),
  ).toBeVisible();
  expect(
    (
      await page.request.patch("/api/platform/users/" + futureUser.id, {
        headers,
        data: { access_starts_at: new Date(Date.now() - 60000).toISOString() },
      })
    ).status(),
  ).toBe(200);
  await login(futurePage, futureEmail);
  await expect(futurePage.getByRole("heading", { name: /Olá,/ })).toBeVisible();
  await futureContext.close();
'''
replace_once(
    "frontend/e2e/access.spec.ts",
    '''  const user = members[0];
  const context = await browser.newContext({
''',
    '''  const user = members[0];
''' + future_flow + '''  const context = await browser.newContext({
''',
)

replace_once(
    "frontend/e2e/access.spec.ts",
    '''        data: {
          access_starts_at: null,
          access_expires_at: new Date(Date.now() - 60000).toISOString(),
        },
''',
    '''        data: {
          plan_code: "monthly",
          access_starts_at: null,
          access_expires_at: new Date(Date.now() - 60000).toISOString(),
        },
''',
)

print("access activation patch applied")
