import io
import os
from pathlib import Path

from pypdf import PdfReader
from test_api import assessment, patient
from test_protocols_rom import catalog, pose  # noqa: F401
from test_video import enqueue

from app import jobs
from app.report_brand import label, report_filename


def pdf_text(response):
    return "\n".join(
        page.extract_text() or ""
        for page in PdfReader(io.BytesIO(response.content)).pages
    )


def test_report_presentation_helpers():
    assert label("lateral_right") == "Lateral direita"
    assert label("lateral_left") == "Lateral esquerda"
    assert label("review") == "Pendente de revisão profissional"
    assert label("needs_review") == "Pendente de revisão profissional"
    assert (
        report_filename("Ruan Rocha da Paixão", "2026-09-15T10:00:00")
        == "KINUA_Ruan_Rocha_da_Paixao_2026-09-15.pdf"
    )


def test_basic_pdf_has_human_filename_and_no_assessment_uuid(auth):
    a = assessment(auth)
    response = auth.get(f"/assessments/{a['id']}/report")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="KINUA_Paciente_Teste_{a["created_at"][:10]}.pdf"'
    )
    text = pdf_text(response)
    assert "Paciente Teste" in text
    assert "Professional 1" in text
    assert "Relatório de avaliação" in text
    assert a["id"] not in text
    assert "sha256=" not in text
    assert "stack trace" not in text.lower()


def test_rom_pdf_uses_human_labels_and_preserves_limitations(
    auth, db, video, monkeypatch, catalog
):
    monkeypatch.setattr(jobs, "SessionLocal", db)
    p = patient(auth)
    created = auth.post(
        "/rom/assessments",
        json={"patient_id": p["id"], "movement": "knee_flexion", "side": "right"},
    )
    assert created.status_code == 201, created.text
    assessment_id = created.json()["assessment_id"]
    media = auth.post(
        f"/assessments/{assessment_id}/videos",
        files={"file": ("fixture.webm", video.read_bytes(), "video/webm")},
        data={"view": "lateral_right"},
    )
    assert media.status_code == 201, media.text
    job = enqueue(auth, {"id": assessment_id}, media.json()).json()

    class Provider:
        version = "mediapipe-python/0.10.35;pose_lite/float16/1;sha256=debughash"

        def detect(self, rgb, timestamp):
            return pose("knee_flexion", min(120, timestamp / 10))

        def close(self):
            pass

    assert jobs.claim() == job["id"]
    jobs.process_job(job["id"], Provider)
    result = auth.get(f"/assessments/{assessment_id}").json()
    analysis = result["analyses"][0]
    assert analysis["media"]["view"] == "lateral_right"
    assert analysis["motion"]["signal"] == "right_rom"

    preview_note = (
        "Registro de acompanhamento para validação visual do relatório KINUA. " * 90
    )
    updated = auth.patch(
        f"/assessments/{assessment_id}",
        json={"notes": preview_note},
    )
    assert updated.status_code == 200, updated.text

    response = auth.get(f"/assessments/{assessment_id}/report")
    assert response.status_code == 200
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) >= 3
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    artifact_dir = os.environ.get("KINUA_REPORT_ARTIFACT_DIR")
    if artifact_dir:
        output = Path(artifact_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "KINUA_Paciente_Teste_ROM.pdf").write_bytes(response.content)

    for expected in (
        "Paciente Teste",
        "Professional 1",
        "Lateral direita",
        "Flexão do joelho — direito",
        "Pendente de revisão profissional",
        "Qualidade de captura limitada",
        "Estimativa geométrica 2D",
        "Visibilidade não representa acurácia clínica",
        "câmera não verifica o plano anatômico em 3D",
        "Máximos entre amostras podem ser perdidos",
        "Revisão profissional",
        "Versão técnica: KINUA ROM 1.0.0",
        "Motor de pose: MediaPipe 0.10.35",
    ):
        assert expected in text

    for forbidden in (
        assessment_id,
        "lateral_right",
        "lateral_left",
        "right_rom",
        "left_rom",
        "sha256=",
        "pose_lite/float16/1",
        "storage_key",
        "bucket",
        "Traceback",
    ):
        assert forbidden not in text

    assert "°" in text
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="KINUA_Paciente_Teste_'
    )
