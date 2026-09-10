from test_api import patient, upload

from app import models as m


def snapshots(auth, landmarks):
    p = patient(auth)
    result = []
    for _ in range(2):
        a = auth.post(
            "/assessments",
            json={"patient_id": p["id"], "kind": "postural", "mode": "photo"},
        ).json()
        media = upload(auth, a)
        response = auth.post(
            "/assessments/" + a["id"] + "/analyze",
            json={
                "media_id": media["id"],
                "provider": "MediaPipePoseProvider",
                "provider_version": "test-fixture/1",
                "landmarks": landmarks,
                "camera_level_confirmed": True,
                "view_confirmed": True,
            },
        )
        assert response.status_code == 201, response.text
        result.append(response.json()["analyses"][0])
    return result


def test_comparison_preserves_values_and_rejects_versions(auth, db, landmarks):
    a, b = snapshots(auth, landmarks)
    response = auth.get("/comparisons", params={"a": a["id"], "b": b["id"]})
    assert response.status_code == 200
    assert response.json()["comparable"]
    with db() as session:
        assessment_id = session.get(m.Analysis, b["id"]).assessment_id
    pdf = auth.get(
        "/assessments/" + assessment_id + "/report",
        params={"compare_to": a["id"], "analysis_id": b["id"]},
    )
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert all(m["difference"] in (0, None) for m in response.json()["measurements"])
    assert (
        auth.get("/comparisons", params={"a": a["id"], "b": a["id"]}).status_code == 422
    )
    with db() as session:
        session.get(m.Analysis, b["id"]).biomechanics_version = "future/99"
        session.commit()
    result = auth.get("/comparisons", params={"a": a["id"], "b": b["id"]}).json()
    assert not result["comparable"] and "biomechanics_version" in result["reasons"]


def test_comparison_scope(auth, landmarks):
    a, b = snapshots(auth, landmarks)
    auth.post("/auth/logout")
    auth.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert (
        auth.get("/comparisons", params={"a": a["id"], "b": b["id"]}).status_code == 404
    )
