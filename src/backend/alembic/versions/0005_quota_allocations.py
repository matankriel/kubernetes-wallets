"""Revision 0005: department and team quota allocation tables

Creates department_quota_allocations and team_quota_allocations tables
that track CPU/RAM budget assignments flowing down the org hierarchy.

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "department_quota_allocations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column("cpu_limit", sa.Integer(), nullable=False),
        sa.Column("ram_gb_limit", sa.Integer(), nullable=False),
        sa.Column("cpu_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ram_gb_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_id"],
            ["fields.id"],
            name="fk_dqa_field_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_dqa_department_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_department_quota_allocations"),
        sa.UniqueConstraint("department_id", "site", name="uq_dqa_department_site"),
    )
    op.create_index("ix_dqa_field_id", "department_quota_allocations", ["field_id"])
    op.create_index("ix_dqa_department_id", "department_quota_allocations", ["department_id"])

    op.create_table(
        "team_quota_allocations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column("cpu_limit", sa.Integer(), nullable=False),
        sa.Column("ram_gb_limit", sa.Integer(), nullable=False),
        sa.Column("cpu_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ram_gb_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_tqa_department_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_tqa_team_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_team_quota_allocations"),
        sa.UniqueConstraint("team_id", "site", name="uq_tqa_team_site"),
    )
    op.create_index("ix_tqa_department_id", "team_quota_allocations", ["department_id"])
    op.create_index("ix_tqa_team_id", "team_quota_allocations", ["team_id"])


def downgrade():
    op.drop_index("ix_tqa_team_id", table_name="team_quota_allocations")
    op.drop_index("ix_tqa_department_id", table_name="team_quota_allocations")
    op.drop_table("team_quota_allocations")
    op.drop_index("ix_dqa_department_id", table_name="department_quota_allocations")
    op.drop_index("ix_dqa_field_id", table_name="department_quota_allocations")
    op.drop_table("department_quota_allocations")
