"""Student attachments — مرفقات الحالة الصحية والتقارير."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class StudentAttachment(UUIDPkMixin, TimestampMixin, Base):
    """مرفق مرتبط بملف الطالب (تقرير صحي، فحص...)."""
    __tablename__ = "student_attachments"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # health_report | medical_clearance | parent_consent | other
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(1000))
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


__all__ = ["StudentAttachment"]
