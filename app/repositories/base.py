"""Base repository with generic CRUD operations."""
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository providing common query operations."""

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: str) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: Any = None,
    ) -> tuple[list[ModelT], int]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if filters:
            for key, value in filters.items():
                if value is None:
                    continue
                col = getattr(self.model, key, None)
                if col is not None:
                    stmt = stmt.where(col == value)
                    count_stmt = count_stmt.where(col == value)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        total = (await self.db.execute(count_stmt)).scalar() or 0
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, **kwargs: Any) -> ModelT:
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    async def get_by(self, **kwargs: Any) -> ModelT | None:
        stmt = select(self.model)
        for key, value in kwargs.items():
            col = getattr(self.model, key, None)
            if col is not None:
                stmt = stmt.where(col == value)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by(self, **kwargs: Any) -> list[ModelT]:
        stmt = select(self.model)
        for key, value in kwargs.items():
            col = getattr(self.model, key, None)
            if col is not None:
                stmt = stmt.where(col == value)
        return list((await self.db.execute(stmt)).scalars().all())
