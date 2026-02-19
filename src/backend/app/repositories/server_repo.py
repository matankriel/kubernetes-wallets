"""Repository for bare-metal server inventory.

All DB access for the servers table goes through this class.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.server import Server


class ServerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, server_id: str) -> Server:
        result = await self.session.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if server is None:
            raise NotFoundError(f"Server '{server_id}' not found")
        return server

    async def list_servers(
        self,
        site: str | None = None,
        performance_tier: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Server], int]:
        query = select(Server)
        if site:
            query = query.where(Server.site == site)
        if performance_tier:
            query = query.where(Server.performance_tier == performance_tier)
        if status:
            query = query.where(Server.status == status)

        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        paginated = query.offset((page - 1) * page_size).limit(page_size)
        rows = await self.session.execute(paginated)
        return list(rows.scalars().all()), total

    async def upsert_from_external(self, server_data: list[dict]) -> dict[str, int]:
        """Upsert servers from the external API response.

        Returns counts: {inserted, updated}.
        INSERT ... ON CONFLICT (name) DO UPDATE ensures idempotency.
        """
        if not server_data:
            return {"inserted": 0, "updated": 0}

        now = datetime.now(UTC)
        inserted = 0
        updated = 0

        for data in server_data:
            stmt = (
                insert(Server)
                .values(
                    name=data["name"],
                    vendor=data.get("vendor"),
                    site=data.get("site"),
                    deployment_cluster=data.get("deployment_cluster"),
                    cpu=data.get("cpu"),
                    ram_gb=data.get("ram_gb"),
                    serial_number=data.get("serial_number"),
                    product=data.get("product"),
                    performance_tier=data.get("performance_tier"),
                    status="active",
                    synced_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "vendor": data.get("vendor"),
                        "site": data.get("site"),
                        "deployment_cluster": data.get("deployment_cluster"),
                        "cpu": data.get("cpu"),
                        "ram_gb": data.get("ram_gb"),
                        "serial_number": data.get("serial_number"),
                        "product": data.get("product"),
                        "performance_tier": data.get("performance_tier"),
                        "status": "active",
                        "synced_at": now,
                    },
                )
            )
            result = await self.session.execute(stmt)
            # rowcount: 1 = insert, 2 = update (PostgreSQL convention with ON CONFLICT)
            if result.rowcount == 1:
                inserted += 1
            else:
                updated += 1

        await self.session.commit()
        return {"inserted": inserted, "updated": updated}

    async def mark_offline(self, names_to_keep: list[str]) -> int:
        """Set status=offline for all servers whose name is not in names_to_keep."""
        stmt = (
            update(Server)
            .where(Server.name.not_in(names_to_keep), Server.status == "active")
            .values(status="offline")
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
