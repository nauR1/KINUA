"""Compare immutable measurements only when capture and method are compatible."""

from fastapi import HTTPException
from sqlalchemy import select

from .. import models as m
from ..repositories import assessment_for


def compare(db, user, left_id: str, right_id: str):
    analyses = [db.get(m.Analysis, key) for key in (left_id, right_id)]
    if any(a is None for a in analyses):
        raise HTTPException(404, "Análise não encontrada.")
    assessments = [assessment_for(db, a.assessment_id, user) for a in analyses]
    if assessments[0].patient_id != assessments[1].patient_id:
        raise HTTPException(422, "Selecione avaliações do mesmo paciente.")
    if left_id == right_id or assessments[0].id == assessments[1].id:
        raise HTTPException(422, "Selecione duas avaliações distintas.")
    media = [db.get(m.AssessmentMedia, a.media_id) for a in analyses]
    reasons = []
    if analyses[0].motion.get("rom", {}).get("movement") != analyses[1].motion.get(
        "rom", {}
    ).get("movement"):
        reasons.append("movimento ROM")
    for attr, label in [("protocol", "protocolo"), ("side", "lado")]:
        if getattr(assessments[0], attr) != getattr(assessments[1], attr):
            reasons.append(label)
    if media[0].view != media[1].view:
        reasons.append("vista")
    for attr in ("provider_version", "biomechanics_version", "rules_version"):
        if getattr(analyses[0], attr) != getattr(analyses[1], attr):
            reasons.append(attr)
    if analyses[0].motion.get("target_fps") != analyses[1].motion.get("target_fps"):
        reasons.append("FPS de análise")
    if reasons:
        return {"comparable": False, "reasons": reasons, "measurements": []}
    sets = [
        list(
            db.scalars(
                select(m.BiomechanicalMeasurement).where(
                    m.BiomechanicalMeasurement.analysis_id == a.id
                )
            )
        )
        for a in analyses
    ]
    right = {item.key: item for item in sets[1]}
    results = []
    for a in sets[0]:
        b = right.get(a.key)
        if b is None:
            continue
        compatible = (
            a.unit == b.unit
            and a.details.get("method") == b.details.get("method")
            and a.details.get("statistic") == b.details.get("statistic")
        )
        usable = compatible and a.value is not None and b.value is not None
        results.append(
            {
                "key": a.key,
                "label": a.label,
                "unit": a.unit,
                "a": a.value,
                "b": b.value,
                "difference": round(b.value - a.value, 4) if usable else None,
                "statistic": a.details.get("statistic", "instantaneous"),
                "reason": None
                if usable
                else "Medida indisponível ou método incompatível.",
            }
        )
    return {
        "comparable": True,
        "reasons": [],
        "measurements": results,
        "notice": "Diferença B − A, sem percentual de melhora. Perspectiva, roupa, posicionamento e erro de medição podem explicar variações. Compare também os registros e revisões profissionais.",
    }
