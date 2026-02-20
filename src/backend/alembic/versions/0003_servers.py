"""Revision 0003: servers table

Creates the servers table for bare-metal server inventory.
Performance tier is classified as 'regular' or 'high_performance'
based on CPU count vs PERFORMANCE_TIER_CPU_THRESHOLD.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "servers",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("vendor", sa.Text(), nullable=True),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column("deployment_cluster", sa.Text(), nullable=True),
        sa.Column("cpu", sa.Integer(), nullable=False),
        sa.Column("ram_gb", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.Text(), nullable=True),
        sa.Column("product", sa.Text(), nullable=True),
        sa.Column(
            "performance_tier",
            sa.Text(),
            sa.CheckConstraint(
                "performance_tier IN ('regular', 'high_performance')",
                name="ck_servers_performance_tier",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            sa.CheckConstraint(
                "status IN ('active', 'offline')",
                name="ck_servers_status",
            ),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_servers"),
        sa.UniqueConstraint("name", name="uq_servers_name"),
        sa.UniqueConstraint("serial_number", name="uq_servers_serial_number"),
    )
    op.create_index("ix_servers_site", "servers", ["site"])
    op.create_index("ix_servers_performance_tier", "servers", ["performance_tier"])
    op.create_index("ix_servers_status", "servers", ["status"])


def downgrade():
    op.drop_index("ix_servers_status", table_name="servers")
    op.drop_index("ix_servers_performance_tier", table_name="servers")
    op.drop_index("ix_servers_site", table_name="servers")
    op.drop_table("servers")
