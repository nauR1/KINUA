import hashlib
import io
import re
import uuid
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from .core.config import settings

Image.MAX_IMAGE_PIXELS = 20_000_000


class StorageProvider(Protocol):
    def put(
        self, data: bytes, extension: str = ".jpg", prefix: str = "production/"
    ) -> tuple[str, str]: ...
    def path(self, key: str) -> Path: ...
    def verified_path(
        self, key: str, expected_hash: str, expected_size: int
    ) -> Path: ...
    def close(self) -> None: ...
    def delete(self, key: str) -> None: ...


class LocalStorageProvider:
    def __init__(self):
        self.root = Path(settings().storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def close(self):
        return None

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if "/" in key:
            validate_storage_key(key)
        if not target.is_relative_to(self.root) or (
            "/" not in key and target.parent != self.root
        ):
            raise ValueError("Chave de armazenamento inválida")
        return target

    def put(
        self, data: bytes, extension: str = ".jpg", prefix: str = "production/"
    ) -> tuple[str, str]:
        if extension not in (".jpg", ".mp4", ".mov", ".webm"):
            raise ValueError("Extensão inválida")
        validate_prefix(prefix)
        key = prefix + str(uuid.uuid4()) + extension
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        return key, hashlib.sha256(data).hexdigest()

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)

    def verified_path(self, key: str, expected_hash: str, expected_size: int) -> Path:
        """Detect missing/corrupted storage before associating media with a result.



        This is an integrity check, not protection against a host administrator
        who can alter both the database hash and the stored file.
        """
        path = self.path(key)
        try:
            if path.stat().st_size != expected_size:
                raise HTTPException(
                    409, "Integridade da mídia divergente. Não utilize esta captura."
                )
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise HTTPException(
                    409, "Integridade da mídia divergente. Não utilize esta captura."
                )
        except FileNotFoundError:
            raise HTTPException(404, "Arquivo indisponível no armazenamento.") from None
        return path


def normalize_image(data: bytes) -> tuple[bytes, int, int]:

    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Formato não aceito")
            if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                raise ValueError("Imagem muito grande")
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            if min(image.size) < 64:
                raise ValueError("Imagem muito pequena")
            output = io.BytesIO()
            # Re-encode: remove EXIF/location and non-image payloads.
            image.save(output, format="JPEG", quality=92)
            return output.getvalue(), image.width, image.height
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(
            422, "Imagem inválida. Use JPEG, PNG ou WebP, até 20 megapixels."
        )


def brightness(path: Path) -> float:

    with Image.open(path) as image:
        small = image.convert("L")
        small.thumbnail((128, 128))
        return ImageStat.Stat(small).mean[0] / 255


# A bounded private staging directory exists only for an operation's lifetime.


class S3StorageProvider(LocalStorageProvider):
    def __init__(self, client=None, bucket=None):
        import boto3
        from botocore.config import Config

        config = settings()
        self.client = client or boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint_url,
            region_name=config.s3_region,
            aws_access_key_id=config.s3_access_key_id,
            aws_secret_access_key=config.s3_secret_access_key,
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": 3},
                s3={"addressing_style": "virtual"},
            ),
        )
        self.bucket = bucket or config.s3_bucket
        self.temp = None

    def validate_key(self, key):
        validate_storage_key(key)

    def close(self):
        if self.temp:
            self.temp.cleanup()
            self.temp = None

    def put(self, data, extension=".jpg", prefix="production/"):
        if extension not in (".jpg", ".mp4", ".mov", ".webm"):
            raise ValueError("Extensão inválida")
        validate_prefix(prefix)
        key = prefix + str(uuid.uuid4()) + extension
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        except (BotoCoreError, ClientError):
            raise HTTPException(
                503, "Armazenamento temporariamente indisponível."
            ) from None
        return key, hashlib.sha256(data).hexdigest()

    def path(self, key):

        self.validate_key(key)
        if self.temp is None:
            self.temp = TemporaryDirectory(prefix="kinua-private-")
            self.root = Path(self.temp.name)
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise HTTPException(
                    404, "Arquivo indisponível no armazenamento."
                ) from None
            raise HTTPException(
                503, "Armazenamento temporariamente indisponível."
            ) from None
        except BotoCoreError:
            raise HTTPException(
                503, "Armazenamento temporariamente indisponível."
            ) from None
        body = response["Body"]
        try:
            total = 0
            with target.open("wb") as stream:
                while chunk := body.read(1024 * 1024):
                    total += len(chunk)
                    if total > max(
                        settings().max_video_bytes, settings().max_upload_bytes
                    ):
                        raise HTTPException(
                            409, "Mídia excede o limite de integridade."
                        )
                    stream.write(chunk)
        finally:
            body.close()
        return target

    def delete(self, key):
        self.validate_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError):
            raise HTTPException(
                503, "Não foi possível remover a mídia do armazenamento."
            ) from None


_active_storage = ContextVar("kinua_storage", default=None)


def get_storage() -> StorageProvider:

    return _active_storage.get() or (
        S3StorageProvider()
        if settings().storage_backend == "s3"
        else LocalStorageProvider()
    )


def storage_operation(function):

    @wraps(function)
    def wrapped(*args, **kwargs):
        if _active_storage.get() is not None:
            return function(*args, **kwargs)
        storage = get_storage()
        token = _active_storage.set(storage)
        try:
            return function(*args, **kwargs)
        finally:
            _active_storage.reset(token)
            storage.close()

    return wrapped


def validate_prefix(prefix: str):
    if prefix != "production/" and not re.fullmatch(r"demo/[a-zA-Z0-9_-]+/", prefix):
        raise ValueError("Prefixo de armazenamento inválido.")


def validate_storage_key(key: str):
    if not re.fullmatch(
        r"(?:(?:production/)|(?:demo/[a-zA-Z0-9_-]+/))?[a-zA-Z0-9_-]+\.(jpg|mp4|mov|webm)",
        key,
    ):
        raise ValueError("Chave de armazenamento inválida.")


def media_prefix(clinic):
    return "demo/" + clinic.id + "/" if clinic.is_demo else "production/"
