import hashlib
import io
import uuid
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from .core.config import settings

Image.MAX_IMAGE_PIXELS = 20_000_000


class StorageProvider(Protocol):
    def put(self, data: bytes) -> tuple[str, str]: ...
    def path(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...


class LocalStorageProvider:
    def __init__(self):
        self.root = Path(settings().storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if target.parent != self.root:
            raise ValueError("Chave de armazenamento inválida")
        return target

    def put(self, data: bytes, extension: str = ".jpg") -> tuple[str, str]:
        if extension not in (".jpg", ".mp4", ".webm"):
            raise ValueError("Extensão inválida")
        key = str(uuid.uuid4()) + extension
        with self.path(key).open("xb") as stream:
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
