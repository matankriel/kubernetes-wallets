"""Revision 0002: fields, departments, and teams tables

Creates:
- fields: Level 2 of the org hierarchy (site-specific, children of center)
- departments: Level 3 (children of field)
- teams: Level 4 (children of department, mapped to LDAP groups)

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fields",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("center_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("site", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["center_id"],
            ["centers.id"],
            name="fk_fields_center_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fields"),
        sa.UniqueConstraint("center_id", "name", name="uq_fields_center_name"),
    )
    op.create_index("ix_fields_center_id", "fields", ["center_id"])

    op.create_table(
        "departments",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_id"],
            ["fields.id"],
            name="fk_departments_field_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("field_id", "name", name="uq_departments_field_name"),
    )
    op.create_index("ix_departments_field_id", "departments", ["field_id"])

    op.create_table(
        "teams",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("ldap_group_cn", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_teams_department_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_teams"),
        sa.UniqueConstraint("ldap_group_cn", name="uq_teams_ldap_group_cn"),
        sa.UniqueConstraint("department_id", "name", name="uq_teams_department_name"),
    )
    op.create_index("ix_teams_department_id", "teams", ["department_id"])


def downgrade():
    op.drop_index("ix_teams_department_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_departments_field_id", table_name="departments")
    op.drop_table("departments")
    op.drop_index("ix_fields_center_id", table_name="fields")
    op.drop_table("fields")
