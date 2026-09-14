import io
import sys
from datetime import timedelta

import pytest
from pypdf import PdfReader
from sqlalchemy import select
from test_access_admin import FakeS3
from test_api import assessment, patient, upload
from test_protocols_rom import catalog  # noqa: F401

from app import demo_seed, storage
from app import models as m
from app.core.access import access_state
from app.core.config import settings
from app.core.database import Base
from app.storage import S3StorageProvider

PASSWORD = "Demo-test-password-123"


@pytest.fixture
def demo(db, monkeypatch):
    monkeypatch.setattr(settings(), "allow_demo_seed", True)
    return demo_seed.seed_demo(db, "demo@test.local", PASSWORD)


def login(client):
    result = client.post(
        "/auth/login", json={"email": "demo@test.local", "password": PASSWORD}
    )
    assert result.status_code == 200, result.text
    return client


def test_seed_flag_required(db):
    with pytest.raises(ValueError, match="ALLOW_DEMO_SEED"):
        demo_seed.seed_demo(db, "demo@test.local", PASSWORD)
    with db() as s:
        assert not s.scalar(select(m.Clinic.id).where(m.Clinic.is_demo.is_(True)))


def test_normal_bootstrap_no_synthetic(db, monkeypatch):
    from app import seed

    monkeypatch.setattr(seed, "SessionLocal", db)
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", PASSWORD)
    monkeypatch.setattr(
        sys, "argv", ["seed", "--platform-admin", "--email", "new-global@test.local"]
    )
    seed.main()
    with db() as s:
        assert not s.scalar(select(m.Patient.id))
        assert not s.scalar(select(m.Assessment.id))
        assert not s.scalar(select(m.Clinic.id).where(m.Clinic.is_demo.is_(True)))


def test_legacy_demo_refused(monkeypatch):
    from app import seed

    monkeypatch.setattr(sys, "argv", ["seed", "--demo"])
    with pytest.raises(SystemExit, match="desativado"):
        seed.main()


def test_demo_created_and_idempotent(db, demo, client):
    login(client)
    assert client.get("/auth/me").json()["is_demo"] is True
    assert len(client.get("/patients").json()) == 3
    with db() as s:
        user = s.scalar(select(m.User).where(m.User.email == "demo@test.local"))
        original = user.password_hash
        assert s.get(m.Clinic, demo).plan_code == "custom"
        assert not s.scalar(select(m.Analysis.id))
        assert not s.scalar(select(m.AssessmentMedia.id))
    assert demo_seed.seed_demo(db, "demo@test.local", PASSWORD) == demo
    with db() as s:
        assert s.get(m.User, user.id).password_hash == original


@pytest.mark.parametrize("mode", ["production", "demo", "development"])
def test_app_mode_no_auth_bypass(db, demo, client, monkeypatch, mode):
    monkeypatch.setattr(settings(), "app_mode", mode)
    login(client)
    assert client.get("/platform/dashboard").status_code == 403
    assert (
        client.post(
            "/admin/users",
            json={
                "name": "No Global",
                "email": "no@test.local",
                "password": PASSWORD,
                "role": "platform_admin",
            },
        ).status_code
        == 403
    )
    assert (
        client.patch("/admin/users/user-1", json={"is_active": False}).status_code
        == 404
    )
    with db() as s:
        c = s.get(m.Clinic, "clinic-1")
        c.access_expires_at = m.now() - timedelta(seconds=1)
        s.commit()
    assert (
        client.post(
            "/auth/login",
            json={"email": "user1@test.local", "password": "Test-password-123"},
        ).json()["detail"]["code"]
        == "subscription_expired"
    )


def test_demo_subscription_exception_is_explicit(db, demo):
    with db() as s:
        c = s.get(m.Clinic, demo)
        c.subscription_status = "expired"
        c.access_expires_at = m.now() - timedelta(days=2)
        u = s.scalar(select(m.User).where(m.User.clinic_id == demo))
        assert access_state(u, c)["allowed"]
        c.is_active = False
        assert access_state(u, c)["code"] == "clinic_suspended"
        c.is_active = True
        u.is_active = False
        assert access_state(u, c)["code"] == "account_disabled"


def test_demo_cannot_target_real_email(db, demo):
    with pytest.raises(ValueError, match="não demonstrativa"):
        demo_seed.seed_demo(db, "user1@test.local", PASSWORD, reset=True)


@pytest.mark.usefixtures("catalog")
def test_demo_reset_preserves_other_tenant_and_media(
    db, demo, auth, monkeypatch, landmarks
):
    # Keep a production patient, assessment, media, session and report.
    a = assessment(auth)
    prod_media = upload(auth, a)
    auth.get("/assessments/" + a["id"] + "/report")
    with db() as s:
        before = {
            t.name: list(s.execute(select(t)).mappings())
            for t in Base.metadata.sorted_tables
            if t.name != "demo_media_cleanup"
        }
        prod_key = s.get(m.AssessmentMedia, prod_media["id"]).storage_key
    login(auth)
    a = assessment(auth)
    media = upload(auth, a)
    # The real calculation pipeline receives explicit authorized synthetic test landmarks.
    result = auth.post(
        "/assessments/" + a["id"] + "/analyze",
        json={
            "media_id": media["id"],
            "landmarks": landmarks,
            "provider": "MediaPipePoseProvider",
            "provider_version": "fixture/1",
            "camera_level_confirmed": True,
            "view_confirmed": True,
        },
    )
    assert result.status_code == 201, result.text
    findings = auth.get("/assessments/" + a["id"]).json()["analyses"][0]["findings"]
    for finding in findings:
        assert (
            auth.post(
                "/findings/" + finding["id"] + "/review",
                json={
                    "state": "professional_confirmed",
                    "note": "Revisão sintética QA",
                },
            ).status_code
            == 200
        )
    auth.get("/assessments/" + a["id"] + "/report")
    p = patient(auth)
    run = auth.post(
        "/assessment-protocols",
        json={"patient_id": p["id"], "version_id": "knee@1.0.0"},
    )
    assert run.status_code == 201
    rom = auth.post(
        "/rom/assessments",
        json={"patient_id": p["id"], "movement": "knee_flexion", "side": "right"},
    )
    assert rom.status_code == 201, rom.text
    with db() as s:
        demo_key = s.get(m.AssessmentMedia, media["id"]).storage_key
        assert demo_key.startswith("demo/" + demo + "/")
    demo_seed.seed_demo(db, "demo@test.local", PASSWORD, reset=True)
    assert auth.get("/patients").status_code == 401
    assert storage.LocalStorageProvider().path(prod_key).exists()
    assert not storage.LocalStorageProvider().path(demo_key).exists()
    with db() as s:
        # Every pre-existing non-demo row is byte-for-byte identical.
        for t in Base.metadata.sorted_tables:
            if t.name not in before:
                continue
            pk = list(t.primary_key)[0]
            for row in before[t.name]:
                if t.name == "clinics" and row["id"] == demo:
                    continue
                # baseline included bootstrap demo data; only compare production ownership.
                if (
                    t.name in ("users", "patients", "assessments", "audit_logs")
                    and row.get("clinic_id") == demo
                ):
                    continue
                if t.name == "professionals" and row["registration"] == "DEMONSTRAÇÃO":
                    continue
                current = (
                    s.execute(select(t).where(pk == row[pk.name])).mappings().first()
                )
                assert current == row, (t.name, row[pk.name])
        assert not s.scalar(select(m.DemoMediaCleanup.id))


def test_reset_rolls_back_before_storage_delete(db, demo, client, monkeypatch):
    login(client)
    a = assessment(client)
    media = upload(client, a)
    with db() as s:
        key = s.get(m.AssessmentMedia, media["id"]).storage_key
        patient_ids = list(
            s.scalars(select(m.Patient.id).where(m.Patient.clinic_id == demo))
        )
    original = demo_seed.reset_rows

    def fail_after_rows(s, c):
        original(s, c)
        raise RuntimeError("injected")

    monkeypatch.setattr(demo_seed, "reset_rows", fail_after_rows)
    with pytest.raises(RuntimeError):
        demo_seed.seed_demo(db, "demo@test.local", PASSWORD, True)
    with db() as s:
        assert (
            list(s.scalars(select(m.Patient.id).where(m.Patient.clinic_id == demo)))
            == patient_ids
        )
        assert s.get(m.AssessmentMedia, media["id"])
    assert storage.LocalStorageProvider().path(key).exists()


@pytest.mark.parametrize("demo_mark", [True, False])
def test_pdf_tenant_mark(db, auth, demo, demo_mark):
    if demo_mark:
        login(auth)
    a = assessment(auth)
    response = auth.get("/assessments/" + a["id"] + "/report")
    assert response.status_code == 200
    text = "".join(
        p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages
    )
    assert ("DEMONSTRAÇÃO — DADOS FICTÍCIOS" in text) == demo_mark


def test_metrics_and_filters_exclude_demo(db, demo, client):
    with db() as s:
        u = s.get(m.User, "user-1")
        u.role = "platform_admin"
        s.commit()
    client.post(
        "/auth/login",
        json={"email": "user1@test.local", "password": "Test-password-123"},
    )
    data = client.get("/platform/dashboard").json()
    assert (
        data["total_clinics"] == 3
        and data["production_clinics"] == 2
        and data["demo_clinics"] == 1
    )
    assert data["active_clinics"] == 2
    assert data["active_users"] == 2
    assert [c["id"] for c in client.get("/platform/clinics?mode=demo").json()] == [demo]
    assert all(
        not c["is_demo"] for c in client.get("/platform/clinics?mode=production").json()
    )
    assert (
        client.patch("/platform/clinics/clinic-1", json={"is_demo": True}).status_code
        == 422
    )


def test_s3_prefix_reset_and_retry(db, demo, client, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(settings(), "storage_backend", "s3")
    monkeypatch.setattr(storage, "S3StorageProvider", lambda: storage_provider(fake))
    production_key = "production/preserved.jpg"
    fake.objects[production_key] = b"production"
    login(client)
    a = assessment(client)
    media = upload(client, a)
    with db() as s:
        key = s.get(m.AssessmentMedia, media["id"]).storage_key
    original = fake.delete_object

    def fail(**kwargs):
        raise RuntimeError("storage unavailable")

    fake.delete_object = fail
    with pytest.raises(RuntimeError):
        demo_seed.seed_demo(db, "demo@test.local", PASSWORD, True)
    with db() as s:
        assert s.scalar(select(m.DemoMediaCleanup.id))
    assert fake.objects[production_key] == b"production"
    fake.delete_object = original
    demo_seed.seed_demo(db, "demo@test.local", PASSWORD)
    assert key not in fake.objects and fake.objects[production_key] == b"production"


def storage_provider(fake):
    return S3StorageProvider(fake, "private")


@pytest.mark.parametrize(
    "key",
    [
        "production/safe.jpg",
        "demo/another/key.jpg",
        "../secret.jpg",
        "demo/wrong/../key.jpg",
    ],
)
def test_reset_prefix_rejects_foreign_objects(key):
    with pytest.raises(ValueError):
        demo_seed.demo_key(key, "target")


def test_reset_refuses_global_admin(db, demo):
    with db() as s:
        u = s.scalar(select(m.User).where(m.User.clinic_id == demo))
        u.role = "platform_admin"
        s.commit()
    with pytest.raises(ValueError):
        demo_seed.seed_demo(db, "demo@test.local", PASSWORD, True)


def test_cli_validation_does_not_echo_password(db, monkeypatch):
    monkeypatch.setattr(settings(), "allow_demo_seed", True)
    monkeypatch.setenv("DEMO_PASSWORD", "tiny")
    monkeypatch.setattr(sys, "argv", ["demo_seed", "--email", "demo@test.local"])
    with pytest.raises(SystemExit) as error:
        demo_seed.main()
    assert "tiny" not in str(error.value)
    assert "Dados inválidos" in str(error.value)


def test_reset_refuses_cross_tenant_reference(db, demo):
    with db() as s:
        demo_user = s.scalar(select(m.User).where(m.User.clinic_id == demo))
        s.add(
            m.AuditLog(
                clinic_id="clinic-1",
                actor_id=demo_user.id,
                action="test.reference",
                resource_id="fixture",
            )
        )
        s.commit()
    with pytest.raises(ValueError, match="externa"):
        demo_seed.seed_demo(db, "demo@test.local", PASSWORD, True)
    with db() as s:
        assert (
            len(list(s.scalars(select(m.Patient).where(m.Patient.clinic_id == demo))))
            == 3
        )
        assert s.get(m.User, demo_user.id)
