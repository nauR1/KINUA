"""Add optional per-user access start override."""

import sqlalchemy as sa
from alembic import op

revision = "9e1609260000"
down_revision = "8d402b230000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("access_starts_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("users", "access_starts_at")
