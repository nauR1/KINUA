"""Isolate cancelled/retried worker attempts.
Revision ID: 2a9c071bf630
Revises: 6d49ba3c72e9
"""

import sqlalchemy as sa
from alembic import op

revision = "2a9c071bf630"
down_revision = "6d49ba3c72e9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "processing_jobs", sa.Column("run_token", sa.String(36), nullable=True)
    )


def downgrade():
    op.drop_column("processing_jobs", "run_token")
