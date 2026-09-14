"""Add commercial access controls without expiring existing accounts."""

import sqlalchemy as sa
from alembic import op

revision = "7c301a230000"
down_revision = "2a9c071bf630"
branch_labels = None
depends_on = None
COMMON = [
    "is_active",
    "access_expires_at",
    "suspended_at",
    "suspension_reason",
    "created_at",
    "updated_at",
]
CLINIC = [
    "plan_code",
    "subscription_status",
    "access_starts_at",
    "max_users",
    "provider",
    "external_subscription_id",
    "external_customer_id",
    "period_start",
    "period_end",
]


def upgrade():
    for table in ["clinics", "users"]:
        # SQLite needs table recreation for CURRENT_TIMESTAMP on populated tables.
        with op.batch_alter_table(
            table,
            recreate="always" if op.get_bind().dialect.name == "sqlite" else "auto",
        ) as batch:
            batch.add_column(
                sa.Column(
                    "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
                )
            )
            for name in ["access_expires_at", "suspended_at"]:
                batch.add_column(sa.Column(name, sa.DateTime(timezone=True)))
            batch.add_column(sa.Column("suspension_reason", sa.Text()))
            for name in ["created_at", "updated_at"]:
                batch.add_column(
                    sa.Column(
                        name,
                        sa.DateTime(timezone=True),
                        nullable=False,
                        server_default=sa.func.now(),
                    )
                )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True)))
    for name, default in [("plan_code", "custom"), ("subscription_status", "active")]:
        op.add_column(
            "clinics",
            sa.Column(name, sa.String(20), nullable=False, server_default=default),
        )
    for name in ["access_starts_at", "period_start", "period_end"]:
        op.add_column("clinics", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column("clinics", sa.Column("max_users", sa.Integer()))
    for name, size in [
        ("provider", 40),
        ("external_subscription_id", 200),
        ("external_customer_id", 200),
    ]:
        op.add_column("clinics", sa.Column(name, sa.String(size)))
    op.add_column("audit_logs", sa.Column("changes", sa.JSON()))


def downgrade():
    op.drop_column("audit_logs", "changes")
    for name in reversed(CLINIC):
        op.drop_column("clinics", name)
    op.drop_column("users", "last_login_at")
    for table in ["users", "clinics"]:
        for name in reversed(COMMON):
            op.drop_column(table, name)
