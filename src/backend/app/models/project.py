"""SQLAlchemy ORM model for projects (Kubernetes namespaces)."""

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.server import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    site: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_tier: Mapped[str | None] = mapped_column(Text, nullable=True)
    namespace_name: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    status: Mapped[str] = mapped_column(
        Text, server_default=text("'provisioning'"), nullable=False
    )
    quota_cpu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_ram_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updated_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    team: Mapped["Team"] = relationship("Team")  # noqa: F821
