import json
import math
from pathlib import Path

import pytest
from test_api import patient
from test_video import enqueue  # noqa: F401

from app import jobs
from app import models as m
from app.rom import DEFINITIONS, ROMEngine, definition
from app.schemas import Landmark


@pytest.fixture
def catalog(db):
    data = json.loads(
        (Path(__file__).parents[1] / "migrations/data/protocols_v1.json").read_text(
            encoding="utf-8"
        )
    )
    with db() as session:
        session.add_all(m.ProtocolCategory(**v) for v in data["categories"])
        session.flush()
        for d in data["protocols"]:
            session.add(
                m.Protocol(id=d["id"], category_id=d["category_id"], name=d["name"])
            )
            session.flush()
            session.add(
                m.ProtocolVersion(
                    id=d["id"] + "@" + d["version"],
                    protocol_id=d["id"],
                    version=d["version"],
                    definition=d,
                )
            )
        session.commit()


def start(auth):
    p = patient(auth)
    response = auth.post(
        "/assessment-protocols",
        json={"patient_id": p["id"], "version_id": "knee@1.0.0"},
    )
    assert response.status_code == 201, response.text
    return response.json()["assessment_id"]


def test_protocol_resume_conflict_skip_and_version_snapshot(auth, db, catalog):
    assert len(auth.get("/protocols").json()["categories"]) == 7
    identifier = start(auth)
    url = f"/assessment-protocols/{identifier}"
    initial = auth.get(url).json()
    assert len(initial["steps"]) == 12
    payload = dict(
        revision=0,
        state="in_progress",
        result="História profissional",
        note="Observação",
    )
    r = auth.patch(url + "/steps/history", json=payload)
    assert r.status_code == 200
    assert r.json()["steps"][0]["started_at"]
    assert auth.patch(url + "/steps/history", json=payload).status_code == 409
    payload.update(revision=1, state="completed")
    assert auth.patch(url + "/steps/history", json=payload).status_code == 200
    assert auth.get(url).json()["steps"][0]["result"] == "História profissional"
    assert (
        auth.patch(
            url + "/steps/review",
            json=dict(revision=0, state="skipped", note="Não aplicável"),
        ).status_code
        == 422
    )
    assert (
        auth.patch(
            url + "/steps/pain",
            json=dict(revision=0, state="completed", result="simulado"),
        ).status_code
        == 422
    )
    assert (
        auth.patch(
            url + "/steps/pain",
            json=dict(revision=0, state="skipped", note="Módulo fora desta rodada"),
        ).status_code
        == 200
    )
    assert (
        auth.post(url + "/complete", json={"conclusion": "Revisão"}).status_code == 409
    )
    assert (
        auth.patch(
            "/assessments/" + identifier,
            json={"status": "completed", "conclusion": "Bypass"},
        ).status_code
        == 409
    )
    with db() as session:
        version = session.get(m.ProtocolVersion, "knee@1.0.0")
        version.definition = {**version.definition, "name": "Nome alterado"}
        session.commit()
    assert auth.get(url).json()["snapshot"]["name"] == initial["snapshot"]["name"]
    auth.post("/auth/logout")
    auth.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert auth.get(url).status_code == 404
    assert auth.patch(url + "/steps/history", json=payload).status_code == 404


def test_protocol_capture_link_and_complete_manual_path(auth, catalog):
    identifier = start(auth)
    url = f"/assessment-protocols/{identifier}"
    result = auth.post(
        url + "/steps/rom/capture", json={"movement": "knee_flexion", "side": "right"}
    )
    assert result.status_code == 201, result.text
    child = auth.get("/assessments/" + result.json()["assessment_id"]).json()
    assert child["rom_session"]["movement"] == "knee_flexion"
    assert child["protocol_parent_id"] == identifier
    assert (
        auth.post(
            url + "/steps/rom/capture",
            json={"movement": "knee_flexion", "side": "right"},
        ).json()
        == result.json()
    )
    assert (
        auth.patch(
            url + "/steps/rom", json={"revision": 1, "state": "completed"}
        ).status_code
        == 409
    )
    assert (
        auth.patch(
            url + "/steps/rom",
            json={"revision": 1, "state": "skipped", "note": "Não realizado"},
        ).status_code
        == 409
    )

    parent = start(auth)
    url = f"/assessment-protocols/{parent}"
    for step in auth.get(url).json()["steps"]:
        if step["step_key"] == "report":
            pdf = auth.get("/assessments/" + parent + "/report")
            assert pdf.status_code == 200
        state = "skipped" if step["definition"]["optional"] else "completed"
        r = auth.patch(
            url + "/steps/" + step["step_key"],
            json={
                "revision": 0,
                "state": state,
                "note": "Não aplicável por decisão profissional",
                "result": "Registro manual; sem captura automatizada.",
            },
        )
        assert r.status_code == 200, r.text
    assert (
        auth.post(
            url + "/complete", json={"conclusion": "Registro profissional sem captura."}
        ).status_code
        == 200
    )
    assert (
        auth.patch(
            url + "/steps/history", json={"revision": 1, "state": "in_progress"}
        ).status_code
        == 409
    )
    assert auth.get("/assessments/" + parent + "/report").status_code == 200


def pose(movement, degrees, width=640, height=480, mirror=False):
    config = definition(movement)
    interior = degrees if config["formula"] == "angle" else 180 - degrees
    coords = [
        (0.5, 0.25),
        (0.5, 0.5),
        (
            0.5 + 0.2 * math.sin(math.radians(interior)),
            0.5 - 0.2 * math.cos(math.radians(interior)),
        ),
    ]
    return [
        Landmark(
            name="right_" + name,
            x=(1 - x if mirror else x) * height / width,
            y=y,
            visibility=0.96,
        )
        for name, (x, y) in zip(config["points"], coords)
    ]


@pytest.mark.parametrize("movement", list(DEFINITIONS))
@pytest.mark.parametrize("degrees", [0, 30, 45, 90, 135, 150, 180])
def test_rom_geometry_known_angles_scale_and_mirror(movement, degrees):
    e = ROMEngine(definition(movement))
    view = "anterior" if e.config["plane"] == "frontal" else "lateral_right"
    for width, height in [(640, 480), (1280, 960), (1000, 1000)]:
        for mirror in [False, True]:
            values, _ = e.measure(
                pose(movement, degrees, width, height, mirror),
                width,
                height,
                view,
                "rom",
                "right",
                0.7,
            )
            assert values[0]["value"] == pytest.approx(degrees, abs=0.001)


def test_rom_refuses_wrong_plane_occlusion_darkness():
    e = ROMEngine(definition("knee_flexion"))
    points = pose("knee_flexion", 90)
    for view, brightness, landmarks in [
        ("anterior", 0.8, points),
        ("lateral_left", 0.8, points),
        ("lateral_right", 0.01, points),
        ("lateral_right", 0.8, points[:-1]),
    ]:
        values, q = e.measure(landmarks, 640, 480, view, "rom", "right", brightness)
        assert values[0]["value"] is None and q["valid_frames"] == 0


def test_rom_extension_peak_minimum_gaps_and_onset():
    e = ROMEngine(definition("knee_extension"))
    records = []
    for i, v in enumerate([90, 90, 90, 80, 50, None, 20, 10, 10]):
        ms, q = e.measure(
            pose("knee_extension", v) if v is not None else [],
            640,
            480,
            "lateral_right",
            "rom",
            "right",
            0.7,
        )
        records.append(
            dict(
                frame_index=i * 2,
                timestamp_ms=i * 200,
                measurements={m["key"]: m for m in ms},
                quality=q,
            )
        )
    result, motion = e.summarize(records, "lateral_right", "rom", "right", 5)
    d = result[0]["details"]
    assert d["peak_value"] == pytest.approx(10)
    assert d["max"] == pytest.approx(90) and d["amplitude"] == pytest.approx(80)
    assert d["movement_start_index"] == 3 and d["peak_frame_index"] == 14
    assert records[6]["velocity"]["right_rom"] is None
    assert not motion["phase_detection"]["cycles"]


def test_rom_worker_history_plane_validation_review_and_scope(
    auth,
    db,
    video,
    monkeypatch,  # noqa: F811 -- shared pytest fixture
):
    monkeypatch.setattr(jobs, "SessionLocal", db)
    p = patient(auth)
    a = auth.post(
        "/rom/assessments",
        json={"patient_id": p["id"], "movement": "knee_flexion", "side": "right"},
    )
    assert a.status_code == 201
    identifier = a.json()["assessment_id"]
    assert (
        auth.post(
            "/rom/assessments",
            json={
                "patient_id": p["id"],
                "movement": "knee_flexion",
                "side": "bilateral",
            },
        ).status_code
        == 422
    )
    url = f"/assessments/{identifier}"
    args = dict(files={"file": ("fixture.webm", video.read_bytes(), "video/webm")})
    assert (
        auth.post(url + "/videos", data={"view": "anterior"}, **args).status_code == 422
    )
    media = auth.post(url + "/videos", data={"view": "lateral_right"}, **args)
    assert media.status_code == 201, media.text
    job = enqueue(auth, {"id": identifier}, media.json()).json()

    class Provider:
        version = "fixture/rom-v1"

        def detect(self, rgb, timestamp):
            return pose("knee_flexion", min(120, timestamp / 10))

        def close(self):
            pass

    assert jobs.claim() == job["id"]
    jobs.process_job(job["id"], Provider)
    result = auth.get(url).json()
    analysis = result["analyses"][0]
    assert len(analysis["frames"]) == 10
    measure = analysis["rom_measurements"][0]
    assert measure["maximum"] == pytest.approx(120) and measure[
        "excursion"
    ] == pytest.approx(120)
    history = auth.get(f"/patients/{p['id']}/rom").json()
    assert (
        history[0]["review_state"] == "needs_review"
        and history[0]["peak_frame_index"] == 12
    )
    finding = analysis["findings"][0]
    auth.post(
        "/findings/" + finding["id"] + "/review",
        json={"state": "professional_confirmed"},
    )
    assert (
        auth.get(f"/patients/{p['id']}/rom").json()[0]["review_state"]
        == "professional_confirmed"
    )
    assert (
        auth.patch(
            url, json={"status": "completed", "conclusion": "Revisado em teste"}
        ).status_code
        == 200
    )
    assert auth.get(url + "/report").status_code == 200
    auth.post("/auth/logout")
    auth.post(
        "/auth/login",
        json={"email": "user2@test.local", "password": "Test-password-123"},
    )
    assert auth.get(f"/patients/{p['id']}/rom").status_code == 404
