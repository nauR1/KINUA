"""Explicit demo tenancy and recoverable media deletion."""

import sqlalchemy as sa
from alembic import op

revision = "8d402b230000"
down_revision = "7c301a230000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "clinics",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "demo_media_cleanup",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "clinic_id", sa.String(36), sa.ForeignKey("clinics.id"), nullable=False
        ),
        sa.Column("storage_key", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_demo_media_cleanup_clinic_id", "demo_media_cleanup", ["clinic_id"]
    )


def downgrade():
    op.drop_table("demo_media_cleanup")
    op.drop_column("clinics", "is_demo")
