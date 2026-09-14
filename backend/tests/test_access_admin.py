import io
from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app import models as m
from app.core.access import access_state
from app.core.security import hasher
from app.main import app
from app.storage import S3StorageProvider

NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "user_data,clinic_data,code",
    [
        ({}, {}, None),
        ({"is_active": False}, {}, "account_disabled"),
        ({"access_expires_at": NOW}, {}, "user_access_expired"),
        ({"access_expires_at": NOW - timedelta(seconds=1)}, {}, "user_access_expired"),
        ({}, {"is_active": False}, "clinic_suspended"),
        ({}, {"subscription_status": "suspended"}, "clinic_suspended"),
        ({}, {"subscription_status": "cancelled"}, "subscription_cancelled"),
        ({}, {"subscription_status": "expired"}, "subscription_expired"),
        ({}, {"access_expires_at": NOW}, "subscription_expired"),
        ({}, {"access_expires_at": NOW + timedelta(seconds=1)}, None),
        ({}, {"access_starts_at": NOW + timedelta(days=1)}, "access_not_started"),
        (
            {"role": "platform_admin", "access_expires_at": NOW},
            {"is_active": False},
            None,
        ),
        ({"role": "platform_admin", "is_active": False}, {}, "account_disabled"),
        (
            {"access_expires_at": NOW + timedelta(days=9)},
            {"access_expires_at": NOW},
            "subscription_expired",
        ),
    ],
)
def test_central_access(user_data, clinic_data, code):
    u = m.User(**({"role": "physiotherapist", "is_active": True} | user_data))
    c = m.Clinic(
        **(
            {"is_active": True, "plan_code": "custom", "subscription_status": "active"}
            | clinic_data
        )
    )
    assert access_state(u, c, NOW)["code"] == code


@pytest.fixture
def platform(client, db):
    with db() as session:
        session.add(
            m.User(
                id="global",
                clinic_id="clinic-1",
                email="global@test.local",
                name="Global QA",
                role="platform_admin",
                password_hash=hasher.hash("Test-password-123"),
            )
        )
        session.commit()
    assert (
        client.post(
            "/auth/login",
            json={"email": "global@test.local", "password": "Test-password-123"},
        ).status_code
        == 200
    )
    return client


def test_platform_no_clinical_access(platform):
    for path in [
        "/patients",
        "/dashboard",
        "/admin/audit",
        "/protocols",
        "/rom/movements",
    ]:
        assert platform.get(path).status_code == 403
    assert platform.get("/platform/dashboard").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/platform/users", "/platform/clinics", "/platform/dashboard", "/platform/audit"],
)
def test_clinic_admin_cannot_global(auth, path):
    assert auth.get(path).status_code == 403


def test_clinic_admin_idor(auth):
    assert (
        auth.patch("/admin/users/user-2", json={"is_active": False}).status_code == 404
    )
    assert (
        auth.patch("/admin/users/user-1", json={"role": "platform_admin"}).status_code
        == 403
    )
    assert (
        auth.post(
            "/admin/users",
            json={
                "name": "Invalid",
                "email": "other@test.local",
                "password": "Test-password-123",
                "clinic_id": "clinic-2",
            },
        ).status_code
        == 403
    )
    assert (
        auth.post(
            "/admin/users",
            json={
                "name": "Invalid",
                "email": "other@test.local",
                "password": "Test-password-123",
                "role": "platform_admin",
            },
        ).status_code
        == 403
    )
    assert all(u["clinic_id"] == "clinic-1" for u in auth.get("/admin/users").json())


def test_physiotherapist_denied(client):
    client.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert client.get("/admin/users").status_code == 403
    assert client.get("/platform/users").status_code == 403


def test_last_global_admin(platform):
    assert (
        platform.patch("/platform/users/global", json={"is_active": False}).status_code
        == 409
    )
    assert (
        platform.patch("/platform/users/global", json={"role": "admin"}).status_code
        == 409
    )
    assert platform.get("/auth/me").status_code == 200


@pytest.mark.parametrize("days", [7, 30, 90, 365])
def test_extend(platform, days):
    c = platform.post(
        "/platform/clinics", json={"name": "Clinic Trial", "plan_code": "trial"}
    ).json()
    r = platform.post("/platform/clinics/" + c["id"] + "/extend", json={"days": days})
    assert r.status_code == 200
    assert r.json()["access"]["days_remaining"] == days
    assert (
        platform.patch(
            "/platform/clinics/" + c["id"],
            json={"plan_code": "lifetime", "access_expires_at": None},
        ).json()["access"]["days_remaining"]
        is None
    )


def test_administration_flow(platform, db):
    c = platform.post(
        "/platform/clinics", json={"name": "Clinic QA", "max_users": 2}
    ).json()
    identifier = c["id"]
    assert (
        platform.post(
            f"/platform/clinics/{identifier}/extend", json={"trial": True, "days": 7}
        ).json()["plan_code"]
        == "trial"
    )
    u = platform.post(
        "/platform/users",
        json={
            "name": "Clinic Admin",
            "email": "clinic@test.local",
            "password": "Test-password-123",
            "role": "admin",
            "clinic_id": identifier,
        },
    ).json()
    with TestClient(app, headers={"X-Requested-With": "Biometria"}) as clinic:
        assert (
            clinic.post(
                "/auth/login",
                json={"email": "clinic@test.local", "password": "Test-password-123"},
            ).status_code
            == 200
        )
        professional = clinic.post(
            "/admin/users",
            json={
                "name": "Physio QA",
                "email": "physio@test.local",
                "password": "Test-password-123",
            },
        )
        assert professional.status_code == 201
        assert (
            clinic.post(
                "/admin/users",
                json={
                    "name": "Overflow",
                    "email": "overflow@test.local",
                    "password": "Test-password-123",
                },
            ).status_code
            == 409
        )
        patient = clinic.post(
            "/patients",
            json={"name": "Fake Patient", "birth_date": "1990-01-01"},
        )
        assert patient.status_code == 201
        assert (
            platform.patch(
                "/platform/users/" + u["id"], json={"is_active": False}
            ).status_code
            == 200
        )
        assert clinic.get("/patients").status_code == 401
        assert (
            clinic.post(
                "/auth/login",
                json={"email": "clinic@test.local", "password": "Test-password-123"},
            ).json()["detail"]["code"]
            == "account_disabled"
        )
        assert (
            platform.patch(
                "/platform/users/" + u["id"], json={"is_active": True}
            ).status_code
            == 200
        )
        assert (
            clinic.post(
                "/auth/login",
                json={"email": "clinic@test.local", "password": "Test-password-123"},
            ).status_code
            == 200
        )
        assert (
            platform.patch(
                "/platform/clinics/" + identifier,
                json={
                    "access_starts_at": None,
                    "access_expires_at": (m.now() - timedelta(seconds=1)).isoformat(),
                },
            ).status_code
            == 200
        )
        assert (
            clinic.get("/patients").json()["detail"]["code"] == "subscription_expired"
        )
        platform.post("/platform/clinics/" + identifier + "/extend", json={"days": 30})
        assert clinic.get("/patients").status_code == 200
        assert (
            platform.patch(
                "/platform/clinics/" + identifier,
                json={"subscription_status": "suspended"},
            ).status_code
            == 200
        )
        assert clinic.get("/patients").status_code == 401
    logs = platform.get("/platform/audit").json()
    assert any(a["action"] == "platform.user_suspended" for a in logs)
    assert "Fake Patient" not in str(logs)
    assert "password" not in str(logs)
    assert "password_hash" not in str(platform.get("/platform/users").json())
    assert (
        len(
            platform.get(
                "/platform/users", params={"q": "clinic@test", "clinic_id": identifier}
            ).json()
        )
        == 1
    )


def test_individual_expiry_existing_session(auth, db):
    with db() as session:
        u = session.get(m.User, "user-1")
        u.access_expires_at = m.now()
        session.commit()
    assert auth.get("/patients").json()["detail"]["code"] == "user_access_expired"


@pytest.mark.parametrize(
    "body",
    [
        {"access_expires_at": "2026-01-01T00:00:00"},
        {"access_expires_at": "nonsense"},
        {"max_users": 0},
        {"subscription_status": "invented"},
        {
            "access_starts_at": "2027-01-01T00:00:00Z",
            "access_expires_at": "2026-01-01T00:00:00Z",
        },
        {"is_active": None},
    ],
)
def test_clinic_invalid_inputs(platform, body):
    assert platform.patch("/platform/clinics/clinic-1", json=body).status_code == 422


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **kw):
        self.objects[kw["Key"]] = kw["Body"]

    def get_object(self, **kw):
        if kw["Key"] not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.objects[kw["Key"]])}

    def delete_object(self, **kw):
        self.objects.pop(kw["Key"], None)


def test_s3_roundtrip_private_integrity_cleanup():
    from fastapi import HTTPException

    fake = FakeS3()
    provider = S3StorageProvider(fake, "private-bucket")
    key, digest = provider.put(b"test", ".mp4")
    path = provider.verified_path(key, digest, 4)
    assert path.read_bytes() == b"test"
    with pytest.raises(ValueError):
        provider.path("../secret.mp4")
    fake.objects[key] = b"evil"
    with pytest.raises(HTTPException) as caught:
        provider.verified_path(key, digest, 4)
    assert caught.value.status_code == 409
    provider.delete(key)
    with pytest.raises(HTTPException) as caught:
        provider.path(key)
    assert caught.value.status_code == 404
    provider.close()
    assert not path.exists()


def test_s3_factory_shared_in_operation(monkeypatch):
    from app import storage

    fake = FakeS3()
    monkeypatch.setattr(storage.settings(), "storage_backend", "s3")
    monkeypatch.setattr(
        storage, "S3StorageProvider", lambda: S3StorageProvider(fake, "test")
    )

    @storage.storage_operation
    def operation():
        first = storage.get_storage()
        assert storage.get_storage() is first
        key, digest = first.put(b"test")
        return first.verified_path(key, digest, 4)

    assert not operation().exists()


def test_s3_video_worker_media_and_report(auth, db, video, monkeypatch, landmarks):
    from test_video import enqueue, setup_video

    from app import jobs, storage
    from app.schemas import Landmark

    fake = FakeS3()
    monkeypatch.setattr(storage.settings(), "storage_backend", "s3")
    monkeypatch.setattr(
        storage, "S3StorageProvider", lambda: S3StorageProvider(fake, "private")
    )
    monkeypatch.setattr(jobs, "SessionLocal", db)

    class Provider:
        version = "qa-fixture"

        def detect(self, rgb, timestamp):
            return [Landmark(**p) for p in landmarks]

        def close(self):
            return None

    assessment, media = setup_video(auth, video)
    assert auth.get("/media/" + media["id"]).content == video.read_bytes()
    job = enqueue(auth, assessment, media).json()
    assert jobs.claim() == job["id"]
    jobs.process_job(job["id"], Provider)
    result = auth.get("/assessments/" + assessment["id"]).json()
    assert result["jobs"][0]["state"] == "succeeded"
    report = auth.get("/assessments/" + assessment["id"] + "/report")
    assert report.status_code == 200
    assert report.content.startswith(b"%PDF")


def test_global_audit_is_not_in_clinic_feed(platform):
    platform.post("/platform/clinics", json={"name": "Other commercial tenant"})
    platform.post("/auth/logout")
    platform.post(
        "/auth/login",
        json={"email": "user1@test.local", "password": "Test-password-123"},
    )
    assert all(
        not a["action"].startswith("platform.")
        for a in platform.get("/admin/audit").json()
    )
