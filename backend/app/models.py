import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    DateTime,
    Float,
    Integer,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .core.database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Clinic(Base):
    __tablename__ = "clinics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="physiotherapist")


class Professional(Base):
    __tablename__ = "professionals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    registration: Mapped[str] = mapped_column(String(80), default="")


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    birth_date: Mapped[str] = mapped_column(String(10))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    notes: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AssessmentMedia(Base):
    __tablename__ = "assessment_media"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    view: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    media_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_media.id"), unique=True
    )
    provider: Mapped[str] = mapped_column(String(100))
    provider_version: Mapped[str] = mapped_column(String(160))
    biomechanics_version: Mapped[str] = mapped_column(String(30))
    rules_version: Mapped[str] = mapped_column(String(30))
    quality: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PoseFrame(Base):
    __tablename__ = "pose_frames"
    __table_args__ = (UniqueConstraint("analysis_id", "frame_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[float] = mapped_column(Float)


class PoseLandmark(Base):
    __tablename__ = "pose_landmarks"
    __table_args__ = (UniqueConstraint("frame_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    frame_id: Mapped[str] = mapped_column(ForeignKey("pose_frames.id"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility: Mapped[float] = mapped_column(Float)


class BiomechanicalMeasurement(Base):
    __tablename__ = "biomechanical_measurements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    details: Mapped[dict] = mapped_column(JSON)


class ClinicalRule(Base):
    __tablename__ = "clinical_rules"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(30))
    definition: Mapped[dict] = mapped_column(JSON)


class AttentionFinding(Base):
    __tablename__ = "attention_findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    measurement_id: Mapped[str] = mapped_column(
        ForeignKey("biomechanical_measurements.id")
    )
    region: Mapped[str] = mapped_column(String(40))
    side: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20), default="informational")
    state: Mapped[str] = mapped_column(String(30), default="needs_review")
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[dict] = mapped_column(JSON)


class ProfessionalReview(Base):
    __tablename__ = "professional_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("attention_findings.id"), index=True
    )
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    sha256: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
