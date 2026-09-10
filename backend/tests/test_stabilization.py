"""Regression cases reproduced during the engineering audit; no live data."""

import math

import pytest
from test_api import patient
from test_video import enqueue, setup_video  # noqa: F401

from app import jobs
from app import models as m
from app.biomechanics.engine import angle
from app.biomechanics.motion import MotionEngine
from app.schemas import Landmark


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_angle_refuses_nonfinite(bad):
    with pytest.raises(ValueError):
        angle((bad, 1), (0, 0), (1, 0))


@pytest.mark.parametrize("degrees", [0, 45, 90, 135, 180])
def test_angle_reference(degrees):
    r = math.radians(degrees)
    assert angle((1, 0), (0, 0), (math.cos(r), math.sin(r))) == pytest.approx(
        degrees, abs=1e-6
    )


def test_zero_trunk_is_unavailable():
    points = [
        Landmark(name="right_" + name, x=0.5, y=0.5, visibility=0.99)
        for name in ["hip", "shoulder"]
    ]
    values, _ = MotionEngine().measure(
        points, 640, 480, "lateral_right", "arm_raise", "right", 0.8
    )
    assert (
        next(m for m in values if m["key"] == "right_trunk_sagittal")["value"] is None
    )


def test_preview_refuses_duplicate_landmarks(auth):
    p = {"name": "right_knee", "x": 0.5, "y": 0.5, "visibility": 0.99}
    r = auth.post(
        "/rom/preview",
        json={
            "movement": "knee_flexion",
            "side": "right",
            "view": "lateral_right",
            "landmarks": [p, p],
            "width": 640,
            "height": 480,
            "brightness": 0.8,
            "plane_confirmed": True,
        },
    )
    assert r.status_code == 422


def test_cancel_retry_cannot_publish_old_attempt(
    auth, db, video, monkeypatch, landmarks
):  # noqa: F811
    monkeypatch.setattr(jobs, "SessionLocal", db)
    a, media = setup_video(auth, video)
    identifier = enqueue(auth, a, media).json()["id"]
    jobs.claim()

    class RacingProvider:
        version = "fixture/race"
        changed = False

        def detect(self, rgb, timestamp):
            if not self.changed:
                self.changed = True
                assert auth.post("/jobs/" + identifier + "/cancel").status_code == 200
                assert enqueue(auth, a, media).status_code == 202
                assert jobs.claim() == identifier
            return [Landmark(**p) for p in landmarks]

        def close(self):
            pass

    with pytest.raises(jobs.Cancelled):
        jobs.process_job(identifier, RacingProvider)
    result = auth.get("/assessments/" + a["id"]).json()
    assert result["analyses"] == []
    assert result["jobs"][0]["state"] == "running"


def test_patient_edit_preserves_fields_and_refuses_stale_revision(auth):
    original = patient(auth)
    payload = {
        "name": "QA Edited",
        "birth_date": original["birth_date"],
        "phone": "123456",
        "complaint": "Synthetic",
        "expected_revision": original["revision"],
    }
    r = auth.patch("/patients/" + original["id"], json=payload)
    assert r.status_code == 200
    assert r.json()["details"]["phone"] == "123456"
    assert auth.patch("/patients/" + original["id"], json=payload).status_code == 409
    assert (
        next(p for p in auth.get("/patients").json() if p["id"] == original["id"])[
            "name"
        ]
        == "QA Edited"
    )


def test_concurrent_notes_do_not_overwrite(auth):
    from test_api import assessment

    a = assessment(auth)
    url = "/assessments/" + a["id"]
    assert (
        auth.patch(url, json={"notes": "First tab", "expected_notes": ""}).status_code
        == 200
    )
    assert (
        auth.patch(url, json={"notes": "Stale tab", "expected_notes": ""}).status_code
        == 409
    )
    assert auth.get(url).json()["notes"] == "First tab"


@pytest.mark.parametrize(
    "path",
    [
        "/auth/me",
        "/dashboard",
        "/patients",
        "/admin/users",
        "/admin/audit",
        "/protocols",
        "/protocols/pending",
        "/rom/movements",
        "/assessments/missing",
        "/media/missing",
        "/patients/missing/rom",
        "/assessments/missing/report",
    ],
)
def test_protected_endpoints_without_session(client, path):
    assert client.get(path).status_code == 401


def test_expired_session_is_rejected(auth, db):
    from datetime import timedelta

    from sqlalchemy import select

    with db() as session:
        token = session.scalar(select(m.Session))
        token.expires_at = m.now() - timedelta(seconds=1)
        session.commit()
    assert auth.get("/auth/me").status_code == 401


def test_old_failure_does_not_fail_new_attempt(auth, db, video, monkeypatch):  # noqa: F811
    monkeypatch.setattr(jobs, "SessionLocal", db)
    a, media = setup_video(auth, video)
    identifier = enqueue(auth, a, media).json()["id"]
    jobs.claim()
    with db() as session:
        old = session.get(m.ProcessingJob, identifier).run_token
    auth.post("/jobs/" + identifier + "/cancel")
    enqueue(auth, a, media)
    jobs.claim()
    jobs.fail(identifier, "stale failure", old)
    with db() as session:
        assert session.get(m.ProcessingJob, identifier).state == "running"


def test_motion_valid_arm_is_not_discarded_when_legs_are_occluded():
    points = [
        Landmark(name="right_" + n, x=x, y=y, visibility=0.99)
        for n, x, y in [("hip", 0.5, 0.7), ("shoulder", 0.5, 0.3), ("elbow", 0.8, 0.3)]
    ]
    measures, quality = MotionEngine().measure(
        points, 640, 480, "lateral_right", "arm_raise", "right", 0.8
    )
    assert next(m for m in measures if m["key"] == "right_arm_elevation")["value"] == 90
    assert quality["valid_frames"] == 1
