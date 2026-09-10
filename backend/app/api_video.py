from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import models as m
from .core.config import settings
from .core.database import get_db
from .core.security import current_user
from .repositories import assessment_for, audit
from .rom import allowed_views
from .schemas import VideoJobInput
from .services.serialization import row
from .storage import LocalStorageProvider
from .vision.video import validate_upload

router = APIRouter()


@router.post("/assessments/{assessment_id}/videos", status_code=201)
def upload_video(
    assessment_id: str,
    file: UploadFile = File(...),
    view: str = Form(...),
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    assessment = assessment_for(db, assessment_id, user)
    if assessment.status == "completed" or assessment.mode != "video":
        raise HTTPException(409, "Use uma avaliação de vídeo ainda não concluída.")
    if view not in ("anterior", "posterior", "lateral_left", "lateral_right"):
        raise HTTPException(422, "Vista inválida.")
    rom = db.get(m.ROMSession, assessment.id)
    if rom and view not in allowed_views(rom.definition, assessment.side):
        raise HTTPException(
            422, "A vista deve corresponder ao plano e lado definidos para este ROM."
        )
    if (
        assessment.protocol == "single_leg_squat"
        and view.startswith("lateral_")
        and view != "lateral_" + assessment.side
    ):
        raise HTTPException(
            422, "A vista lateral deve corresponder ao lado de apoio escolhido."
        )
    extension = Path(file.filename or "").suffix.lower()
    if extension not in (".mp4", ".webm"):
        raise HTTPException(422, "Envie MP4 ou WebM.")
    data = file.file.read(settings().max_video_bytes + 1)
    file.file.close()
    if len(data) > settings().max_video_bytes:
        raise HTTPException(413, "Limite de 100 MB.")
    storage = LocalStorageProvider()
    key, sha = storage.put(data, extension)
    try:
        metadata = validate_upload(storage.path(key))
        media = m.AssessmentMedia(
            assessment_id=assessment.id,
            owner_id=user.id,
            storage_key=key,
            sha256=sha,
            mime=metadata["mime"],
            size=len(data),
            width=metadata["width"],
            height=metadata["height"],
            view=view,
            metadata_json=metadata,
        )
        db.add(media)
        db.flush()
        audit(db, user, "video.uploaded", media.id)
        db.commit()
    except ValueError as exc:
        storage.delete(key)
        raise HTTPException(422, str(exc))
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    result = row(media)
    result.pop("storage_key")
    return result


@router.post("/assessments/{assessment_id}/jobs", status_code=202)
def enqueue(
    assessment_id: str,
    body: VideoJobInput,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    assessment = assessment_for(db, assessment_id, user, lock=True)
    if assessment.status == "completed":
        raise HTTPException(409, "Avaliação concluída.")
    media = db.scalar(
        select(m.AssessmentMedia).where(
            m.AssessmentMedia.id == body.media_id,
            m.AssessmentMedia.assessment_id == assessment.id,
        )
    )
    if not media or not media.mime.startswith("video/"):
        raise HTTPException(404, "Vídeo não encontrado.")
    rom = db.get(m.ROMSession, assessment.id)
    if rom and media.view not in allowed_views(rom.definition, assessment.side):
        raise HTTPException(422, "Plano incompatível com o ROM selecionado.")
    if db.scalar(select(m.Analysis).where(m.Analysis.media_id == media.id)):
        raise HTTPException(409, "Vídeo já analisado. Resultado imutável.")
    job = db.scalar(select(m.ProcessingJob).where(m.ProcessingJob.media_id == media.id))
    if job:
        if job.state in ("pending", "running", "succeeded"):
            raise HTTPException(
                409, "Este vídeo já tem processamento ativo ou concluído."
            )
        job.state = "pending"
        job.progress = 0
        job.error = ""
        job.options = body.model_dump()
        job.updated_at = m.now()
    else:
        job = m.ProcessingJob(
            assessment_id=assessment.id,
            media_id=media.id,
            owner_id=user.id,
            options=body.model_dump(),
        )
        db.add(job)
        db.flush()
    audit(db, user, "video.enqueued", job.id)
    db.commit()
    return row(job)


@router.get("/assessments/{assessment_id}/jobs")
def jobs(
    assessment_id: str,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    assessment_for(db, assessment_id, user)
    return [
        row(j)
        for j in db.scalars(
            select(m.ProcessingJob)
            .where(m.ProcessingJob.assessment_id == assessment_id)
            .order_by(m.ProcessingJob.created_at)
        )
    ]


@router.post("/jobs/{job_id}/cancel")
def cancel(
    job_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db)
):
    job = db.get(m.ProcessingJob, job_id)
    if not job:
        raise HTTPException(404, "Processamento não encontrado.")
    assessment_for(db, job.assessment_id, user)
    result = db.execute(
        update(m.ProcessingJob)
        .where(
            m.ProcessingJob.id == job.id,
            m.ProcessingJob.state.in_(["pending", "running"]),
        )
        .values(state="cancelled", updated_at=m.now())
    )
    if not result.rowcount:
        raise HTTPException(409, "O processamento já terminou.")
    audit(db, user, "video.cancelled", job.id)
    db.commit()
    return {"state": "cancelled"}
