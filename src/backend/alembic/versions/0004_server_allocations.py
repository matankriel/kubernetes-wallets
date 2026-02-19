"""Revision 0004: field_server_allocations table

Creates the field_server_allocations join table that tracks which
bare-metal servers are assigned to which fields. A server can only
be allocated to one field at a time (UNIQUE on server_id).

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-19
"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "field_server_allocations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column(
            "allocated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("allocated_by", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name="fk_fsa_server_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["field_id"],
            ["fields.id"],
            name="fk_fsa_field_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_field_server_allocations"),
        # A server can only be assigned to one field at a time
        sa.UniqueConstraint("server_id", name="uq_fsa_server_id"),
    )
    op.create_index("ix_fsa_field_id", "field_server_allocations", ["field_id"])
    op.create_index("ix_fsa_server_id", "field_server_allocations", ["server_id"])


def downgrade():
    op.drop_index("ix_fsa_server_id", table_name="field_server_allocations")
    op.drop_index("ix_fsa_field_id", table_name="field_server_allocations")
    op.drop_table("field_server_allocations")
