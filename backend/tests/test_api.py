import io

from PIL import Image
from sqlalchemy import select

from app import models as m


def patient(client):
    r = client.post(
        "/patients",
        json={
            "name": "Paciente Teste",
            "birth_date": "1990-01-01",
            "complaint": "Fictício",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def assessment(client):
    p = patient(client)
    r = client.post(
        "/assessments",
        json={"patient_id": p["id"], "kind": "postural", "mode": "camera"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, a):
    image = io.BytesIO()
    Image.new("RGB", (640, 960), (180, 180, 180)).save(image, format="JPEG")
    r = client.post(
        f"/assessments/{a['id']}/media",
        files={"file": ("fixture.jpg", image.getvalue(), "image/jpeg")},
        data={"view": "anterior"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_auth_and_logout(client):
    assert client.get("/patients").status_code == 401
    assert (
        client.post(
            "/auth/login", json={"email": "user1@test.local", "password": "wrong"}
        ).status_code
        == 401
    )
    r = client.post(
        "/auth/login",
        json={"email": "user1@test.local", "password": "Test-password-123"},
    )
    assert r.status_code == 200
    assert "HttpOnly" in r.headers["set-cookie"]
    assert "SameSite=strict" in r.headers["set-cookie"]
    assert "password_hash" not in client.get("/auth/me").text
    client.post("/auth/logout")
    assert client.get("/patients").status_code == 401


def test_rate_limit(client):
    for _ in range(5):
        assert (
            client.post(
                "/auth/login", json={"email": "unknown@test.local", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", json={"email": "unknown@test.local", "password": "wrong"}
        ).status_code
        == 429
    )


def test_csrf(auth):
    assert (
        auth.post(
            "/patients", json={}, headers={"Origin": "https://attacker.test"}
        ).status_code
        == 403
    )
    assert (
        auth.post("/patients", json={}, headers={"X-Requested-With": ""}).status_code
        == 403
    )


def test_patient_validation(auth):
    assert (
        auth.post(
            "/patients", json={"name": "A", "birth_date": "2999-01-01"}
        ).status_code
        == 422
    )
    assert (
        auth.post(
            "/patients",
            json={"name": "Valid", "birth_date": "1990-01-01", "clinic_id": "other"},
        ).status_code
        == 422
    )


def test_complete_workflow_and_immutability(auth, landmarks, db):
    a = assessment(auth)
    media = upload(auth, a)
    body = {
        "media_id": media["id"],
        "provider": "MediaPipePoseProvider",
        "provider_version": "test-fixture/1",
        "landmarks": landmarks,
        "camera_level_confirmed": True,
        "view_confirmed": True,
    }
    r = auth.post(f"/assessments/{a['id']}/analyze", json=body)
    assert r.status_code == 201, r.text
    result = r.json()
    analysis = result["analyses"][0]
    assert (
        next(x for x in analysis["measurements"] if x["key"] == "shoulder_tilt")[
            "value"
        ]
        == 0
    )
    assert len(analysis["frames"][0]["landmarks"]) == len(landmarks)
    assert auth.post(f"/assessments/{a['id']}/analyze", json=body).status_code == 409
    assert (
        auth.patch(
            f"/assessments/{a['id']}",
            json={"status": "completed", "conclusion": "Conclusão"},
        ).status_code
        == 409
    )
    original_order = [f["id"] for f in analysis["findings"]]
    for finding in analysis["findings"]:
        r = auth.post(
            "/findings/" + finding["id"] + "/review",
            json={
                "state": "professional_confirmed",
                "note": "Medida revisada; dado sintético.",
            },
        )
        assert r.status_code == 200
        reloaded = auth.get(f"/assessments/{a['id']}").json()["analyses"][0]["findings"]
        assert [f["id"] for f in reloaded] == original_order
    assert (
        auth.patch(
            f"/assessments/{a['id']}",
            json={
                "status": "completed",
                "notes": "Notas <tag> escapadas",
                "conclusion": "Conclusão profissional de teste.",
            },
        ).status_code
        == 200
    )
    assert (
        auth.post(
            "/findings/" + analysis["findings"][0]["id"] + "/review",
            json={"state": "professional_rejected"},
        ).status_code
        == 409
    )
    assert auth.get("/media/" + media["id"]).headers["content-type"] == "image/jpeg"
    pdf = auth.get(f"/assessments/{a['id']}/report")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    history = auth.get("/patients/" + a["patient_id"] + "/assessments").json()
    assert history[0]["status"] == "completed"
    with db() as session:
        assert (
            session.scalar(select(m.Report)).snapshot["assessment"]["conclusion"]
            == "Conclusão profissional de teste."
        )
        assert session.scalar(select(m.ProfessionalReview)).reviewer_id == "user-1"
        assert session.scalar(
            select(m.AuditLog).where(m.AuditLog.action == "report.generated")
        )


def test_cross_clinic_isolation(auth, landmarks):
    a = assessment(auth)
    media = upload(auth, a)
    result = auth.post(
        f"/assessments/{a['id']}/analyze",
        json={
            "media_id": media["id"],
            "provider": "MediaPipePoseProvider",
            "provider_version": "fixture",
            "landmarks": landmarks,
            "camera_level_confirmed": True,
            "view_confirmed": True,
        },
    ).json()
    finding = result["analyses"][0]["findings"][0]["id"]
    auth.post("/auth/logout")
    auth.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert auth.get("/patients").json() == []
    for route in [
        f"/assessments/{a['id']}",
        f"/media/{media['id']}",
        f"/patients/{a['patient_id']}/assessments",
        f"/assessments/{a['id']}/report",
    ]:
        assert auth.get(route).status_code == 404
    assert (
        auth.post(
            "/findings/" + finding + "/review", json={"state": "professional_confirmed"}
        ).status_code
        == 404
    )
    assert (
        auth.post("/assessments", json={"patient_id": a["patient_id"]}).status_code
        == 404
    )
    assert auth.get("/admin/audit").status_code == 403
    assert auth.get("/admin/users").status_code == 403


def test_invalid_upload(auth):
    a = assessment(auth)
    r = auth.post(
        f"/assessments/{a['id']}/media",
        files={"file": ("fake.jpg", b"<script>bad</script>", "image/jpeg")},
        data={"view": "anterior"},
    )
    assert r.status_code == 422


def test_media_cannot_be_attached_to_other_assessment(auth, landmarks):
    a, b = assessment(auth), assessment(auth)
    media = upload(auth, a)
    r = auth.post(
        f"/assessments/{b['id']}/analyze",
        json={
            "media_id": media["id"],
            "provider": "MediaPipePoseProvider",
            "provider_version": "fixture",
            "landmarks": landmarks,
        },
    )
    assert r.status_code == 404


def test_admin_user_creation(auth):
    r = auth.post(
        "/admin/users",
        json={
            "name": "Novo profissional",
            "email": "new@test.local",
            "password": "Long-password-123",
            "role": "physiotherapist",
        },
    )
    assert r.status_code == 201
    assert "password" not in r.text
    auth.post("/auth/logout")
    assert (
        auth.post(
            "/auth/login",
            json={"email": "new@test.local", "password": "Long-password-123"},
        ).status_code
        == 200
    )
    assert (
        auth.post(
            "/admin/users",
            json={
                "name": "Forbidden",
                "email": "no@test.local",
                "password": "Long-password-123",
            },
        ).status_code
        == 403
    )
