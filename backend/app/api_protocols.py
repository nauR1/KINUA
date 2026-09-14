"""Guided assessment protocols and ROM entry points, scoped to the current clinic."""

from copy import deepcopy
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .core.database import get_db
from .core.security import current_user
from .repositories import assessment_for, audit, patient_for
from .rom import DEFINITIONS, VERSION, ROMEngine
from .rom import definition as rom_definition
from .schemas import Landmark, StrictModel
from .services.serialization import row

router = APIRouter()


class ROMPreview(StrictModel):
    movement: str
    side: Literal["left", "right", "bilateral"]
    view: Literal["anterior", "posterior", "lateral_left", "lateral_right"]
    landmarks: list[Landmark] = Field(max_length=33)
    width: int = Field(ge=64, le=4096)
    height: int = Field(ge=64, le=4096)
    brightness: float = Field(ge=0, le=1)
    plane_confirmed: Literal[True]

    @field_validator("landmarks")
    @classmethod
    def unique_landmarks(cls, value):
        if len({p.name for p in value}) != len(value):
            raise ValueError("Landmarks duplicados")
        return value


@router.post("/rom/preview")
def preview(body: ROMPreview, user: m.User = Depends(current_user)):
    if body.movement not in DEFINITIONS:
        raise HTTPException(422, "Movimento não suportado.")
    measures, quality = ROMEngine(rom_definition(body.movement)).measure(
        body.landmarks,
        body.width,
        body.height,
        body.view,
        "rom",
        body.side,
        body.brightness,
    )
    return {"measurements": measures, "quality": quality}


class StartProtocol(StrictModel):
    patient_id: str
    version_id: str


class StepUpdate(StrictModel):
    revision: int = Field(ge=0)
    state: Literal["not_started", "in_progress", "completed", "skipped"]
    result: str = Field(default="", max_length=20000)
    note: str = Field(default="", max_length=10000)


class CaptureStart(StrictModel):
    movement: str | None = None
    side: Literal["left", "right", "bilateral"] = "right"


class ROMStart(CaptureStart):
    patient_id: str
    movement: str


class ProtocolComplete(StrictModel):
    conclusion: str = Field(min_length=1, max_length=20000)


def get_run(db, assessment_id):
    return db.scalar(
        select(m.AssessmentProtocol).where(
            m.AssessmentProtocol.assessment_id == assessment_id
        )
    )


def protocol_result(db, run):
    result = row(run)
    result["steps"] = []
    rows = {
        s.step_key: s
        for s in db.scalars(
            select(m.AssessmentStepResult).where(
                m.AssessmentStepResult.assessment_protocol_id == run.id
            )
        )
    }
    for definition in run.snapshot["steps"]:
        step = rows[definition["key"]]
        child = (
            db.get(m.Assessment, step.child_assessment_id)
            if step.child_assessment_id
            else None
        )
        result["steps"].append(
            {
                **row(step),
                "definition": definition,
                "child": row(child) if child else None,
            }
        )
    return result


def mutable_step(db, assessment_id, key, user):
    parent = assessment_for(db, assessment_id, user, lock=True)
    if parent.status == "completed":
        raise HTTPException(409, "Protocolo concluído é imutável.")
    run = get_run(db, parent.id)
    if not run:
        raise HTTPException(404, "Protocolo não encontrado.")
    step = db.scalar(
        select(m.AssessmentStepResult)
        .where(
            m.AssessmentStepResult.assessment_protocol_id == run.id,
            m.AssessmentStepResult.step_key == key,
        )
        .execution_options(populate_existing=True)
    )
    if not step:
        raise HTTPException(404, "Etapa não encontrada.")
    config = next(d for d in run.snapshot["steps"] if d["key"] == key)
    return parent, run, step, config


def make_rom(db, user, patient_id, movement, side):
    if movement not in DEFINITIONS:
        raise HTTPException(422, "Movimento ROM não suportado.")
    config = rom_definition(movement)
    if config["plane"] == "sagittal" and side == "bilateral":
        raise HTTPException(
            422,
            "ROM sagital exige um lado por captura; avalie o lado oposto separadamente.",
        )
    child = m.Assessment(
        clinic_id=user.clinic_id,
        patient_id=patient_id,
        created_by=user.id,
        kind="movement",
        mode="video",
        protocol="rom",
        side=side,
    )
    db.add(child)
    db.flush()
    db.add(
        m.ROMSession(
            assessment_id=child.id,
            movement=movement,
            definition=deepcopy(config),
            version=VERSION,
        )
    )
    audit(db, user, "rom.started", child.id)
    return child


@router.get("/protocols")
def catalog(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "categories": [
            row(c)
            for c in db.scalars(
                select(m.ProtocolCategory).order_by(m.ProtocolCategory.name)
            )
        ],
        "versions": [
            {**row(v), "protocol": row(db.get(m.Protocol, v.protocol_id))}
            for v in db.scalars(
                select(m.ProtocolVersion).order_by(m.ProtocolVersion.id)
            )
        ],
    }


@router.post("/assessment-protocols", status_code=201)
def start(
    body: StartProtocol,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    patient_for(db, body.patient_id, user)
    version = db.get(m.ProtocolVersion, body.version_id)
    if not version:
        raise HTTPException(404, "Versão de protocolo não encontrada.")
    assessment = m.Assessment(
        clinic_id=user.clinic_id,
        patient_id=body.patient_id,
        created_by=user.id,
        kind="functional",
        mode="camera",
        protocol="static",
    )
    db.add(assessment)
    db.flush()
    run = m.AssessmentProtocol(
        assessment_id=assessment.id,
        version_id=version.id,
        snapshot=deepcopy(version.definition),
    )
    db.add(run)
    db.flush()
    for step in run.snapshot["steps"]:
        db.add(
            m.AssessmentStepResult(assessment_protocol_id=run.id, step_key=step["key"])
        )
    audit(db, user, "protocol.started", assessment.id)
    db.commit()
    return {"assessment_id": assessment.id}


@router.get("/assessment-protocols/{assessment_id}")
def get_protocol(
    assessment_id: str,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    assessment_for(db, assessment_id, user)
    run = get_run(db, assessment_id)
    if not run:
        raise HTTPException(404, "Protocolo não encontrado.")
    return protocol_result(db, run)


@router.patch("/assessment-protocols/{assessment_id}/steps/{key}")
def update_step(
    assessment_id: str,
    key: str,
    body: StepUpdate,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    parent, run, step, config = mutable_step(db, assessment_id, key, user)
    if step.revision != body.revision:
        raise HTTPException(
            409, "Etapa alterada em outra janela. Recarregue antes de salvar."
        )
    if not config["available"] and body.state not in ("not_started", "skipped"):
        raise HTTPException(
            422,
            "Esta etapa pertence a um módulo futuro; não pode ser marcada como realizada.",
        )
    child = (
        db.get(m.Assessment, step.child_assessment_id)
        if step.child_assessment_id
        else None
    )
    if body.state == "skipped":
        if not config["optional"] or not body.note:
            raise HTTPException(
                422, "Etapa obrigatória ou justificativa de salto ausente."
            )
        if child and child.status != "completed":
            raise HTTPException(
                409, "Conclua e revise a captura vinculada antes de pular a etapa."
            )
    if body.state == "completed":
        if config["kind"] in ("capture", "rom"):
            if not child or not db.scalar(
                select(m.Analysis.id).where(m.Analysis.assessment_id == child.id)
            ):
                raise HTTPException(409, "A etapa exige uma captura com análise salva.")
        elif not body.result:
            raise HTTPException(
                422, "Registre o resultado profissional antes de concluir a etapa."
            )
        if key == "review":
            linked = db.scalars(
                select(m.Assessment)
                .join(
                    m.AssessmentStepResult,
                    m.AssessmentStepResult.child_assessment_id == m.Assessment.id,
                )
                .where(m.AssessmentStepResult.assessment_protocol_id == run.id)
            ).all()
            if any(a.status != "completed" for a in linked):
                raise HTTPException(
                    409, "Revise e conclua as avaliações vinculadas primeiro."
                )
        if key == "report" and not db.scalar(
            select(m.Report.id).where(m.Report.assessment_id == parent.id)
        ):
            raise HTTPException(
                409, "Gere um relatório antes de marcar esta etapa como concluída."
            )
    previous = step.state
    step.state = body.state
    step.result = body.result
    step.note = body.note
    if body.state in ("in_progress", "completed") and not step.started_at:
        step.started_at = m.now()
    if previous != body.state:
        step.completed_at = m.now() if body.state == "completed" else None
        step.skipped_at = m.now() if body.state == "skipped" else None
    step.revision += 1
    step.updated_by = user.id
    step.updated_at = m.now()
    parent.status = "review"
    audit(db, user, "protocol.step." + body.state, step.id)
    db.commit()
    return protocol_result(db, run)


@router.post(
    "/assessment-protocols/{assessment_id}/steps/{key}/capture", status_code=201
)
def capture_step(
    assessment_id: str,
    key: str,
    body: CaptureStart,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    parent, run, step, config = mutable_step(db, assessment_id, key, user)
    if step.child_assessment_id:
        return {"assessment_id": step.child_assessment_id}
    if not config["available"] or config["kind"] not in ("capture", "rom"):
        raise HTTPException(422, "Esta etapa não oferece captura.")
    if config["kind"] == "rom":
        if body.movement not in config.get("movements", []):
            raise HTTPException(422, "Movimento incompatível com esta etapa.")
        child = make_rom(db, user, parent.patient_id, body.movement, body.side)
    else:
        protocol = config["capture_protocol"]
        if protocol == "single_leg_squat" and body.side == "bilateral":
            raise HTTPException(422, "Escolha o lado de apoio.")
        child = m.Assessment(
            clinic_id=user.clinic_id,
            patient_id=parent.patient_id,
            created_by=user.id,
            kind="postural" if protocol == "static" else "movement",
            mode="camera" if protocol == "static" else "video",
            protocol=protocol,
            side=body.side,
        )
        db.add(child)
        db.flush()
    step.child_assessment_id = child.id
    step.state = "in_progress"
    step.started_at = step.started_at or m.now()
    step.revision += 1
    step.updated_by = user.id
    step.updated_at = m.now()
    audit(db, user, "protocol.capture.created", child.id)
    db.commit()
    return {"assessment_id": child.id}


@router.post("/assessment-protocols/{assessment_id}/complete")
def complete(
    assessment_id: str,
    body: ProtocolComplete,
    user: m.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    parent, run, _, _ = mutable_step(db, assessment_id, "review", user)
    for step in protocol_result(db, run)["steps"]:
        if step["state"] not in ("completed", "skipped") or (
            step["state"] == "skipped" and not step["definition"]["optional"]
        ):
            raise HTTPException(
                409,
                "Conclua ou justifique o salto de todas as etapas antes de finalizar.",
            )
        if step["child"] and step["child"]["status"] != "completed":
            raise HTTPException(
                409, "Existem avaliações vinculadas ainda não concluídas."
            )
    parent.conclusion = body.conclusion
    parent.status = "completed"
    audit(db, user, "protocol.completed", parent.id)
    db.commit()
    return {"assessment_id": parent.id, "status": parent.status}


@router.get("/rom/movements")
def movements(user: m.User = Depends(current_user)):
    return [rom_definition(key) for key in DEFINITIONS]


@router.post("/rom/assessments", status_code=201)
def start_rom(
    body: ROMStart, user: m.User = Depends(current_user), db: Session = Depends(get_db)
):
    patient_for(db, body.patient_id, user)
    child = make_rom(db, user, body.patient_id, body.movement, body.side)
    db.commit()
    return {"assessment_id": child.id}


@router.get("/patients/{patient_id}/rom")
def rom_history(
    patient_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db)
):
    patient_for(db, patient_id, user)
    records = db.execute(
        select(
            m.ROMMeasurement,
            m.Analysis,
            m.Assessment,
            m.AssessmentMedia.view,
            m.AttentionFinding.state,
        )
        .join(m.Analysis, m.Analysis.id == m.ROMMeasurement.analysis_id)
        .join(m.Assessment, m.Assessment.id == m.Analysis.assessment_id)
        .join(m.AssessmentMedia, m.AssessmentMedia.id == m.Analysis.media_id)
        .outerjoin(
            m.AttentionFinding,
            m.AttentionFinding.measurement_id == m.ROMMeasurement.measurement_id,
        )
        .where(
            m.Assessment.patient_id == patient_id,
            m.Assessment.clinic_id == user.clinic_id,
        )
        .order_by(m.Assessment.created_at, m.Analysis.created_at, m.ROMMeasurement.id)
    ).all()
    result = []
    for measurement, analysis, assessment, view, review_state in records:
        result.append(
            {
                **row(measurement),
                "assessment_id": assessment.id,
                "created_at": row(analysis)["created_at"],
                "view": view,
                "provider_version": analysis.provider_version,
                "engine_version": analysis.biomechanics_version,
                "fps": analysis.motion.get("target_fps"),
                "review_state": review_state or "needs_review",
            }
        )
    return result


@router.get("/protocols/pending")
def pending(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        {
            "assessment": row(a),
            "name": r.snapshot["name"],
            "version": r.snapshot["version"],
            "completed_steps": db.scalar(
                select(func.count())
                .select_from(m.AssessmentStepResult)
                .where(
                    m.AssessmentStepResult.assessment_protocol_id == r.id,
                    m.AssessmentStepResult.state.in_(["completed", "skipped"]),
                )
            ),
            "total_steps": len(r.snapshot["steps"]),
        }
        for r, a in db.execute(
            select(m.AssessmentProtocol, m.Assessment)
            .join(m.Assessment, m.Assessment.id == m.AssessmentProtocol.assessment_id)
            .where(
                m.Assessment.clinic_id == user.clinic_id,
                m.Assessment.status != "completed",
            )
            .order_by(m.Assessment.created_at.desc())
        ).all()
    ]
