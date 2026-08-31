"""Session lifecycle service — every class session is a state machine.

State machine (frozen in the model module):
  scheduled → teacher_present | teacher_absent | cancelled
  teacher_absent → substitute_required | teacher_present | cancelled
  substitute_required → substitute_accepted | cancelled
  substitute_accepted → class_started | teacher_absent | cancelled
  teacher_present → class_started | completed
  class_started → lesson_prepared | completed
  lesson_prepared → completed
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException, ForbiddenException
from app.models.schedules import ScheduleEntry
from app.models.session_lifecycle import (
    SESSION_STATUSES,
    SESSION_TRANSITIONS,
    SessionLifecycle,
)
from app.services.audit_service import AuditService


# Translation to dashboard indicator colors.
# 🟢 = lesson_prepared/completed (taught) | 🟠 = present but not prepared | 🔴 = absent
INDICATOR_COLORS = {
    "scheduled":            ("⚪", "لم تبدأ بعد"),
    "teacher_absent":       ("🔴", "المعلم غائب"),
    "substitute_required":  ("🔴", "في انتظار رد البديل"),
    "substitute_accepted":  ("🟠", "بديل مقبول — لم يبدأ"),
    "teacher_present":      ("🟠", "المعلم حاضر — لم يحضّر الدرس"),
    "class_started":        ("🟠", "الحصة بدأت — لم يبدأ التحضير"),
    "lesson_prepared":      ("🟢", "المعلم حاضر ومحضّر الدرس"),
    "completed":            ("🟢", "الحصة مكتملة"),
    "cancelled":            ("⚫", "أُلغيت"),
}


def assert_can_transition(user_permissions: set[str], primary_role: str) -> None:
    if "session_lifecycle.transition" not in user_permissions:
        raise ForbiddenException("لا تملك صلاحية تغيير حالة الحصص")


class SessionLifecycleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def get_or_create_for_entry(
        self, *, school_id: str, entry: ScheduleEntry, date: str
    ) -> SessionLifecycle:
        row = (
            await self.db.execute(
                select(SessionLifecycle).where(
                    SessionLifecycle.schedule_entry_id == entry.id,
                    SessionLifecycle.date == date,
                )
            )
        ).scalar_one_or_none()
        if row:
            return row
        row = SessionLifecycle(
            school_id=school_id,
            schedule_entry_id=entry.id,
            date=date,
            status="scheduled",
            teacher_id=entry.teacher_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def transition(
        self,
        *,
        school_id: str,
        actor_id: str,
        actor_role: str,
        user_permissions: set[str],
        schedule_entry_id: str,
        date: str,
        to_status: str,
        notes: str | None = None,
        substitute_teacher_id: str | None = None,
    ) -> SessionLifecycle:
        assert_can_transition(user_permissions, actor_role)
        if to_status not in SESSION_STATUSES:
            raise ValidationException(f"حالة غير معروفة: {to_status}")

        row = (
            await self.db.execute(
                select(SessionLifecycle).where(
                    SessionLifecycle.schedule_entry_id == schedule_entry_id,
                    SessionLifecycle.date == date,
                )
            )
        ).scalar_one_or_none()
        if not row:
            # create from scratch
            entry = (
                await self.db.execute(
                    select(ScheduleEntry).where(ScheduleEntry.id == schedule_entry_id)
                )
            ).scalar_one_or_none()
            if not entry:
                raise ValidationException("المدخل غير موجود")
            row = SessionLifecycle(
                school_id=school_id,
                schedule_entry_id=schedule_entry_id,
                date=date,
                status="scheduled",
                teacher_id=entry.teacher_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(row)
            await self.db.flush()

        allowed = SESSION_TRANSITIONS.get(row.status, set())
        if to_status not in allowed:
            raise ValidationException(
                f"لا يمكن الانتقال من '{row.status}' إلى '{to_status}'"
            )

        from_status = row.status
        row.status = to_status
        row.notes = notes
        if substitute_teacher_id:
            row.substitute_teacher_id = substitute_teacher_id
        row.recorded_by = actor_id
        row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit.log(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="session.transition",
            entity_type="session_lifecycle",
            entity_id=row.id,
            details=f"انتقال الحصة: {from_status} → {to_status}",
            extra={
                "schedule_entry_id": schedule_entry_id,
                "date": date,
                "from": from_status,
                "to": to_status,
            },
        )
        return row

    @staticmethod
    def color_for(status: str) -> tuple[str, str]:
        return INDICATOR_COLORS.get(status, ("⚪", status))
