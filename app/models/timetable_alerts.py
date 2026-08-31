"""Timetable alert settings — مرتبطة بالـ Timetable لا بإشعارات عشوائية."""
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class TimetableAlertSetting(UUIDPkMixin, TimestampMixin, Base):
    """إعدادات التنبيهات لكل مدرسة ومرتبطة بالأوقات الرسمية."""
    __tablename__ = "timetable_alert_settings"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    # قبل بداية الطابور (بالدقائق)
    assembly_lead_minutes: Mapped[int] = mapped_column(Integer, default=10)
    # قبل بداية الحصة (بالدقائق)
    period_start_lead_minutes: Mapped[int] = mapped_column(Integer, default=5)
    # قبل نهاية الحصة (بالدقائق)
    period_end_lead_minutes: Mapped[int] = mapped_column(Integer, default=5)
    # تنبيه التحضير — يحفّز المعلم لحضور الحصة
    preparation_lead_minutes: Mapped[int] = mapped_column(Integer, default=3)
    # التأخر المسموح قبل اعتبار المعلم متأخراً
    late_threshold_minutes: Mapped[int] = mapped_column(Integer, default=10)
    # تنبيه عند التأخر عن التحضير
    alert_on_late_preparation: Mapped[bool] = mapped_column(default=True)


__all__ = ["TimetableAlertSetting"]
