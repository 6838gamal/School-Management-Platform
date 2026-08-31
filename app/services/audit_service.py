"""Audit log service — append-only."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    """خدمة سجل التدقيق — يمكن كتابة السجلات فقط (لا تعديل ولا حذف منطقي)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        school_id: str,
        actor_id: str | None,
        actor_role: str | None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            extra=extra,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_recent(self, school_id: str, limit: int = 100) -> list[AuditLog]:
        """جلب أحدث سجلات المدرسة (للمدراء)."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.school_id == school_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
