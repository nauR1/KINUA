import hashlib
import secrets
from datetime import timedelta
from typing import Literal

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from . import models as m
from . import schemas as s
from .api_protocols import router as protocol_router
from .api_video import router as video_router
from .clinical.engine import RULESET
from .core.body_limit import BodyLimitMiddleware
from .core.config import settings
from .core.database import get_db
from .core.security import (
    DUMMY_HASH,
    admin,
    current_user,
    digest,
    hasher,
    utc,
    verify_password,
)
from .reports import make_pdf
from .repositories import assessment_for, audit, patient_for
from .services.analysis import analyze
from .services.comparison import compare
from .services.serialization import assessment_result, row
from .storage import LocalStorageProvider, normalize_image

app = FastAPI(title="KINUA API", version="2.2.1")
app.include_router(video_router)
app.include_router(protocol_router)


@app.get("/comparisons")
def comparison(
    a: str,
    b: str,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    return compare(db, user, a, b)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Requested-With"],
)
app.add_middleware(
    BodyLimitMiddleware,
    max_bytes=settings().max_upload_bytes + 1024 * 1024,
    video_bytes=settings().max_video_bytes + 1024 * 1024,
)


@app.middleware("http")
async def protect(request: Request, call_next):
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin not in settings().origins:
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        if request.headers.get("x-requested-with") != "Biometria":
            return JSONResponse(
                {"detail": "Cabeçalho de proteção ausente."}, status_code=403
            )
        content_length = request.headers.get("content-length")
        if content_length and (
            not content_length.isdigit()
            or int(content_length)
            > (
                settings().max_video_bytes
                if request.url.path.endswith("/videos")
                else settings().max_upload_bytes
            )
            + 1024 * 1024
        ):
            return JSONResponse(
                {"detail": "Arquivo ou requisição excede o limite."}, status_code=413
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {"detail": "Conflito de gravação. Atualize a página e tente novamente."},
        status_code=409,
    )


@app.get("/health")
def health(db: DBSession = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "service": "biometria", "version": app.version}


@app.post("/auth/login")
def login(body: s.Login, response: Response, db: DBSession = Depends(get_db)):
    email = body.email.lower()
    key = digest(email)
    attempt = db.get(m.LoginAttempt, key)
    if attempt and utc(attempt.window_start) < m.now() - timedelta(minutes=15):
        db.delete(attempt)
        db.flush()
        attempt = None
    if attempt and attempt.count >= 5:
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos.")
    user = db.scalar(select(m.User).where(m.User.email == email))
    valid = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not valid or not user:
        if not attempt:
            attempt = m.LoginAttempt(key=key, count=0)
            db.add(attempt)
        attempt.count += 1
        db.commit()
        raise HTTPException(401, "E-mail ou senha inválidos.")
    if attempt:
        db.delete(attempt)
    token = secrets.token_urlsafe(48)
    db.add(
        m.Session(
            token_hash=digest(token),
            user_id=user.id,
            expires_at=m.now() + timedelta(hours=settings().session_hours),
        )
    )
    audit(db, user, "auth.login", user.id)
    db.commit()
    response.set_cookie(
        "biometria_session",
        token,
        httponly=True,
        secure=settings().secure_cookies,
        samesite="strict",
        max_age=settings().session_hours * 3600,
        path="/",
    )
    return {"id": user.id, "name": user.name, "role": user.role}


@app.get("/auth/me")
def me(user: m.User = Depends(current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "clinic_id": user.clinic_id,
    }


@app.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    db.execute(
        delete(m.Session).where(
            m.Session.token_hash == digest(request.cookies.get("biometria_session", ""))
        )
    )
    audit(db, user, "auth.logout", user.id)
    db.commit()
    response.delete_cookie("biometria_session", path="/")
    return {"ok": True}


@app.get("/dashboard")
def dashboard(user: m.User = Depends(current_user), db: DBSession = Depends(get_db)):
    scope = m.Assessment.clinic_id == user.clinic_id
    recent = db.scalars(
        select(m.Assessment)
        .where(scope)
        .order_by(m.Assessment.created_at.desc())
        .limit(8)
    )
    return {
        "patients": db.scalar(
            select(func.count())
            .select_from(m.Patient)
            .where(m.Patient.clinic_id == user.clinic_id)
        ),
        "assessments": db.scalar(
            select(func.count()).select_from(m.Assessment).where(scope)
        ),
        "pending": db.scalar(
            select(func.count())
            .select_from(m.Assessment)
            .where(scope, m.Assessment.status != "completed")
        ),
        "last_30_days": db.scalar(
            select(func.count())
            .select_from(m.Assessment)
            .where(scope, m.Assessment.created_at >= m.now() - timedelta(days=30))
        ),
        "recent": [row(a) for a in recent],
    }


@app.get("/patients")
def patients(
    q: str = "", user: m.User = Depends(current_user), db: DBSession = Depends(get_db)
):
    stmt = select(m.Patient).where(m.Patient.clinic_id == user.clinic_id)
    if q:
        stmt = stmt.where(m.Patient.name.ilike("%" + q[:160] + "%"))
    return [
        row(p)
        for p in db.scalars(stmt.order_by(m.Patient.created_at.desc()).limit(500))
    ]


@app.post("/patients", status_code=201)
def create_patient(
    body: s.PatientInput,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    data = body.model_dump(mode="json")
    patient = m.Patient(
        clinic_id=user.clinic_id,
        name=data.pop("name"),
        birth_date=data.pop("birth_date"),
        details=data,
    )
    db.add(patient)
    db.flush()
    audit(db, user, "patient.created", patient.id)
    db.commit()
    return row(patient)


@app.patch("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    body: s.PatientUpdate,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    patient = patient_for(db, patient_id, user, lock=True)
    if (
        body.expected_revision is not None
        and body.expected_revision != row(patient)["revision"]
    ):
        raise HTTPException(
            409, "Paciente alterado em outra janela. Reabra o cadastro antes de salvar."
        )
    data = body.model_dump(mode="json", exclude={"expected_revision"})
    patient.name, patient.birth_date = data.pop("name"), data.pop("birth_date")
    patient.details = data
    audit(db, user, "patient.updated", patient.id)
    db.commit()
    return row(patient)


@app.get("/patients/{patient_id}/assessments")
def history(
    patient_id: str,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    patient_for(db, patient_id, user)
    return [
        row(a)
        for a in db.scalars(
            select(m.Assessment)
            .where(
                m.Assessment.patient_id == patient_id,
                m.Assessment.clinic_id == user.clinic_id,
            )
            .order_by(m.Assessment.created_at.desc())
        )
    ]


@app.post("/assessments", status_code=201)
def create_assessment(
    body: s.AssessmentInput,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    patient_for(db, body.patient_id, user)
    assessment = m.Assessment(
        clinic_id=user.clinic_id, created_by=user.id, **body.model_dump()
    )
    db.add(assessment)
    db.flush()
    audit(db, user, "assessment.created", assessment.id)
    db.commit()
    return row(assessment)


@app.get("/assessments/{assessment_id}")
def get_assessment(
    assessment_id: str,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    return assessment_result(db, assessment_for(db, assessment_id, user))


@app.patch("/assessments/{assessment_id}")
def update_assessment(
    assessment_id: str,
    body: s.AssessmentUpdate,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    assessment = assessment_for(db, assessment_id, user, lock=True)
    if assessment.status == "completed":
        raise HTTPException(
            409, "Avaliação concluída é imutável. Crie um acompanhamento."
        )
    for field in ("notes", "conclusion"):
        expected = getattr(body, "expected_" + field)
        if expected is not None and expected != getattr(assessment, field):
            raise HTTPException(
                409,
                "Observações alteradas em outra janela. Reabra a avaliação antes de salvar.",
            )
    if body.status == "completed":
        if db.scalar(
            select(m.AssessmentProtocol.id).where(
                m.AssessmentProtocol.assessment_id == assessment.id
            )
        ):
            raise HTTPException(
                409, "Conclua pelo roteiro do protocolo, após revisar todas as etapas."
            )
        if db.scalar(
            select(m.ProcessingJob).where(
                m.ProcessingJob.assessment_id == assessment.id,
                m.ProcessingJob.state.in_(["pending", "running"]),
            )
        ):
            raise HTTPException(
                409, "Aguarde ou cancele o processamento de vídeo antes de concluir."
            )
        findings = db.scalars(
            select(m.AttentionFinding)
            .join(m.Analysis)
            .where(m.Analysis.assessment_id == assessment.id)
        ).all()
        if not findings or any(
            f.state in ("needs_review", "detected") for f in findings
        ):
            raise HTTPException(
                409, "Revise todos os registros de medida antes de concluir."
            )
        conclusion = (
            body.conclusion
            if "conclusion" in body.model_fields_set
            else assessment.conclusion
        )
        if not conclusion:
            raise HTTPException(
                422, "Escreva a conclusão profissional antes de concluir."
            )
    for key, value in body.model_dump(
        exclude_unset=True, exclude={"expected_notes", "expected_conclusion"}
    ).items():
        setattr(assessment, key, value)
    audit(db, user, "assessment.updated", assessment.id)
    db.commit()
    return assessment_result(db, assessment)


@app.post("/assessments/{assessment_id}/media", status_code=201)
async def upload(
    assessment_id: str,
    file: UploadFile = File(...),
    view: Literal["anterior", "posterior", "lateral_right", "lateral_left"] = Form(...),
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    assessment = assessment_for(db, assessment_id, user)
    if assessment.status == "completed":
        raise HTTPException(409, "Avaliação concluída.")
    if db.scalar(
        select(m.AssessmentProtocol.id).where(
            m.AssessmentProtocol.assessment_id == assessment.id
        )
    ):
        raise HTTPException(
            409, "Abra a etapa de captura do protocolo para enviar mídia."
        )
    if assessment.mode == "video":
        raise HTTPException(422, "Use upload de vídeo para este protocolo.")
    data = await file.read(settings().max_upload_bytes + 1)
    await file.close()
    if len(data) > settings().max_upload_bytes:
        raise HTTPException(413, "Arquivo excede 20 MB.")
    normalized, width, height = normalize_image(data)
    storage = LocalStorageProvider()
    key, sha = storage.put(normalized)
    try:
        media = m.AssessmentMedia(
            assessment_id=assessment.id,
            owner_id=user.id,
            storage_key=key,
            sha256=sha,
            mime="image/jpeg",
            size=len(normalized),
            width=width,
            height=height,
            view=view,
        )
        db.add(media)
        db.flush()
        audit(db, user, "media.uploaded", media.id)
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    result = row(media)
    result.pop("storage_key")
    return result


@app.get("/media/{media_id}")
def media_file(
    media_id: str, user: m.User = Depends(current_user), db: DBSession = Depends(get_db)
):
    media = db.get(m.AssessmentMedia, media_id)
    if not media:
        raise HTTPException(404, "Mídia não encontrada.")
    assessment_for(db, media.assessment_id, user)
    path = LocalStorageProvider().verified_path(
        media.storage_key, media.sha256, media.size
    )
    if not path.is_file():
        raise HTTPException(404, "Arquivo indisponível no armazenamento.")
    return FileResponse(
        path, media_type=media.mime, headers={"Content-Disposition": "inline"}
    )


@app.post("/assessments/{assessment_id}/analyze", status_code=201)
def process(
    assessment_id: str,
    body: s.AnalyzeInput,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    analyze(db, assessment_id, body, user)
    return assessment_result(db, assessment_for(db, assessment_id, user))


@app.post("/findings/{finding_id}/review")
def review(
    finding_id: str,
    body: s.ReviewInput,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    finding = db.get(m.AttentionFinding, finding_id)
    if not finding:
        raise HTTPException(404, "Registro não encontrado.")
    analysis = db.get(m.Analysis, finding.analysis_id)
    assessment = assessment_for(db, analysis.assessment_id, user, lock=True)
    if assessment.status == "completed":
        raise HTTPException(409, "Avaliação concluída.")
    finding.state = body.state
    db.add(
        m.ProfessionalReview(
            finding_id=finding.id, reviewer_id=user.id, **body.model_dump()
        )
    )
    audit(db, user, "finding.reviewed", finding.id)
    db.commit()
    return row(finding)


@app.get("/assessments/{assessment_id}/report")
def report(
    assessment_id: str,
    compare_to: str | None = None,
    analysis_id: str | None = None,
    user: m.User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    assessment = assessment_for(db, assessment_id, user)
    snapshot = {
        "assessment": assessment_result(db, assessment),
        "patient": row(patient_for(db, assessment.patient_id, user)),
        "professional": db.get(m.User, assessment.created_by).name,
    }
    if snapshot["assessment"].get("assessment_protocol"):
        children = []
        for step in snapshot["assessment"]["assessment_protocol"]["steps"]:
            if step["child_assessment_id"]:
                child = assessment_for(db, step["child_assessment_id"], user)
                child_result = assessment_result(db, child)
                children.append(child_result)
                snapshot["assessment"]["analyses"].extend(child_result["analyses"])
        snapshot["protocol_children"] = children
    if compare_to:
        target = db.get(m.Analysis, analysis_id) if analysis_id else None
        if not target or target.assessment_id != assessment.id:
            raise HTTPException(
                422, "Selecione uma análise desta avaliação para comparar."
            )
        comparison = compare(db, user, compare_to, analysis_id)
        if not comparison["comparable"]:
            raise HTTPException(
                422, "Capturas incompatíveis: " + ", ".join(comparison["reasons"])
            )
        prior = db.get(m.Analysis, compare_to)
        snapshot["comparison"] = {
            **comparison,
            "analysis_a": compare_to,
            "analysis_b": analysis_id,
            "date_a": db.get(m.Assessment, prior.assessment_id).created_at.isoformat(),
            "date_b": assessment.created_at.isoformat(),
        }
    pdf = make_pdf(snapshot, db)
    record = m.Report(
        assessment_id=assessment.id,
        created_by=user.id,
        sha256=hashlib.sha256(pdf).hexdigest(),
        snapshot=snapshot,
    )
    db.add(record)
    db.flush()
    audit(db, user, "report.generated", record.id)
    db.commit()
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="avaliacao-{assessment.id}.pdf"'
        },
    )


@app.get("/settings/rules")
def rules(user: m.User = Depends(current_user)):
    return RULESET


@app.get("/admin/audit")
def audit_log(user: m.User = Depends(admin), db: DBSession = Depends(get_db)):
    return [
        row(x)
        for x in db.scalars(
            select(m.AuditLog)
            .where(m.AuditLog.clinic_id == user.clinic_id)
            .order_by(m.AuditLog.created_at.desc())
            .limit(200)
        )
    ]


@app.get("/admin/users")
def users(user: m.User = Depends(admin), db: DBSession = Depends(get_db)):
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role}
        for u in db.scalars(select(m.User).where(m.User.clinic_id == user.clinic_id))
    ]


@app.post("/admin/users", status_code=201)
def create_user(
    body: s.UserInput, user: m.User = Depends(admin), db: DBSession = Depends(get_db)
):
    if db.scalar(select(m.User).where(m.User.email == body.email.lower())):
        raise HTTPException(409, "Não foi possível cadastrar este e-mail.")
    new = m.User(
        clinic_id=user.clinic_id,
        name=body.name,
        email=body.email.lower(),
        role=body.role,
        password_hash=hasher.hash(body.password),
    )
    db.add(new)
    db.flush()
    db.add(m.Professional(user_id=new.id))
    audit(db, user, "user.created", new.id)
    db.commit()
    return {"id": new.id, "name": new.name, "role": new.role}
