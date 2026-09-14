"""Substitutable server pose provider. No biomechanics library imports."""

import hashlib
import urllib.request
from pathlib import Path
from typing import Protocol

from ..core.config import settings
from ..schemas import LANDMARK_NAMES, Landmark

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
MODEL_HASH = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"


def prepare_model():
    path = Path(settings().pose_model_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(MODEL_URL, timeout=60).read(20 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != MODEL_HASH:
            raise ValueError("Falha na integridade do modelo.")
        temporary = path.with_suffix(".download")
        temporary.write_bytes(data)
        temporary.replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_HASH:
        raise ValueError("Modelo local diferente da versão aprovada.")
    return path


class PoseProvider(Protocol):
    version: str

    def detect(self, rgb_frame, timestamp_ms: int) -> list[Landmark]: ...
    def close(self) -> None: ...


class MediaPipePoseProvider:
    version = "mediapipe-python/0.10.35;pose_lite/float16/1;sha256=" + MODEL_HASH

    def __init__(self):
        import mediapipe as mp

        self.mp = mp
        path = Path(settings().pose_model_path)
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_HASH
        ):
            raise ValueError(
                "Modelo ausente ou inválido. Execute python -m app.vision.provider."
            )
        self.detector = mp.tasks.vision.PoseLandmarker.create_from_options(
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_poses=2,
            )
        )

    def detect(self, rgb_frame, timestamp_ms):
        result = self.detector.detect_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb_frame),
            timestamp_ms,
        )
        if len(result.pose_landmarks) > 1:
            raise ValueError("Mais de uma pessoa no enquadramento.")
        return (
            [
                Landmark(
                    name=LANDMARK_NAMES[i],
                    x=p.x,
                    y=p.y,
                    z=p.z,
                    visibility=p.visibility or 0,
                )
                for i, p in enumerate(result.pose_landmarks[0])
            ]
            if result.pose_landmarks
            else []
        )

    def close(self):
        self.detector.close()


if __name__ == "__main__":
    prepare_model()
    print("Modelo de pose preparado e hash verificado.")
