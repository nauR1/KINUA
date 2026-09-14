import math
from pathlib import Path

import cv2

from ..core.config import settings


def validate_upload(path: Path) -> dict:
    import json
    import subprocess
    import sys

    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.vision.video", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        raise ValueError(
            "A validação do vídeo excedeu 90 segundos. Use um arquivo menor."
        ) from None
    try:
        payload = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise ValueError("Não foi possível validar o vídeo.") from None
    if result.returncode:
        raise ValueError(payload.get("error", "Vídeo incompatível."))
    return payload


def probe(path: Path) -> dict:
    with path.open("rb") as file:
        header = file.read(32)
    if b"ftyp" in header:
        mime = "video/mp4"
    elif header.startswith(b"\x1a\x45\xdf\xa3"):
        mime = "video/webm"
    else:
        raise ValueError("Vídeo incompatível. Use MP4 ou WebM.")
    cap = cv2.VideoCapture(str(path))
    try:
        # MediaRecorder WebM may omit frame count and duration. Decode the bounded
        # stream and use presentation timestamps rather than guessed metadata.
        count = 0
        previous = -1.0
        width = height = 0
        intervals = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            if w * h > 3840 * 2160 or min(w, h) < 64:
                raise ValueError("Use vídeo entre 64 px e 4K.")
            if count and (w, h) != (width, height):
                raise ValueError("Resolução variável não suportada.")
            width, height = w, h
            stamp = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            if not math.isfinite(stamp) or stamp < 0 or (count and stamp <= previous):
                raise ValueError(
                    "Timestamps inválidos. Reexporte o vídeo com taxa constante."
                )
            if stamp > settings().max_video_seconds * 1000 or count >= 7200:
                raise ValueError("Limite de 60 segundos e 7200 frames por vídeo.")
            if count:
                intervals.append(stamp - previous)
            previous = stamp
            count += 1
        if count < 2:
            raise ValueError("Vídeo não decodificável ou muito curto.")
        import statistics

        duration = (previous + statistics.median(intervals)) / 1000
        fps = count / duration
        return {
            "mime": mime,
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": count,
            "duration_seconds": duration,
        }
    finally:
        cap.release()


def frames(path: Path, target_fps: int, metadata: dict):
    cap = cv2.VideoCapture(str(path))
    previous = -1.0
    next_time = 0.0
    index = 0
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            time_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            # Never invent VFR timestamps. A decoder that cannot supply PTS is refused.
            if (
                not math.isfinite(time_ms)
                or time_ms < 0
                or (index > 0 and time_ms <= previous)
            ):
                raise ValueError(
                    "O decodificador não forneceu timestamps monotônicos. Reexporte o vídeo com taxa constante."
                )
            previous = time_ms
            if time_ms > settings().max_video_seconds * 1000 or index > 7200:
                raise ValueError("O vídeo excede os limites de processamento.")
            if time_ms + 0.01 >= next_time:
                height, width = bgr.shape[:2]
                if (width, height) != (metadata["width"], metadata["height"]):
                    raise ValueError("A resolução do vídeo mudou durante a captura.")
                scale = min(1, 1280 / max(width, height))
                if scale < 1:
                    bgr = cv2.resize(bgr, (round(width * scale), round(height * scale)))
                yield index, time_ms, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                next_time = time_ms + 1000 / target_fps
            index += 1
        if index < metadata["frame_count"] * 0.95:
            raise ValueError(
                "Vídeo truncado ou falha de decodificação. Nenhuma análise parcial foi publicada."
            )
    finally:
        cap.release()


if __name__ == "__main__":
    import json
    import sys

    try:
        print(json.dumps(probe(Path(sys.argv[1])), ensure_ascii=True))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        sys.exit(1)
