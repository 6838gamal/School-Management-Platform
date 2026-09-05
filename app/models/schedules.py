# app/models/schedules.py

"""
Schedule models - الجداول الدراسية والحصص
"""
from sqlalchemy import ForeignKey, Integer, String, Boolean, UniqueConstraint, Text, Time, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func
import enum
from datetime import time, date

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class DayOfWeek(str, enum.Enum):
    """أيام الأسبوع"""
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    
    @property
    def arabic_name(self) -> str:
        """الاسم بالعربية"""
        names = {
            "sunday": "الأحد",
            "monday": "الإثنين",
            "tuesday": "الثلاثاء",
            "wednesday": "الأربعاء",
            "thursday": "الخميس",
            "friday": "الجمعة",
            "saturday": "السبت"
        }
        return names.get(self.value, self.value)
    
    @property
    def number(self) -> int:
        """رقم اليوم (0=الأحد, 6=السبت)"""
        numbers = {
            "sunday": 0,
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6
        }
        return numbers.get(self.value, 0)
    
    @classmethod
    def from_number(cls, number: int) -> "DayOfWeek":
        """إنشاء من رقم اليوم"""
        mapping = {
            0: cls.SUNDAY,
            1: cls.MONDAY,
            2: cls.TUESDAY,
            3: cls.WEDNESDAY,
            4: cls.THURSDAY,
            5: cls.FRIDAY,
            6: cls.SATURDAY
        }
        return mapping.get(number, cls.SUNDAY)


class ScheduleStatus:
    """حالة الجدول - قيم نصية"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class Schedule(UUIDPkMixin, TimestampMixin, Base):
    """
    الجدول الدراسي الرئيسي
    """
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint(
            "school_id", "section_id", "year_id", 
            name="uq_schedule_section_year"
        ),
        UniqueConstraint(
            "school_id", "name", 
            name="uq_schedule_school_name"
        ),
    )

    # ========== الحقول الأساسية ==========
    school_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("schools.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف المدرسة"
    )
    
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        doc="اسم الجدول"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        doc="وصف الجدول"
    )
    
    # ========== الحقول المرتبطة ==========
    section_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("sections.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف الشعبة"
    )
    
    year_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("academic_years.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف العام الدراسي"
    )
    
    # ========== إعدادات الجدول ==========
    status: Mapped[str] = mapped_column(
        String(50), 
        default="draft",
        nullable=False,
        doc="حالة الجدول"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        doc="هل الجدول مفعل؟"
    )
    
    is_default: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        doc="هل هذا الجدول هو الافتراضي للشعبة؟"
    )
    
    # ========== إعدادات الوقت ==========
    start_date: Mapped[date | None] = mapped_column(
        Date, 
        nullable=True,
        doc="تاريخ بدء تطبيق الجدول"
    )
    
    end_date: Mapped[date | None] = mapped_column(
        Date, 
        nullable=True,
        doc="تاريخ انتهاء تطبيق الجدول"
    )
    
    # ========== العلاقات ==========
    entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry", 
        back_populates="schedule", 
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="الحصص في الجدول"
    )
    
    # ========== Properties للتوافق ==========
    @property
    def academic_year_id(self) -> str:
        """Alias للتوافق مع الكود القديم"""
        return self.year_id
    
    @academic_year_id.setter
    def academic_year_id(self, value: str) -> None:
        self.year_id = value
    
    @property
    def entry_count(self) -> int:
        """عدد الحصص في الجدول"""
        return len(self.entries) if self.entries else 0
    
    @property
    def total_periods(self) -> int:
        """إجمالي عدد الحصص في الأسبوع"""
        if not self.entries:
            return 0
        days = set(e.day_of_week for e in self.entries)
        periods_per_day = {}
        for day in days:
            periods_per_day[day] = len([e for e in self.entries if e.day_of_week == day])
        return sum(periods_per_day.values())
    
    @property
    def days_count(self) -> int:
        """عدد الأيام التي فيها حصص"""
        if not self.entries:
            return 0
        return len(set(e.day_of_week for e in self.entries))
    
    def __repr__(self) -> str:
        return f"<Schedule {self.name} (Section: {self.section_id})>"


class ScheduleEntry(UUIDPkMixin, TimestampMixin, Base):
    """
    مدخل في الجدول الدراسي (حصة واحدة)
    """
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "day_of_week", "period_id", 
            name="uq_schedule_day_period"
        ),
        UniqueConstraint(
            "schedule_id", "day_of_week", "subject_id",
            name="uq_schedule_day_subject"
        ),
        UniqueConstraint(
            "schedule_id", "day_of_week", "period_id", "teacher_id",
            name="uq_schedule_day_period_teacher"
        ),
    )

    # ========== الحقول الأساسية ==========
    schedule_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("schedules.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف الجدول"
    )
    
    # ✅ إضافة school_id
    school_id: Mapped[str] = mapped_column(
        String(36), 
        nullable=False, 
        index=True,
        doc="معرف المدرسة"
    )
    
    # ✅ إضافة section_id
    section_id: Mapped[str] = mapped_column(
        String(36), 
        nullable=False, 
        index=True,
        doc="معرف الشعبة"
    )
    
    # ========== التوقيت ==========
    day_of_week: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        doc="رقم اليوم (0=الأحد, 6=السبت)"
    )
    
    period_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("periods.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف الفترة/الحصة"
    )
    
    # ========== المحتوى ==========
    subject_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("subjects.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف المادة"
    )
    
    teacher_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("teachers.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        doc="معرف المعلم"
    )
    
    room_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("rooms.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True,
        doc="معرف الغرفة"
    )
    
    # ========== معلومات إضافية ==========
    notes: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        doc="ملاحظات على الحصة"
    )
    
    # ========== العلاقات ==========
    schedule: Mapped["Schedule"] = relationship(
        "Schedule", 
        back_populates="entries",
        doc="الجدول المرتبط"
    )
    
    # ========== Properties ==========
    @property
    def day_name(self) -> str:
        """اسم اليوم بالعربية"""
        names = {
            0: "الأحد",
            1: "الإثنين",
            2: "الثلاثاء",
            3: "الأربعاء",
            4: "الخميس",
            5: "الجمعة",
            6: "السبت"
        }
        return names.get(self.day_of_week, "غير معروف")
    
    @property
    def day_name_en(self) -> str:
        """اسم اليوم بالإنجليزية"""
        names = {
            0: "Sunday",
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday"
        }
        return names.get(self.day_of_week, "Unknown")
    
    @property
    def is_weekend(self) -> bool:
        """هل اليوم عطلة؟"""
        return self.day_of_week in [5, 6]
    
    @property
    def is_active_day(self) -> bool:
        """هل اليوم نشط (أيام الأحد إلى الخميس)؟"""
        return self.day_of_week in [0, 1, 2, 3, 4]
    
    def __repr__(self) -> str:
        return f"<ScheduleEntry Day:{self.day_of_week} Period:{self.period_id} Subject:{self.subject_id}>"


# ============================================================
# نموذج إضافي: Template للجداول
# ============================================================
class ScheduleTemplate(UUIDPkMixin, TimestampMixin, Base):
    """
    قالب جدول دراسي - يمكن استخدامه لإنشاء جداول متشابهة بسرعة
    """
    __tablename__ = "schedule_templates"
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_template_school_name"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("schools.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        doc="اسم القالب"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        doc="وصف القالب"
    )
    
    days_count: Mapped[int] = mapped_column(
        Integer, 
        default=5,
        doc="عدد الأيام"
    )
    
    periods_per_day: Mapped[int] = mapped_column(
        Integer, 
        default=5,
        doc="عدد الحصص في اليوم"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True
    )
    
    entries: Mapped[list["ScheduleTemplateEntry"]] = relationship(
        "ScheduleTemplateEntry", 
        back_populates="template", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class ScheduleTemplateEntry(UUIDPkMixin, TimestampMixin, Base):
    """
    مدخل في قالب الجدول
    """
    __tablename__ = "schedule_template_entries"
    __table_args__ = (
        UniqueConstraint(
            "template_id", "day_of_week", "period_id", 
            name="uq_template_day_period"
        ),
    )

    template_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("schedule_templates.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    day_of_week: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    
    period_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("periods.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    subject_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("subjects.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    template: Mapped["ScheduleTemplate"] = relationship(
        "ScheduleTemplate", 
        back_populates="entries"
    )


# ============================================================
# تحديث __all__
# ============================================================
__all__ = [
    "Schedule",
    "ScheduleEntry",
    "ScheduleTemplate",
    "ScheduleTemplateEntry",
    "DayOfWeek",
    "ScheduleStatus",
]
