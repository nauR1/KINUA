"""Explicit synthetic demo bootstrap. Never imported by application startup."""

import argparse
import getpass
import os
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import delete, select

from . import models as m
from .api_admin import UserCreate
from .core.config import settings
from .core.database import Base, SessionLocal
from .core.security import digest, hasher
from .storage import get_storage, validate_storage_key

# Ownership edges, deliberately excluding actors and globally shared catalogs.
OWNERSHIP = {
    "users": ("clinic_id", "clinics"),
    "patients": ("clinic_id", "clinics"),
    "assessments": ("clinic_id", "clinics"),
    "audit_logs": ("clinic_id", "clinics"),
    "professionals": ("user_id", "users"),
    "sessions": ("user_id", "users"),
    "assessment_media": ("assessment_id", "assessments"),
    "analyses": ("assessment_id", "assessments"),
    "processing_jobs": ("assessment_id", "assessments"),
    "pose_frames": ("analysis_id", "analyses"),
    "pose_landmarks": ("frame_id", "pose_frames"),
    "biomechanical_measurements": ("analysis_id", "analyses"),
    "attention_findings": ("analysis_id", "analyses"),
    "professional_reviews": ("finding_id", "attention_findings"),
    "reports": ("assessment_id", "assessments"),
    "assessment_protocols": ("assessment_id", "assessments"),
    "assessment_step_results": ("assessment_protocol_id", "assessment_protocols"),
    "rom_sessions": ("assessment_id", "assessments"),
    "rom_measurements": ("analysis_id", "analyses"),
}


def chunks(values):
    values = list(values)
    for index in range(0, len(values), 500):
        yield values[index : index + 500]


def demo_key(key, clinic_id):
    validate_storage_key(key)
    if not key.startswith("demo/" + clinic_id + "/"):
        raise ValueError("Reset recusado: mídia fora do prefixo desta demonstração.")


def reset_rows(db, clinic):
    if not clinic.is_demo:
        raise ValueError("Reset recusado: clínica não é demonstração.")
    users = list(db.scalars(select(m.User).where(m.User.clinic_id == clinic.id)))
    if any(u.role == "platform_admin" for u in users):
        raise ValueError("Reset recusado: clínica contém platform_admin.")
    active = db.scalar(
        select(m.ProcessingJob.id)
        .join(m.Assessment)
        .where(
            m.Assessment.clinic_id == clinic.id,
            m.ProcessingJob.state.in_(["pending", "running"]),
        )
    )
    if active:
        raise ValueError("Aguarde a conclusão ou cancele os jobs demo antes do reset.")
    ids = {"clinics": {clinic.id}}
    rows = {}
    tables = Base.metadata.sorted_tables
    for table in tables:
        if table.name not in OWNERSHIP:
            continue
        column, parent = OWNERSHIP[table.name]
        pk = list(table.primary_key)[0]
        found = []
        for group in chunks(ids.get(parent, set())):
            found.extend(
                db.execute(select(table).where(table.c[column].in_(group))).mappings()
            )
        rows[table.name] = found
        ids[table.name] = {row[pk.name] for row in found}
    # Fail closed if malformed cross-tenant references would otherwise be affected.
    for table in tables:
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent == "clinics" or not ids.get(parent):
                continue
            pk = list(table.primary_key)[0]
            for group in chunks(ids[parent]):
                linked = db.scalars(select(pk).where(fk.parent.in_(group))).all()
                if any(value not in ids.get(table.name, set()) for value in linked):
                    raise ValueError(
                        "Reset recusado: referência externa ao tenant demo."
                    )
    for media in rows.get("assessment_media", []):
        demo_key(media["storage_key"], clinic.id)
        if not db.scalar(
            select(m.DemoMediaCleanup.id).where(
                m.DemoMediaCleanup.storage_key == media["storage_key"]
            )
        ):
            db.add(
                m.DemoMediaCleanup(
                    clinic_id=clinic.id, storage_key=media["storage_key"]
                )
            )
    db.flush()
    for table in reversed(tables):
        if table.name not in OWNERSHIP:
            continue
        pk = list(table.primary_key)[0]
        for group in chunks(ids.get(table.name, set())):
            db.execute(delete(table).where(pk.in_(group)))
    for user in users:
        db.execute(
            delete(m.LoginAttempt).where(m.LoginAttempt.key == digest(user.email))
        )
    db.expire_all()


def cleanup_media(factory, clinic_id):
    storage = get_storage()
    removed = 0
    try:
        with factory.begin() as db:
            clinic = db.scalar(
                select(m.Clinic).where(m.Clinic.id == clinic_id).with_for_update()
            )
            if not clinic or not clinic.is_demo:
                raise ValueError("Limpeza recusada: clínica não é demo.")
            queue = list(
                db.scalars(
                    select(m.DemoMediaCleanup).where(
                        m.DemoMediaCleanup.clinic_id == clinic_id
                    )
                )
            )
            for item in queue:
                demo_key(item.storage_key, clinic_id)
                if db.scalar(
                    select(m.AssessmentMedia.id).where(
                        m.AssessmentMedia.storage_key == item.storage_key
                    )
                ):
                    raise ValueError("Mídia ainda referenciada; limpeza recusada.")
                storage.delete(item.storage_key)
                db.delete(item)
                removed += 1
    finally:
        storage.close()
    return removed


def seed_demo(factory, email, password, reset=False):
    if not settings().allow_demo_seed:
        raise ValueError(
            "Demo seed desabilitado. Exige ALLOW_DEMO_SEED=true explicitamente."
        )
    # Same password/name/email validation as regular user provisioning.
    body = UserCreate(name="Profissional Demonstração", email=email, password=password)
    with factory.begin() as db:
        existing = db.scalar(select(m.User).where(m.User.email == body.email.lower()))
        if existing:
            clinic = db.scalar(
                select(m.Clinic)
                .where(m.Clinic.id == existing.clinic_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if not clinic.is_demo or existing.role == "platform_admin":
                raise ValueError(
                    "E-mail pertence a conta não demonstrativa; nenhuma alteração realizada."
                )
            clinic_id = clinic.id
            if reset:
                reset_rows(db, clinic)
            else:
                clinic = None
        else:
            clinic = m.Clinic(
                name="KINUA — Ambiente de Demonstração",
                is_demo=True,
                is_active=True,
                plan_code="custom",
                subscription_status="active",
            )
            db.add(clinic)
            db.flush()
            clinic_id = clinic.id
        if clinic is not None:
            clinic.is_active = True
            clinic.access_expires_at = None
            clinic.access_starts_at = None
            clinic.suspended_at = None
            clinic.suspension_reason = None
            user = m.User(
                clinic_id=clinic.id,
                name=body.name,
                email=body.email.lower(),
                password_hash=hasher.hash(body.password),
                role="admin",
            )
            db.add(user)
            db.flush()
            db.add(m.Professional(user_id=user.id, registration="DEMONSTRAÇÃO"))
            patients = []
            for name, birth in [
                ("Ana Demonstração", "1990-05-12"),
                ("Carlos Exemplo", "1985-08-20"),
                ("Marina Teste", "1998-03-03"),
            ]:
                patient = m.Patient(
                    clinic_id=clinic.id,
                    name=name,
                    birth_date=birth,
                    details={
                        "notes": "Registro sintético de demonstração. Não representa pessoa real."
                    },
                )
                db.add(patient)
                db.flush()
                patients.append(patient)
            for patient, days, kind, state in [
                (patients[0], 30, "postural", "completed"),
                (patients[0], 0, "followup", "draft"),
                (patients[1], 2, "functional", "draft"),
            ]:
                db.add(
                    m.Assessment(
                        clinic_id=clinic.id,
                        patient_id=patient.id,
                        created_by=user.id,
                        kind=kind,
                        mode="photo",
                        protocol="static",
                        status=state,
                        created_at=m.now() - timedelta(days=days),
                        notes="DEMONSTRAÇÃO: avaliação sem captura ou medidas automatizadas.",
                        conclusion="Registro demonstrativo concluído para apresentar o histórico; sem resultados clínicos."
                        if state == "completed"
                        else "",
                    )
                )
            db.add(
                m.AuditLog(
                    clinic_id=clinic.id,
                    actor_id=user.id,
                    action="demo.reset" if reset else "demo.created",
                    resource_id=clinic.id,
                    changes={"synthetic": True},
                )
            )
    # No object is deleted before the database transaction commits.
    cleanup_media(factory, clinic_id)
    return clinic_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if not settings().allow_demo_seed:
        raise SystemExit("Demo seed desabilitado. Exige ALLOW_DEMO_SEED=true.")
    password = os.environ.get("DEMO_PASSWORD") or getpass.getpass(
        "Senha da demo (12–128 caracteres): "
    )
    try:
        seed_demo(SessionLocal, args.email, password, args.reset)
    except ValidationError:
        raise SystemExit(
            "Dados inválidos. Verifique e-mail e senha de 12–128 caracteres; valores omitidos por segurança."
        ) from None
    except Exception as exc:
        # External storage can fail after DB commit. Queue remains safe to retry.
        raise SystemExit(
            "Demo não finalizada: "
            + str(exc)
            + ". Reexecute sem --reset para retomar eventual limpeza pendente."
        ) from None
    print(
        "Demonstração preparada. Use somente dados fictícios. Nenhuma senha foi exibida."
    )


if __name__ == "__main__":
    main()
