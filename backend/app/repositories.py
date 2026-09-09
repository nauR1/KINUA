from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Assessment, Patient, User, AuditLog


def assessment_for(db: Session, identifier: str, user: User) -> Assessment:
    item = db.scalar(
        select(Assessment).where(
            Assessment.id == identifier, Assessment.clinic_id == user.clinic_id
        )
    )
    if not item:
        raise HTTPException(404, "Avaliação não encontrada.")
    return item


def patient_for(db: Session, identifier: str, user: User) -> Patient:
    item = db.scalar(
        select(Patient).where(
            Patient.id == identifier, Patient.clinic_id == user.clinic_id
        )
    )
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
