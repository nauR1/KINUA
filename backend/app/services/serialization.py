import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import inspect, select

from ..models import (
    Analysis,
    AssessmentMedia,
    AttentionFinding,
    BiomechanicalMeasurement,
    PoseFrame,
    PoseLandmark,
    ProcessingJob,
    ProfessionalReview,
)


def row(item):
    data = {}
    for column in inspect(item).mapper.column_attrs:
        value = getattr(item, column.key)
        if isinstance(value, datetime):
            value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            data[column.key] = value.isoformat()
        else:
            data[column.key] = value
    if item.__tablename__ == "patients":
        content = {k: data[k] for k in ("name", "birth_date", "details")}
        data["revision"] = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
    return data


def analysis_result(db, analysis):
    from ..models import ROMMeasurement

    result = row(analysis)
    result["rom_measurements"] = [
        row(r)
        for r in db.scalars(
            select(ROMMeasurement).where(ROMMeasurement.analysis_id == analysis.id)
        )
    ]
    result["media"] = row(db.get(AssessmentMedia, analysis.media_id))
    result["media"].pop("storage_key", None)
    result["measurements"] = [
        row(x)
        for x in db.scalars(
            select(BiomechanicalMeasurement)
            .where(BiomechanicalMeasurement.analysis_id == analysis.id)
            .order_by(BiomechanicalMeasurement.key)
        )
    ]
    result["findings"] = []
    findings = db.scalars(
        select(AttentionFinding)
        .where(AttentionFinding.analysis_id == analysis.id)
        .order_by(AttentionFinding.region, AttentionFinding.side, AttentionFinding.id)
    ).all()
    reviews = {f.id: [] for f in findings}
    if reviews:
        for review in db.scalars(
            select(ProfessionalReview)
            .where(ProfessionalReview.finding_id.in_(reviews))
            .order_by(ProfessionalReview.created_at)
        ):
            reviews[review.finding_id].append(row(review))
    result["findings"] = [{**row(f), "reviews": reviews[f.id]} for f in findings]
    frames = db.scalars(
        select(PoseFrame)
        .where(PoseFrame.analysis_id == analysis.id)
        .order_by(PoseFrame.frame_index)
    ).all()
    by_frame = {f.id: [] for f in frames}
    if frames:
        for landmark in db.scalars(
            select(PoseLandmark).where(PoseLandmark.frame_id.in_(by_frame))
        ):
            by_frame[landmark.frame_id].append(
                {
                    key: getattr(landmark, key)
                    for key in ("name", "x", "y", "z", "visibility")
                }
            )
    result["frames"] = [
        {
            **row(f),
            "landmarks": by_frame[f.id],
        }
        for f in frames
    ]
    return result


def assessment_result(db, assessment):
    from ..api_protocols import get_run, protocol_result
    from ..models import AssessmentProtocol, AssessmentStepResult, ROMSession

    result = row(assessment)
    session = db.get(ROMSession, assessment.id)
    result["rom_session"] = row(session) if session else None
    run = get_run(db, assessment.id)
    result["assessment_protocol"] = protocol_result(db, run) if run else None
    parent = db.scalar(
        select(AssessmentProtocol.assessment_id)
        .join(
            AssessmentStepResult,
            AssessmentStepResult.assessment_protocol_id == AssessmentProtocol.id,
        )
        .where(AssessmentStepResult.child_assessment_id == assessment.id)
    )
    result["protocol_parent_id"] = parent
    result["jobs"] = [
        row(j)
        for j in db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.assessment_id == assessment.id)
            .order_by(ProcessingJob.created_at)
        )
    ]
    result["analyses"] = [
        analysis_result(db, a)
        for a in db.scalars(
            select(Analysis)
            .where(Analysis.assessment_id == assessment.id)
            .order_by(Analysis.created_at)
        )
    ]
    return result
