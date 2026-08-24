"""Notification models: notifications and per-recipient delivery records."""
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models._mixins import TimestampMixin, UUIDPkMixin


class Notification(UUIDPkMixin, TimestampMixin):
    __tablename__ = "notifications"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(30), default="info")  # info/warning/success/error
    audience: Mapped[str] = mapped_column(String(20), default="user")  # user/role/school/teachers
    audience_role: Mapped[str | None] = mapped_column(String(50))
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    recipients: Mapped[list["NotificationRecipient"]] = relationship(
        "NotificationRecipient", back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationRecipient(UUIDPkMixin, TimestampMixin):
    __tablename__ = "notification_recipients"

    notification_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[str | None] = mapped_column(String(20))

    notification: Mapped["Notification"] = relationship("Notification", back_populates="recipients")
