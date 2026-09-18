"""Add scale-oriented query indexes.

Revision ID: a91809260001
Revises: 9e1609260000
"""

from alembic import op

revision = "a91809260001"
down_revision = "9e1609260000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_processing_jobs_state_created_at",
        "processing_jobs",
        ["state", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_assessments_patient_clinic_created_at",
        "assessments",
        ["patient_id", "clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_assessments_clinic_created_at",
        "assessments",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_patients_clinic_created_at",
        "patients",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_clinic_created_at",
        "audit_logs",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_expires_at",
        "sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_audit_logs_clinic_created_at", table_name="audit_logs")
    op.drop_index("ix_patients_clinic_created_at", table_name="patients")
    op.drop_index("ix_assessments_clinic_created_at", table_name="assessments")
    op.drop_index(
        "ix_assessments_patient_clinic_created_at", table_name="assessments"
    )
    op.drop_index("ix_processing_jobs_state_created_at", table_name="processing_jobs")
