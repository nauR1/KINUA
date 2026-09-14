import pytest
from sqlalchemy import select
from test_api import patient

from app import jobs
from app import models as m
from app.schemas import Landmark
from app.vision.video import frames, probe


def setup_video(auth, video):
    p = patient(auth)
    a = auth.post(
        "/assessments",
        json={
            "patient_id": p["id"],
            "kind": "movement",
            "mode": "video",
            "protocol": "bilateral_squat",
        },
    ).json()
    response = auth.post(
        f"/assessments/{a['id']}/videos",
        files={"file": ("fixture.webm", video.read_bytes(), "video/webm")},
        data={"view": "anterior"},
    )
    assert response.status_code == 201, response.text
    return a, response.json()


def enqueue(auth, a, media):
    return auth.post(
        f"/assessments/{a['id']}/jobs",
        json={
            "media_id": media["id"],
            "fps": 5,
            "camera_level_confirmed": True,
            "view_confirmed": True,
        },
    )


def test_video_timestamps_and_sampling(video):
    metadata = probe(video)
    samples = list(frames(video, 5, metadata))
    assert metadata["frame_count"] == 20
    assert metadata["duration_seconds"] == pytest.approx(2)
    assert len(samples) == 10
    assert [r[1] for r in samples] == pytest.approx(list(range(0, 2000, 200)))


def test_queue_cancel_retry_and_scope(auth, db, video, monkeypatch):
    monkeypatch.setattr(jobs, "SessionLocal", db)
    a, media = setup_video(auth, video)
    job = enqueue(auth, a, media)
    assert job.status_code == 202
    assert enqueue(auth, a, media).status_code == 409
    assert auth.post("/jobs/" + job.json()["id"] + "/cancel").status_code == 200
    assert jobs.claim() is None
    assert enqueue(auth, a, media).status_code == 202
    assert jobs.claim() == job.json()["id"]
    assert auth.post("/jobs/" + job.json()["id"] + "/cancel").status_code == 200
    with pytest.raises(jobs.Cancelled):
        jobs.heartbeat(job.json()["id"], 0.5)
    auth.post("/auth/logout")
    auth.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert auth.get(f"/assessments/{a['id']}/jobs").status_code == 404
    assert auth.post("/jobs/" + job.json()["id"] + "/cancel").status_code == 404
    assert auth.get("/media/" + media["id"]).status_code == 404


def test_worker_persists_series_report_and_immutability(
    auth, db, video, monkeypatch, landmarks
):
    monkeypatch.setattr(jobs, "SessionLocal", db)

    class FixtureProvider:
        version = "test-fixture/1"

        def detect(self, rgb, timestamp):
            return [Landmark(**p) for p in landmarks]

        def close(self):
            pass

    a, media = setup_video(auth, video)
    job = enqueue(auth, a, media).json()
    assert jobs.claim() == job["id"]
    jobs.process_job(job["id"], FixtureProvider)
    result = auth.get("/assessments/" + a["id"]).json()
    assert result["jobs"][0]["state"] == "succeeded"
    analysis = result["analyses"][0]
    assert len(analysis["frames"]) == 10
    assert len(analysis["frames"][1]["landmarks"]) == len(landmarks)
    assert analysis["motion"]["phase_detection"]["cycles"] == []
    assert analysis["measurements"][0]["details"]["statistic"] == "mean"
    assert enqueue(auth, a, media).status_code == 409
    assert auth.get("/assessments/" + a["id"] + "/report").content.startswith(b"%PDF")
    with db() as session:
        assert len(list(session.scalars(select(m.Analysis)))) == 1
    assert auth.post("/jobs/" + job["id"] + "/cancel").status_code == 409


def test_video_validation_and_empty_detection(auth, db, video, monkeypatch):
    monkeypatch.setattr(jobs, "SessionLocal", db)
    a, media = setup_video(auth, video)
    bad = auth.post(
        f"/assessments/{a['id']}/videos",
        files={"file": ("bad.mp4", b"not-video", "video/mp4")},
        data={"view": "anterior"},
    )
    assert bad.status_code == 422
    job = enqueue(auth, a, media).json()
    jobs.claim()

    class EmptyProvider:
        version = "test-fixture/1"

        def detect(self, rgb, timestamp):
            return []

        def close(self):
            pass

    with pytest.raises(ValueError, match="Nenhum frame"):
        jobs.process_job(job["id"], EmptyProvider)
    jobs.fail(job["id"], "Nenhum frame utilizável.")
    result = auth.get("/assessments/" + a["id"]).json()
    assert result["analyses"] == [] and result["jobs"][0]["state"] == "failed"
