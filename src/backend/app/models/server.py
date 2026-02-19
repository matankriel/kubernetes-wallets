"""SQLAlchemy ORM model for the servers table."""

from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    site: Mapped[str | None] = mapped_column(Text, nullable=True)
    deployment_cluster: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    product: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_tier: Mapped[str | None] = mapped_column(
        Text,
        CheckConstraint("performance_tier IN ('regular', 'high_performance')", name="ck_servers_perf_tier"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('active', 'offline')", name="ck_servers_status"),
        server_default=text("'active'"),
        nullable=False,
    )
    synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
