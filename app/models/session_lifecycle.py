"""Session lifecycle — كل حصة تمر بحالات صريحة.

Scheduled → Teacher Assigned → Teacher Present/Absent →
Substitute Required → Substitute Accepted →
Class Started → Lesson Prepared → Class Completed

These states drive the 🟢/🟠/🔴 dashboard lights.
"""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


SESSION_STATUSES = (
    "scheduled",            # الجدولة موجودة لكن لم تبدأ
    "teacher_absent",       # 🔴 المعلم غائب (يُطلب بديل)
    "substitute_required",  # في انتظار رد المعلم البديل
    "substitute_accepted",  # تم تكليف بديل
    "teacher_present",      # 🟠 المعلم حاضر، لم يُحضّر الدرس بعد
    "class_started",        # الحصة بدأت، لم يبدأ التحضير
    "lesson_prepared",      # 🟢 المعلم حضر الدرس
    "completed",            # الحصة انتهت
    "cancelled",            # أُلغيت
)

# Transitions allowed by the system. Ill-formed transitions raise ValidationException.
SESSION_TRANSITIONS = {
    "scheduled":           {"teacher_present", "teacher_absent", "cancelled"},
    "teacher_absent":      {"substitute_required", "teacher_present", "cancelled"},
    "substitute_required": {"substitute_accepted", "cancelled"},
    "substitute_accepted": {"class_started", "teacher_absent", "cancelled"},
    "teacher_present":     {"class_started", "completed"},
    "class_started":       {"lesson_prepared", "completed"},
    "lesson_prepared":     {"completed"},
    "completed":           set(),
    "cancelled":           set(),
}


class SessionLifecycle(UUIDPkMixin, TimestampMixin, Base):
    """حالة حصة معينة في يوم معين."""
    __tablename__ = "session_lifecycle"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    schedule_entry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("schedule_entries.id", ondelete="CASCADE"),
        index=True,
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    teacher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    substitute_teacher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    notes: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    __all__ = ["SessionLifecycle", "SESSION_STATUSES", "SESSION_TRANSITIONS"]
