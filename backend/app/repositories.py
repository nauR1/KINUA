from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assessment, AuditLog, Patient, User


def assessment_for(
    db: Session, identifier: str, user: User, lock: bool = False
) -> Assessment:
    query = select(Assessment).where(
        Assessment.id == identifier, Assessment.clinic_id == user.clinic_id
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query.execution_options(populate_existing=True))
    if not item:
        raise HTTPException(404, "Avaliação não encontrada.")
    return item


def patient_for(
    db: Session, identifier: str, user: User, lock: bool = False
) -> Patient:
    query = select(Patient).where(
        Patient.id == identifier, Patient.clinic_id == user.clinic_id
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query.execution_options(populate_existing=True))
    if not item:
        raise HTTPException(404, "Paciente não encontrado.")
    return item


def audit(db: Session, user: User, action: str, resource_id: str):
    db.add(
        AuditLog(
            clinic_id=user.clinic_id,
            actor_id=user.id,
            action=action,
            resource_id=resource_id,
        )
    )
