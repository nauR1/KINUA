"""Engineering release checks. These do not establish clinical validity."""

import io
import math

import pytest
from PIL import Image
from test_api import assessment, upload

from app import models as m
from app.biomechanics.engine import angle
from app.storage import LocalStorageProvider


def test_partial_assessment_update_preserves_existing_fields(auth):
    a = assessment(auth)
    path = "/assessments/" + a["id"]
    assert (
        auth.patch(
            path,
            json={
                "notes": "Nota anterior",
                "conclusion": "Conclusão anterior",
                "status": "draft",
            },
        ).status_code
        == 200
    )
    result = auth.patch(path, json={"notes": "Nota revisada"}).json()
    assert result["notes"] == "Nota revisada"
    assert result["conclusion"] == "Conclusão anterior"
    assert result["status"] == "draft"


@pytest.mark.parametrize("endpoint", ["media", "report"])
@pytest.mark.parametrize("same_size", [False, True])
def test_replaced_media_is_rejected(auth, db, landmarks, endpoint, same_size):
    a = assessment(auth)
    media = upload(auth, a)
    response = auth.post(
        "/assessments/" + a["id"] + "/analyze",
        json={
            "media_id": media["id"],
            "provider": "MediaPipePoseProvider",
            "provider_version": "fixture",
            "landmarks": landmarks,
            "camera_level_confirmed": True,
            "view_confirmed": True,
        },
    )
    assert response.status_code == 201
    with db() as session:
        record = session.get(m.AssessmentMedia, media["id"])
        path = LocalStorageProvider().path(record.storage_key)
    replacement = io.BytesIO()
    Image.new("RGB", (640, 960), "red").save(replacement, format="JPEG")
    if same_size:
        content = bytearray(path.read_bytes())
        content[-1] ^= 1
        path.write_bytes(content)
    else:
        path.write_bytes(replacement.getvalue())
    route = (
        "/media/" + media["id"]
        if endpoint == "media"
        else "/assessments/" + a["id"] + "/report"
    )
    assert auth.get(route).status_code == 409


def test_angle_against_constructed_reference_sweep():
    for expected in range(1, 180):
        rad = math.radians(expected)
        a = (1.0, 0.0)
        b = (0.0, 0.0)
        c = (math.cos(rad), math.sin(rad))
        for scale in (0.01, 1.0, 100.0):
            points = [(p[0] * scale + 3, p[1] * scale - 4) for p in (a, b, c)]
            assert angle(*points) == pytest.approx(expected, abs=1e-8)
            assert angle(*[(-p[0], p[1]) for p in points]) == pytest.approx(
                expected, abs=1e-8
            )


def test_production_config_refuses_insecure_defaults():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="SECURE_COOKIES"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://example",
            secure_cookies=False,
        )
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql://example",
            secure_cookies=True,
            allowed_origins="http://example.test",
        )
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(
            _env_file=None,
            environment="production",
            database_url="sqlite:///test.db",
            secure_cookies=True,
            allowed_origins="https://example.test",
        )
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://example",
        secure_cookies=True,
        allowed_origins="https://example.test",
    )
    assert settings.origins == ["https://example.test"]
