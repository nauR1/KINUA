import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.storage import LocalStorageProvider, normalize_image


def test_image_metadata_removed():
    image = Image.new("RGB", (100, 200), "white")
    exif = Image.Exif()
    exif[270] = "private metadata"
    exif[274] = 6
    source = io.BytesIO()
    image.save(source, "JPEG", exif=exif)
    data, width, height = normalize_image(source.getvalue())
    assert (width, height) == (200, 100)
    with Image.open(io.BytesIO(data)) as result:
        assert not result.getexif()


def test_storage_path_traversal():
    with pytest.raises(ValueError):
        LocalStorageProvider().path("../outside.jpg")


def test_small_image_rejected():
    source = io.BytesIO()
    Image.new("RGB", (10, 10)).save(source, "PNG")
    with pytest.raises(HTTPException):
        normalize_image(source.getvalue())
