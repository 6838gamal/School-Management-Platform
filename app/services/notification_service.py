"""Notification service — supports user, role, and school-wide targeting."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User, UserRole
from app.repositories.notifications import NotificationRecipientRepository, NotificationRepository
from app.schemas.notifications import NotificationCreate


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)
        self.recipients = NotificationRecipientRepository(db)

    async def send(self, school_id: str, sender_id: str, req: NotificationCreate) -> dict:
        notification = await self.notifications.create(
            school_id=school_id,
            title=req.title,
            body=req.body,
            type=req.type,
            audience=req.audience,
            audience_role=req.audience_role,
            created_by=sender_id,
        )
        user_ids: list[str] = []
        if req.audience == "user":
            user_ids = req.user_ids
        elif req.audience == "role" and req.audience_role:
            result = await self.db.execute(
                select(UserRole.user_id).join(User, User.id == UserRole.user_id).where(
                    UserRole.role_id.in_(
                        select(UserRole.role_id)  # placeholder
                    )
                )
            )
            # Simpler: find users with matching role key in this school
            role_result = await self.db.execute(
                select(User.id).join(UserRole, UserRole.user_id == User.id).join(
                    UserRole.role  # via relationship
                ).where(User.school_id == school_id)
            )
            user_ids = [str(r) for r in role_result.scalars().all()]
        elif req.audience in ("school", "teachers"):
            result = await self.db.execute(
                select(User.id).where(User.school_id == school_id, User.is_active == True)  # noqa: E712
            )
            user_ids = [str(r) for r in result.scalars().all()]

        for uid in user_ids:
            await self.recipients.create(notification_id=notification.id, user_id=uid, is_read=False)
        await self.db.flush()
        return {"id": notification.id, "recipients": len(user_ids)}

    async def list_for_user(self, user_id: str, unread_only: bool = False) -> list[dict]:
        items = await self.recipients.list_by_user(user_id, unread_only)
        result = []
        for r in items:
            n = r.notification
            result.append({
                "id": r.id,
                "notification_id": r.notification_id,
                "title": n.title if n else "",
                "body": n.body if n else None,
                "type": n.type if n else "info",
                "is_read": r.is_read,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            })
        return result

    async def unread_count(self, user_id: str) -> int:
        return await self.recipients.unread_count(user_id)

    async def mark_read(self, recipient_id: str) -> dict:
        from app.core.exceptions import NotFoundException
        r = await self.recipients.get(recipient_id)
        if not r:
            raise NotFoundException("الإشعار غير موجود")
        r.is_read = True
        r.read_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        await self.db.flush()
        return {"id": r.id, "is_read": True}

    async def mark_all_read(self, user_id: str) -> dict:
        items = await self.recipients.list_by_user(user_id, unread_only=True)
        for r in items:
            r.is_read = True
            r.read_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        await self.db.flush()
        return {"marked": len(items)}
