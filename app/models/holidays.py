"""Holiday model - الإجازات والعطل الرسمية"""
from sqlalchemy import Column, String, Date, Boolean, Text, DateTime, ForeignKey, Integer, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import uuid

from app.core.database import Base
from app.models.base import BaseModel


class Holiday(Base, BaseModel):
    """نموذج الإجازات والعطل الرسمية"""
    __tablename__ = "holidays"

    # ============================================================
    # ============ الحقول الخاصة بالنموذج ============
    # ============================================================
    
    # الحقول الموروثة من BaseModel:
    # id, created_at, updated_at, is_active, is_deleted, created_by, updated_by
    
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ============ معلومات الإجازة ============
    name = Column(String(200), nullable=False, comment="اسم الإجازة")
    date = Column(Date, nullable=False, index=True, comment="تاريخ الإجازة")
    
    # ============ نوع الإجازة ============
    is_official = Column(Boolean, default=False, comment="إجازة رسمية (وطنية/دينية)")
    is_weekly = Column(Boolean, default=False, comment="إجازة أسبوعية (جمعة/سبت)")
    is_recurring = Column(Boolean, default=False, comment="إجازة متكررة سنوياً")
    
    # ============ تفاصيل إضافية ============
    reason = Column(Text, nullable=True, comment="سبب الإجازة")
    start_date = Column(Date, nullable=True, comment="بداية الإجازة (للإجازات الممتدة)")
    end_date = Column(Date, nullable=True, comment="نهاية الإجازة (للإجازات الممتدة)")
    
    # ============ التكرار السنوي ============
    recurring_year = Column(Integer, nullable=True, comment="السنة التي تتكرر فيها")
    recurring_month = Column(Integer, nullable=True, comment="الشهر الذي تتكرر فيه")
    recurring_day = Column(Integer, nullable=True, comment="اليوم الذي تتكرر فيه")
    
    # ============ أيام العطل الأسبوعية ============
    weekly_off_days = Column(String(20), nullable=True, default="5,6", comment="أيام العطل الأسبوعية (0-6 مفصولة بفواصل)")
    # 0=الأحد, 1=الإثنين, 2=الثلاثاء, 3=الأربعاء, 4=الخميس, 5=الجمعة, 6=السبت
    
    # ============================================================
    # ============ العلاقات ============
    # ============================================================
    
    school = relationship("School", back_populates="holidays")
    
    # ============================================================
    # ============ الخصائص (Properties) ============
    # ============================================================
    
    @property
    def is_weekend(self) -> bool:
        """التحقق مما إذا كانت الإجازة هي عطلة نهاية الأسبوع"""
        if self.weekly_off_days:
            day_num = self.date.weekday()
            off_days = [int(d.strip()) for d in self.weekly_off_days.split(',') if d.strip()]
            return day_num in off_days
        return False
    
    @property
    def display_date(self) -> str:
        """عرض التاريخ بشكل منسق"""
        return self.date.strftime('%Y-%m-%d')
    
    @property
    def day_name(self) -> str:
        """اسم اليوم"""
        days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
        return days[self.date.weekday()]
    
    @property
    def is_future(self) -> bool:
        """هل الإجازة في المستقبل"""
        return self.date > date.today()
    
    @property
    def is_past(self) -> bool:
        """هل الإجازة في الماضي"""
        return self.date < date.today()
    
    @property
    def is_today(self) -> bool:
        """هل الإجازة اليوم"""
        return self.date == date.today()
    
    @property
    def is_multi_day(self) -> bool:
        """هل الإجازة تمتد لأكثر من يوم"""
        return self.start_date is not None and self.end_date is not None and self.start_date != self.end_date
    
    @property
    def duration_days(self) -> int:
        """عدد أيام الإجازة"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 1
    
    @property
    def status_label(self) -> str:
        """تسمية حالة الإجازة"""
        if self.is_today:
            return "📌 اليوم"
        elif self.is_future:
            return "📅 قادمة"
        else:
            return "✅ منتهية"
    
    @property
    def type_label(self) -> str:
        """تسمية نوع الإجازة"""
        if self.is_official:
            return "🏛️ رسمية"
        elif self.is_weekly:
            return "📆 أسبوعية"
        elif self.is_recurring:
            return "🔄 متكررة"
        else:
            return "📋 عادية"
    
    @property
    def icon(self) -> str:
        """أيقونة حسب نوع الإجازة"""
        if self.is_official:
            return "🏛️"
        elif self.is_weekly:
            return "📆"
        elif self.is_weekend:
            return "🏖️"
        else:
            return "📋"
    
    @property
    def type_color(self) -> str:
        """لون حسب نوع الإجازة"""
        if self.is_official:
            return "amber"
        elif self.is_weekly:
            return "blue"
        elif self.is_weekend:
            return "green"
        else:
            return "slate"
    
    @property
    def type_bg(self) -> str:
        """خلفية حسب نوع الإجازة"""
        if self.is_official:
            return "bg-amber-100"
        elif self.is_weekly:
            return "bg-blue-100"
        elif self.is_weekend:
            return "bg-green-100"
        else:
            return "bg-slate-100"
    
    @property
    def type_text(self) -> str:
        """نص حسب نوع الإجازة"""
        if self.is_official:
            return "text-amber-700"
        elif self.is_weekly:
            return "text-blue-700"
        elif self.is_weekend:
            return "text-green-700"
        else:
            return "text-slate-700"
    
    # ============================================================
    # ============ الدوال ============
    # ============================================================
    
    def __repr__(self) -> str:
        return f"<Holiday {self.name} ({self.date})>"
    
    def __str__(self) -> str:
        return f"{self.name} - {self.display_date}"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الإجازة إلى قاموس مع جميع الخصائص"""
        return {
            "id": self.id,
            "school_id": self.school_id,
            "name": self.name,
            "date": self.display_date,
            "day_name": self.day_name,
            "is_official": self.is_official,
            "is_weekly": self.is_weekly,
            "is_recurring": self.is_recurring,
            "is_weekend": self.is_weekend,
            "reason": self.reason,
            "start_date": self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            "end_date": self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            "duration_days": self.duration_days,
            "is_multi_day": self.is_multi_day,
            "status": self.status_label,
            "type": self.type_label,
            "icon": self.icon,
            "type_color": self.type_color,
            "type_bg": self.type_bg,
            "type_text": self.type_text,
            "is_active": self.is_active,
            "created_at": self.created_at_formatted if hasattr(self, 'created_at_formatted') else str(self.created_at),
            "updated_at": self.updated_at_formatted if hasattr(self, 'updated_at_formatted') else str(self.updated_at),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """ملخص الإجازة"""
        return {
            "id": self.id,
            "name": self.name,
            "date": self.display_date,
            "day_name": self.day_name,
            "status": self.status_label,
            "type": self.type_label,
            "icon": self.icon,
        }


# ============================================================
# ============ دوال مساعدة ============
# ============================================================

def get_weekly_off_days(school_id: Optional[str] = None) -> List[int]:
    """
    الحصول على أيام العطل الأسبوعية
    
    Args:
        school_id: معرف المدرسة (اختياري)
    
    Returns:
        List[int]: قائمة بأرقام أيام العطل (0=الأحد, 6=السبت)
    """
    # القيمة الافتراضية: الجمعة (5) والسبت (6)
    default_days = [5, 6]
    
    # TODO: جلب الإعدادات من قاعدة البيانات حسب المدرسة
    # if school_id:
    #     return await get_school_weekly_off_days(school_id) or default_days
    
    return default_days


def is_weekend(date_obj: date, school_id: Optional[str] = None) -> bool:
    """
    التحقق مما إذا كان التاريخ هو عطلة نهاية الأسبوع
    
    Args:
        date_obj: التاريخ المراد التحقق منه
        school_id: معرف المدرسة (اختياري)
    
    Returns:
        bool: True إذا كان عطلة نهاية الأسبوع
    """
    off_days = get_weekly_off_days(school_id)
    return date_obj.weekday() in off_days


def get_holiday_status(holiday_date: date) -> str:
    """
    الحصول على حالة الإجازة
    
    Args:
        holiday_date: تاريخ الإجازة
    
    Returns:
        str: 'today', 'upcoming', 'past'
    """
    today = date.today()
    if holiday_date == today:
        return "today"
    elif holiday_date > today:
        return "upcoming"
    else:
        return "past"


def get_holiday_status_label(holiday_date: date) -> str:
    """
    الحصول على تسمية حالة الإجازة
    
    Args:
        holiday_date: تاريخ الإجازة
    
    Returns:
        str: التسمية المناسبة
    """
    status = get_holiday_status(holiday_date)
    labels = {
        "today": "📌 اليوم",
        "upcoming": "📅 قادمة",
        "past": "✅ منتهية"
    }
    return labels.get(status, "❓ غير معروف")


def get_holiday_type_icon(holiday: Holiday) -> str:
    """
    الحصول على أيقونة نوع الإجازة
    
    Args:
        holiday: كائن الإجازة
    
    Returns:
        str: الأيقونة المناسبة
    """
    return holiday.icon


def get_holiday_type_label(holiday: Holiday) -> str:
    """
    الحصول على تسمية نوع الإجازة
    
    Args:
        holiday: كائن الإجازة
    
    Returns:
        str: التسمية المناسبة
    """
    return holiday.type_label


def get_holiday_type_color(holiday: Holiday) -> str:
    """
    الحصول على لون نوع الإجازة
    
    Args:
        holiday: كائن الإجازة
    
    Returns:
        str: اللون المناسب
    """
    return holiday.type_color


async def get_holidays_between(
    db: AsyncSession,
    school_id: str,
    start_date: date,
    end_date: date
) -> List[Holiday]:
    """
    جلب الإجازات بين تاريخين
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
    
    Returns:
        List[Holiday]: قائمة الإجازات
    """
    result = await db.execute(
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date >= start_date.strftime('%Y-%m-%d'))
        .where(Holiday.date <= end_date.strftime('%Y-%m-%d'))
        .where(Holiday.is_active == True)
        .order_by(Holiday.date)
    )
    return result.scalars().all()


async def get_holidays_by_month(
    db: AsyncSession,
    school_id: str,
    year: int,
    month: int
) -> List[Holiday]:
    """
    جلب الإجازات في شهر محدد
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        year: السنة
        month: الشهر
    
    Returns:
        List[Holiday]: قائمة الإجازات في الشهر
    """
    from datetime import date, timedelta
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return await get_holidays_between(db, school_id, start_date, end_date)


async def get_holidays_by_year(
    db: AsyncSession,
    school_id: str,
    year: int
) -> List[Holiday]:
    """
    جلب الإجازات في سنة محددة
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        year: السنة
    
    Returns:
        List[Holiday]: قائمة الإجازات في السنة
    """
    from datetime import date
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    return await get_holidays_between(db, school_id, start_date, end_date)


async def get_upcoming_holidays(
    db: AsyncSession,
    school_id: str,
    limit: int = 10
) -> List[Holiday]:
    """
    جلب الإجازات القادمة
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        limit: عدد النتائج
    
    Returns:
        List[Holiday]: قائمة الإجازات القادمة
    """
    today = date.today().strftime('%Y-%m-%d')
    
    result = await db.execute(
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date >= today)
        .where(Holiday.is_active == True)
        .order_by(Holiday.date)
        .limit(limit)
    )
    return result.scalars().all()


async def get_holiday_by_date(
    db: AsyncSession,
    school_id: str,
    date_obj: date
) -> Optional[Holiday]:
    """
    جلب الإجازة في تاريخ محدد
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        date_obj: التاريخ
    
    Returns:
        Optional[Holiday]: الإجازة إن وجدت
    """
    result = await db.execute(
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date == date_obj.strftime('%Y-%m-%d'))
        .where(Holiday.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_holiday_by_id(
    db: AsyncSession,
    holiday_id: str
) -> Optional[Holiday]:
    """
    جلب الإجازة حسب المعرف
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
    
    Returns:
        Optional[Holiday]: الإجازة إن وجدت
    """
    result = await db.execute(
        select(Holiday)
        .where(Holiday.id == holiday_id)
        .where(Holiday.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_holiday(
    db: AsyncSession,
    school_id: str,
    name: str,
    date_obj: date,
    is_official: bool = False,
    is_weekly: bool = False,
    is_recurring: bool = False,
    reason: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    recurring_month: Optional[int] = None,
    recurring_day: Optional[int] = None,
    weekly_off_days: Optional[str] = None,
    created_by: Optional[str] = None
) -> Holiday:
    """
    إنشاء إجازة جديدة
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        name: اسم الإجازة
        date_obj: التاريخ
        is_official: إجازة رسمية
        is_weekly: إجازة أسبوعية
        is_recurring: إجازة متكررة
        reason: سبب الإجازة
        start_date: بداية الإجازة الممتدة
        end_date: نهاية الإجازة الممتدة
        recurring_month: شهر التكرار
        recurring_day: يوم التكرار
        weekly_off_days: أيام العطل الأسبوعية
        created_by: من أنشأ
    
    Returns:
        Holiday: الإجازة المنشأة
    """
    holiday = Holiday(
        school_id=school_id,
        name=name,
        date=date_obj,
        is_official=is_official,
        is_weekly=is_weekly,
        is_recurring=is_recurring,
        reason=reason,
        start_date=start_date,
        end_date=end_date,
        recurring_month=recurring_month,
        recurring_day=recurring_day,
        weekly_off_days=weekly_off_days or "5,6",
        is_active=True,
        created_by=created_by
    )
    
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    
    return holiday


async def update_holiday(
    db: AsyncSession,
    holiday_id: str,
    **kwargs
) -> Optional[Holiday]:
    """
    تحديث إجازة
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
        **kwargs: الحقول المراد تحديثها
    
    Returns:
        Optional[Holiday]: الإجازة المحدثة
    """
    holiday = await get_holiday_by_id(db, holiday_id)
    
    if not holiday:
        return None
    
    # تحديث الحقول
    for key, value in kwargs.items():
        if hasattr(holiday, key) and key not in ['id', 'created_at', 'created_by']:
            setattr(holiday, key, value)
    
    holiday.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(holiday)
    
    return holiday


async def delete_holiday(
    db: AsyncSession,
    holiday_id: str,
    deleted_by: Optional[str] = None
) -> bool:
    """
    حذف إجازة (حذف منطقي)
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
        deleted_by: من قام بالحذف
    
    Returns:
        bool: نجاح العملية
    """
    holiday = await get_holiday_by_id(db, holiday_id)
    
    if not holiday:
        return False
    
    holiday.is_active = False
    holiday.is_deleted = True
    holiday.updated_at = datetime.now()
    if deleted_by:
        holiday.updated_by = deleted_by
    
    await db.commit()
    return True


async def restore_holiday(
    db: AsyncSession,
    holiday_id: str
) -> bool:
    """
    استعادة إجازة محذوفة
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
    
    Returns:
        bool: نجاح العملية
    """
    result = await db.execute(
        select(Holiday)
        .where(Holiday.id == holiday_id)
        .where(Holiday.is_deleted == True)
        .limit(1)
    )
    holiday = result.scalar_one_or_none()
    
    if not holiday:
        return False
    
    holiday.is_active = True
    holiday.is_deleted = False
    holiday.updated_at = datetime.now()
    
    await db.commit()
    return True


async def get_holidays_stats(
    db: AsyncSession,
    school_id: str,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    جلب إحصائيات الإجازات
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        year: السنة (اختياري)
    
    Returns:
        Dict[str, Any]: الإحصائيات
    """
    if year is None:
        year = date.today().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    holidays = await get_holidays_between(db, school_id, start_date, end_date)
    
    stats = {
        "total": len(holidays),
        "official": len([h for h in holidays if h.is_official]),
        "weekly": len([h for h in holidays if h.is_weekly]),
        "recurring": len([h for h in holidays if h.is_recurring]),
        "upcoming": len([h for h in holidays if h.is_future]),
        "past": len([h for h in holidays if h.is_past]),
        "today": len([h for h in holidays if h.is_today]),
        "by_month": {},
        "by_type": {
            "official": 0,
            "weekly": 0,
            "recurring": 0,
            "normal": 0
        }
    }
    
    for holiday in holidays:
        month = holiday.date.month
        stats["by_month"][month] = stats["by_month"].get(month, 0) + 1
        
        if holiday.is_official:
            stats["by_type"]["official"] += 1
        elif holiday.is_weekly:
            stats["by_type"]["weekly"] += 1
        elif holiday.is_recurring:
            stats["by_type"]["recurring"] += 1
        else:
            stats["by_type"]["normal"] += 1
    
    return stats
