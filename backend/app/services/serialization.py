from datetime import datetime, timezone
from sqlalchemy import inspect, select
from ..models import (
    Analysis,
    AssessmentMedia,
    BiomechanicalMeasurement,
    AttentionFinding,
    PoseFrame,
    PoseLandmark,
    ProfessionalReview,
    ProcessingJob,
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
    return data


def analysis_result(db, analysis):
    result = row(analysis)
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
    for finding in db.scalars(
        select(AttentionFinding)
        .where(AttentionFinding.analysis_id == analysis.id)
        .order_by(AttentionFinding.region, AttentionFinding.side, AttentionFinding.id)
    ):
        value = row(finding)
        value["reviews"] = [
            row(x)
            for x in db.scalars(
                select(ProfessionalReview)
                .where(ProfessionalReview.finding_id == finding.id)
                .order_by(ProfessionalReview.created_at)
            )
        ]
        result["findings"].append(value)
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
    result = row(assessment)
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
