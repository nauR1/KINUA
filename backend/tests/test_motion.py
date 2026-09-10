import pytest
from pydantic import ValidationError

from app.biomechanics.motion import MotionEngine, segment_phases, summarize
from app.schemas import AssessmentInput, Landmark


def test_complete_and_incomplete_squats():
    values = [0, 0, 0, 5, 15, 40, 40, 30, 10, 0, 0]
    result = segment_phases(
        values, [i * 200 for i in range(len(values))], "angle", "bilateral_squat"
    )
    assert result["cycles"][0]["complete"]
    assert result["phases"][5] == "maximum"
    assert result["phases"][-1] == "final"
    incomplete = segment_phases(
        values[:8], [i * 200 for i in range(8)], "angle", "bilateral_squat"
    )
    assert incomplete["cycles"][0]["complete"] is False


def test_gaps_never_bridge_repetitions():
    values = [0, 0, 0, 10, 30, None, 20, 0, 0]
    result = segment_phases(
        values, [i * 200 for i in range(len(values))], "angle", "bilateral_squat"
    )
    assert not any(c["complete"] for c in result["cycles"])
    assert result["phases"][5] == "unknown"


def test_stationary_and_no_stable_start():
    assert (
        segment_phases([20] * 20, list(range(20)), "angle", "arm_raise")["cycles"] == []
    )
    assert (
        segment_phases([0, 10, 20, 30, 40], list(range(5)), "angle", "bilateral_squat")[
            "cycles"
        ]
        == []
    )


def test_arm_phases_are_not_squat_labels():
    result = segment_phases(
        [0, 0, 0, 10, 30, 60, 50, 20, 0, 0], list(range(10)), "angle", "arm_raise"
    )
    assert "raising" in result["phases"] and "lowering" in result["phases"]
    assert "descending" not in result["phases"]


def test_medial_projection_sign_and_mirror(landmarks):
    def run(points):
        measures, _ = MotionEngine().measure(
            [Landmark(**p) for p in points],
            1000,
            1000,
            "anterior",
            "bilateral_squat",
            "bilateral",
            0.8,
        )
        return {m["key"]: m for m in measures}

    next(p for p in landmarks if p["name"] == "left_knee")["x"] = 0.45
    m = run(landmarks)
    assert m["left_knee_medial_ratio"]["value"] == pytest.approx(0.25)
    mirrored = [{**p, "x": 1 - p["x"]} for p in landmarks]
    assert run(mirrored)["left_knee_medial_ratio"]["value"] == pytest.approx(0.25)
    assert m["left_hip_flexion"]["value"] is None


def test_summary_uses_real_dt_and_preserves_gap(landmarks):
    records = []
    for i, value in enumerate([0, 20, None, 80]):
        records.append(
            {
                "timestamp_ms": [0, 200, 400, 600][i],
                "measurements": {
                    "left_knee_projection": {
                        "value": value,
                        "label": "Test",
                        "key": "left_knee_projection",
                        "unit": "°",
                        "confidence": 0.9,
                        "details": {"side": "left", "region": "knee"},
                    }
                },
            }
        )
    summary, motion = summarize(records, "anterior", "bilateral_squat", "bilateral", 5)
    assert summary[0]["value"] == pytest.approx(100 / 3, abs=0.0001)
    assert summary[0]["details"]["amplitude"] == 80
    assert records[1]["velocity"]["left_knee_projection"] == 100
    assert records[3]["velocity"]["left_knee_projection"] is None


def test_protocol_validation():
    with pytest.raises(ValidationError):
        AssessmentInput(patient_id="x", mode="video")
    with pytest.raises(ValidationError):
        AssessmentInput(patient_id="x", mode="video", protocol="single_leg_squat")
    assert (
        AssessmentInput(
            patient_id="x", mode="video", protocol="single_leg_squat", side="left"
        ).side
        == "left"
    )
