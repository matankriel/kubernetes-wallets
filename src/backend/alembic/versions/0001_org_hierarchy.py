"""Revision 0001: pgcrypto extension + centers table

Enables the pgcrypto PostgreSQL extension (required for gen_random_uuid())
and creates the centers table (org root, Level 1 of the hierarchy).

Revision ID: 0001
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgcrypto for UUID generation via gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "centers",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_centers"),
        sa.UniqueConstraint("name", name="uq_centers_name"),
    )


def downgrade():
    op.drop_table("centers")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
