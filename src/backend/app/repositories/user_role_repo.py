"""Repository for the user_roles table (DB-based role overrides)."""

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import UserRole


class UserRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> UserRole | None:
        result = await self.session.execute(
            select(UserRole).where(UserRole.username == username)
        )
        return result.scalar_one_or_none()

    async def upsert_user_role(
        self, username: str, role: str, scope_id: str | None, assigned_by: str
    ) -> UserRole:
        stmt = (
            pg_insert(UserRole)
            .values(username=username, role=role, scope_id=scope_id, assigned_by=assigned_by)
            .on_conflict_do_update(
                index_elements=["username"],
                set_={
                    "role": role,
                    "scope_id": scope_id,
                    "assigned_by": assigned_by,
                    "assigned_at": sa.text("now()"),
                },
            )
            .returning(UserRole)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        await self.session.flush()
        return row

    async def delete(self, row: UserRole) -> None:
        await self.session.delete(row)
        await self.session.flush()

    async def list_all(self) -> list[UserRole]:
        result = await self.session.execute(select(UserRole).order_by(UserRole.username))
        return list(result.scalars().all())
