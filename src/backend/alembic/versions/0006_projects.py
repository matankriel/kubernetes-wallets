"""Revision 0006: projects table

Creates the projects table that represents Kubernetes namespaces provisioned
for teams. Each project is tied to a team, has a site location, an SLA type,
and tracks provisioning status.

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("site", sa.Text(), nullable=True),
        sa.Column(
            "sla_type",
            sa.Text(),
            sa.CheckConstraint(
                "sla_type IN ('bronze', 'silver', 'gold')",
                name="ck_projects_sla_type",
            ),
            nullable=True,
        ),
        sa.Column(
            "performance_tier",
            sa.Text(),
            sa.CheckConstraint(
                "performance_tier IN ('regular', 'high_performance')",
                name="ck_projects_performance_tier",
            ),
            nullable=True,
        ),
        sa.Column("namespace_name", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            sa.CheckConstraint(
                "status IN ('provisioning', 'active', 'failed', 'deleting')",
                name="ck_projects_status",
            ),
            server_default=sa.text("'provisioning'"),
            nullable=False,
        ),
        sa.Column("quota_cpu", sa.Integer(), nullable=True),
        sa.Column("quota_ram_gb", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_projects_team_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("namespace_name", name="uq_projects_namespace_name"),
        sa.UniqueConstraint("team_id", "name", name="uq_projects_team_name"),
    )
    op.create_index("ix_projects_team_id", "projects", ["team_id"])
    op.create_index("ix_projects_site", "projects", ["site"])


def downgrade():
    op.drop_index("ix_projects_site", table_name="projects")
    op.drop_index("ix_projects_team_id", table_name="projects")
    op.drop_table("projects")
