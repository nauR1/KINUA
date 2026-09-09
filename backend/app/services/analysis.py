from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import (
    AssessmentMedia,
    Analysis,
    PoseFrame,
    PoseLandmark,
    BiomechanicalMeasurement,
    AttentionFinding,
    User,
)
from ..schemas import AnalyzeInput
from ..repositories import assessment_for, audit
from ..storage import LocalStorageProvider, brightness
from ..biomechanics.engine import BiomechanicsEngine
from ..clinical.engine import ClinicalRulesEngine, AttentionEngine


def analyze(
    db: Session, assessment_id: str, body: AnalyzeInput, user: User
) -> Analysis:
    assessment = assessment_for(db, assessment_id, user)
    if assessment.status == "completed":
        raise HTTPException(
            409, "Avaliação concluída. Crie uma nova avaliação para outra captura."
        )
    media = db.scalar(
        select(AssessmentMedia).where(
            AssessmentMedia.id == body.media_id,
            AssessmentMedia.assessment_id == assessment.id,
        )
    )
    if not media:
        raise HTTPException(404, "Mídia não encontrada nesta avaliação.")
    if db.scalar(select(Analysis).where(Analysis.media_id == media.id)):
        raise HTTPException(
            409, "Esta captura já foi analisada. Os resultados são imutáveis."
        )
    engine, clinical, attention = (
        BiomechanicsEngine(),
        ClinicalRulesEngine(),
        AttentionEngine(),
    )
    measures, quality = engine.analyze(
        body.landmarks,
        media.width,
        media.height,
        media.view,
        body.camera_level_confirmed,
        body.view_confirmed,
        brightness(LocalStorageProvider().path(media.storage_key)),
    )
    analysis = Analysis(
        assessment_id=assessment.id,
        media_id=media.id,
        provider=body.provider,
        provider_version=body.provider_version,
        biomechanics_version=engine.version,
        rules_version=clinical.version,
        quality=quality,
    )
    db.add(analysis)
    db.flush()
    frame = PoseFrame(
        analysis_id=analysis.id, frame_index=0, timestamp_ms=body.timestamp_ms
    )
    db.add(frame)
    db.flush()
    for p in body.landmarks:
        db.add(PoseLandmark(frame_id=frame.id, **p.model_dump()))
    for m in measures:
        measurement = BiomechanicalMeasurement(analysis_id=analysis.id, **m)
        db.add(measurement)
        db.flush()
        if m["value"] is not None:
            finding = attention.explain(m)
            finding["explanation"]["timestamp_ms"] = body.timestamp_ms
            finding["explanation"]["clinical_matches"] = clinical.evaluate(m)
            db.add(
                AttentionFinding(
                    analysis_id=analysis.id, measurement_id=measurement.id, **finding
                )
            )
    assessment.status = "review"
    audit(db, user, "analysis.created", analysis.id)
    db.commit()
    return analysis
