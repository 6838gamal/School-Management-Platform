"""Notifications and reports repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationRecipient
from app.models.reports import AuditLog, ReportLink
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification


class NotificationRecipientRepository(BaseRepository[NotificationRecipient]):
    model = NotificationRecipient

    async def list_by_user(self, user_id: str, unread_only: bool = False) -> list[NotificationRecipient]:
        stmt = select(NotificationRecipient).where(NotificationRecipient.user_id == user_id)
        if unread_only:
            stmt = stmt.where(NotificationRecipient.is_read == False)  # noqa: E712
        result = await self.db.execute(stmt.order_by(NotificationRecipient.created_at.desc()))
        return list(result.scalars().all())

    async def unread_count(self, user_id: str) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(NotificationRecipient).where(
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.is_read == False,  # noqa: E712
            )
        )
        return result.scalar() or 0


class ReportLinkRepository(BaseRepository[ReportLink]):
    model = ReportLink

    async def get_by_token(self, token: str) -> ReportLink | None:
        result = await self.db.execute(select(ReportLink).where(ReportLink.token == token))
        return result.scalar_one_or_none()


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def log(self, **kwargs) -> AuditLog:
        return await self.create(**kwargs)
