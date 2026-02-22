"""SQLAlchemy ORM models for the org hierarchy: Center, Field, Department, Team, UserRole."""

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.server import Base


class Center(Base):
    __tablename__ = "centers"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    fields: Mapped[list["Field"]] = relationship("Field", back_populates="center")


class Field(Base):
    __tablename__ = "fields"
    __table_args__ = (UniqueConstraint("center_id", "name", name="uq_fields_center_name"),)

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    center_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("centers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str] = mapped_column(Text, nullable=False)

    center: Mapped[Center] = relationship("Center", back_populates="fields")
    departments: Mapped[list["Department"]] = relationship("Department", back_populates="field")
    server_allocations: Mapped[list["FieldServerAllocation"]] = relationship(
        "FieldServerAllocation", back_populates="field"
    )
    dept_quotas: Mapped[list["DepartmentQuotaAllocation"]] = relationship(
        "DepartmentQuotaAllocation", back_populates="field"
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("field_id", "name", name="uq_departments_field_name"),)

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    field_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("fields.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)

    field: Mapped[Field] = relationship("Field", back_populates="departments")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="department")
    dept_quotas: Mapped[list["DepartmentQuotaAllocation"]] = relationship(
        "DepartmentQuotaAllocation", back_populates="department"
    )
    team_quotas: Mapped[list["TeamQuotaAllocation"]] = relationship(
        "TeamQuotaAllocation", back_populates="department"
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("department_id", "name", name="uq_teams_department_name"),)

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    department_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ldap_group_cn: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)

    department: Mapped[Department] = relationship("Department", back_populates="teams")
    team_quotas: Mapped[list["TeamQuotaAllocation"]] = relationship(
        "TeamQuotaAllocation", back_populates="team"
    )


class FieldServerAllocation(Base):
    __tablename__ = "field_server_allocations"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    server_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("servers.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    field_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("fields.id", ondelete="RESTRICT"), nullable=False
    )
    allocated_by: Mapped[str | None] = mapped_column(Text, nullable=True)

    field: Mapped[Field] = relationship("Field", back_populates="server_allocations")


class DepartmentQuotaAllocation(Base):
    __tablename__ = "department_quota_allocations"
    __table_args__ = (UniqueConstraint("department_id", "site", name="uq_dqa_department_site"),)

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    field_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("fields.id", ondelete="RESTRICT"), nullable=False
    )
    department_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    site: Mapped[str] = mapped_column(Text, nullable=False)
    cpu_limit: Mapped[int] = mapped_column(nullable=False)
    ram_gb_limit: Mapped[int] = mapped_column(nullable=False)
    cpu_used: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)
    ram_gb_used: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)

    field: Mapped[Field] = relationship("Field", back_populates="dept_quotas")
    department: Mapped[Department] = relationship("Department", back_populates="dept_quotas")


class TeamQuotaAllocation(Base):
    __tablename__ = "team_quota_allocations"
    __table_args__ = (UniqueConstraint("team_id", "site", name="uq_tqa_team_site"),)

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    department_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    site: Mapped[str] = mapped_column(Text, nullable=False)
    cpu_limit: Mapped[int] = mapped_column(nullable=False)
    ram_gb_limit: Mapped[int] = mapped_column(nullable=False)
    cpu_used: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)
    ram_gb_used: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)

    department: Mapped[Department] = relationship("Department", back_populates="team_quotas")
    team: Mapped[Team] = relationship("Team", back_populates="team_quotas")


class UserRole(Base):
    """DB-based role override — takes precedence over LDAP group mapping on login.

    center_admin is intentionally absent from the CHECK constraint; it is LDAP-only.
    platform_admin is the DB-assignable superset of center_admin.
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("username", name="uq_user_roles_username"),
        CheckConstraint(
            "role IN ('platform_admin', 'field_admin', 'dept_admin', 'team_lead')",
            name="ck_user_roles_role",
        ),
    )

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_by: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=True
    )
