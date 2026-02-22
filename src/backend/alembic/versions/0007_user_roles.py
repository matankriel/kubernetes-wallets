"""Revision 0007: user_roles table for DB-based role overrides.

Adds the user_roles table which lets platform_admin grant/revoke roles
without LDAP group changes. center_admin is intentionally excluded from
the CHECK constraint — it is LDAP-only; platform_admin is its DB-assignable
superset.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=True),
        sa.Column("assigned_by", sa.Text(), nullable=False),
        sa.Column(
            "assigned_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "role IN ('platform_admin', 'field_admin', 'dept_admin', 'team_lead')",
            name="ck_user_roles_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_user_roles_username"),
    )
    op.create_index("ix_user_roles_username", "user_roles", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_roles_username", table_name="user_roles")
    op.drop_table("user_roles")
