import math

import pytest
from pydantic import ValidationError

from app.biomechanics.engine import BiomechanicsEngine, angle, horizontal_tilt
from app.clinical.engine import RULESET, ClinicalRulesEngine
from app.schemas import AnalyzeInput, Landmark


@pytest.mark.parametrize(
    "a,b,c,expected",
    [
        ((1, 0), (0, 0), (0, 1), 90),
        ((0, 0), (0, 1), (0, 2), 180),
        ((1, 0), (0, 0), (1, 1), 45),
    ],
)
def test_angle(a, b, c, expected):
    assert angle(a, b, c) == pytest.approx(expected)


def test_degenerate():
    with pytest.raises(ValueError):
        angle((0, 0), (0, 0), (1, 1))
    with pytest.raises(ValueError):
        horizontal_tilt((0, 0), (0, 0))


def run(landmarks, **kwargs):
    return BiomechanicsEngine().analyze(
        [Landmark(**x) for x in landmarks],
        kwargs.get("width", 1000),
        kwargs.get("height", 1000),
        kwargs.get("view", "anterior"),
        kwargs.get("level", True),
        kwargs.get("plane", True),
        kwargs.get("brightness", 0.6),
    )


def test_symmetric_pose(landmarks):
    result, quality = run(landmarks)
    values = {m["key"]: m["value"] for m in result}
    assert values["shoulder_tilt"] == 0
    assert values["pelvis_tilt"] == 0
    assert values["trunk_tilt"] == 0
    assert values["stance_ratio"] == pytest.approx(1)
    assert values["right_knee_projection"] == pytest.approx(180)
    assert values["right_knee_flexion"] is None
    assert quality["coverage"] == 1


def test_aspect_ratio_correction(landmarks):
    next(p for p in landmarks if p["name"] == "right_shoulder")["y"] = 0.35
    values, _ = run(landmarks, width=2000, height=1000)
    assert values[0]["value"] == pytest.approx(
        math.degrees(math.atan(0.1 / 0.8)), abs=0.001
    )


@pytest.mark.parametrize(
    "options", [{"level": False}, {"plane": False}, {"brightness": 0.01}]
)
def test_untrusted_capture_suppresses_measurements(landmarks, options):
    result, _ = run(landmarks, **options)
    assert all(m["value"] is None for m in result)


def test_occlusion_only_blocks_dependent_measurements(landmarks):
    next(p for p in landmarks if p["name"] == "left_shoulder")["visibility"] = 0.2
    result, _ = run(landmarks)
    assert result[0]["value"] is None
    assert result[1]["value"] == 0


def test_sagittal_side(landmarks):
    result, _ = run(landmarks, view="lateral_right")
    values = {m["key"]: m["value"] for m in result}
    assert values["shoulder_tilt"] is None
    assert values["left_knee_flexion"] is None
    assert values["right_knee_flexion"] == pytest.approx(0)


def test_no_experimental_clinical_trigger():
    assert (
        ClinicalRulesEngine().evaluate({"key": "right_knee_projection", "value": 999})
        == []
    )
    assert all(not r["enabled"] for r in RULESET["rules"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("x", float("nan")),
        ("y", float("inf")),
        ("visibility", 1.1),
        ("name", "fake_joint"),
    ],
)
def test_landmark_validation(field, value):
    data = {"name": "nose", "x": 0.5, "y": 0.1, "visibility": 0.9}
    data[field] = value
    with pytest.raises(ValidationError):
        Landmark(**data)


def test_duplicate_points(landmarks):
    with pytest.raises(ValidationError):
        AnalyzeInput(
            media_id="x",
            provider="MediaPipePoseProvider",
            provider_version="1",
            landmarks=[landmarks[0], landmarks[0]],
        )
