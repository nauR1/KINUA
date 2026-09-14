from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PatientInput(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    birth_date: date
    biological_sex: Literal["", "female", "male", "intersex"] = ""
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=254)
    occupation: str = Field(default="", max_length=160)
    sport: str = Field(default="", max_length=160)
    dominance: Literal["", "right", "left", "both"] = ""
    height_cm: float | None = Field(default=None, ge=30, le=260)
    weight_kg: float | None = Field(default=None, ge=1, le=500)
    notes: str = Field(default="", max_length=10000)
    history: str = Field(default="", max_length=10000)
    complaint: str = Field(default="", max_length=10000)

    @field_validator("birth_date")
    @classmethod
    def valid_date(cls, value):
        if value > date.today() or value.year < 1900:
            raise ValueError("Data de nascimento inválida")
        return value


class PatientUpdate(PatientInput):
    expected_revision: str | None = Field(default=None, max_length=64)


class AssessmentInput(StrictModel):
    patient_id: str
    kind: Literal["postural", "functional", "movement", "sports", "followup"] = (
        "postural"
    )
    mode: Literal["photo", "camera", "video"] = "camera"
    protocol: Literal["static", "bilateral_squat", "single_leg_squat", "arm_raise"] = (
        "static"
    )
    side: Literal["bilateral", "left", "right"] = "bilateral"

    @model_validator(mode="after")
    def valid_protocol(self):
        if self.mode == "video" and self.protocol == "static":
            raise ValueError("Selecione um protocolo de movimento para vídeo.")
        if self.mode != "video" and self.protocol != "static":
            raise ValueError("Protocolos dinâmicos exigem vídeo.")
        if self.protocol == "single_leg_squat" and self.side == "bilateral":
            raise ValueError("Indique o lado de apoio do agachamento unipodal.")
        return self


class VideoJobInput(StrictModel):
    media_id: str
    fps: Literal[2, 5, 10] = 5
    camera_level_confirmed: Literal[True]
    view_confirmed: Literal[True]


class AssessmentUpdate(StrictModel):
    expected_notes: str | None = Field(default=None, max_length=20000)
    expected_conclusion: str | None = Field(default=None, max_length=20000)
    notes: str = Field(default="", max_length=20000)
    conclusion: str = Field(default="", max_length=20000)
    status: Literal["draft", "review", "completed"] = "review"


LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


class Landmark(StrictModel):
    name: str
    x: float = Field(ge=-2, le=3)
    y: float = Field(ge=-2, le=3)
    z: float | None = Field(default=None, ge=-10, le=10)
    visibility: float = Field(ge=0, le=1)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if value not in LANDMARK_NAMES:
            raise ValueError("Landmark desconhecido")
        return value


class AnalyzeInput(StrictModel):
    media_id: str
    provider: Literal["MediaPipePoseProvider"]
    provider_version: str = Field(min_length=1, max_length=160)
    landmarks: list[Landmark] = Field(min_length=1, max_length=33)
    timestamp_ms: float = Field(default=0, ge=0, le=86400000)
    camera_level_confirmed: bool = False
    view_confirmed: bool = False

    @field_validator("landmarks")
    @classmethod
    def unique(cls, value):
        if len({p.name for p in value}) != len(value):
            raise ValueError("Landmarks duplicados")
        return value


class ReviewInput(StrictModel):
    state: Literal["professional_confirmed", "professional_rejected", "needs_review"]
    note: str = Field(default="", max_length=10000)


class UserInput(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "physiotherapist"] = "physiotherapist"
