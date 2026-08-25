"""Behavior models: categories and records for student behavior tracking."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class BehaviorCategory(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "behavior_categories"
    __table_args__ = ()

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # positive / negative
    default_severity: Mapped[int] = mapped_column(Integer, default=1)  # 1-5


class BehaviorRecord(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "behavior_records"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("behavior_categories.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # positive / negative
    severity: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    action_taken: Mapped[str | None] = mapped_column(String(1000))
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "BehaviorCategory",
    "BehaviorRecord"
]
