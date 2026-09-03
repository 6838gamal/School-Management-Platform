"""Holiday model - الإجازات والعطل الرسمية"""
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import Column, String, Date, Boolean, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date, datetime, timedelta
import uuid

from app.core.database import Base


class Holiday(Base):
    """نموذج الإجازات والعطل الرسمية"""
    __tablename__ = "holidays"

    # ============ الحقول الأساسية ============
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
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
    
    # ============ التكرار ============
    recurring_year = Column(Integer, nullable=True, comment="السنة التي تتكرر فيها (للإجازات السنوية)")
    recurring_month = Column(Integer, nullable=True, comment="الشهر الذي تتكرر فيه")
    recurring_day = Column(Integer, nullable=True, comment="اليوم الذي تتكرر فيه")
    
    # ============ أيام الأسبوع المعطلة ============
    weekly_off_days = Column(String(20), nullable=True, default="5,6", comment="أيام العطل الأسبوعية (مفصولة بفواصل)")
    # 0=الأحد, 1=الإثنين, 2=الثلاثاء, 3=الأربعاء, 4=الخميس, 5=الجمعة, 6=السبت
    
    # ============ حالة الإجازة ============
    is_active = Column(Boolean, default=True, comment="هل الإجازة نشطة")
    is_deleted = Column(Boolean, default=False, comment="هل تم الحذف")
    
    # ============ الطوابع الزمنية ============
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    created_by = Column(String(36), nullable=True, comment="من أنشأ")
    updated_by = Column(String(36), nullable=True, comment="من عدل")
    
    # ============ ❌ تم إزالة العلاقة لتجنب خطأ التهيئة ============
    # school = relationship("School", back_populates="holidays")  # تم حذف هذا السطر
    
    def __repr__(self):
        return f"<Holiday {self.name} ({self.date})>"
    
    # ============================================================
    # ============ الخصائص المحسوبة (Properties) ============
    # ============================================================
    
    @property
    def is_weekend(self) -> bool:
        """التحقق مما إذا كانت الإجازة هي عطلة نهاية الأسبوع"""
        if self.weekly_off_days:
            day_num = self.date.weekday()  # 0=الأحد, 6=السبت
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
    def type_icon(self) -> str:
        """أيقونة نوع الإجازة"""
        if self.is_official:
            return "🏛️"
        elif self.is_weekly:
            return "📆"
        elif self.is_recurring:
            return "🔄"
        else:
            return "📋"
    
    @property
    def holiday_year(self) -> int:
        """السنة التي تحدث فيها الإجازة"""
        return self.date.year
    
    @property
    def holiday_month(self) -> int:
        """الشهر الذي تحدث فيه الإجازة"""
        return self.date.month
    
    @property
    def holiday_day(self) -> int:
        """اليوم الذي تحدث فيه الإجازة"""
        return self.date.day


# ============================================================
# ============ دوال مساعدة للعمل مع الإجازات ============
# ============================================================

def get_default_weekly_off_days() -> List[int]:
    """
    الحصول على أيام العطل الأسبوعية الافتراضية
    
    Returns:
        List[int]: قائمة بأرقام أيام العطل (الجمعة والسبت)
    """
    return [5, 6]  # الجمعة (5) والسبت (6)


def parse_weekly_off_days(weekly_off_days: Optional[str]) -> List[int]:
    """
    تحويل أيام العطل الأسبوعية من نص إلى قائمة
    
    Args:
        weekly_off_days: نص أيام العطل (مثل "5,6")
    
    Returns:
        List[int]: قائمة أيام العطل
    """
    if not weekly_off_days:
        return get_default_weekly_off_days()
    
    try:
        return [int(d.strip()) for d in weekly_off_days.split(',') if d.strip()]
    except:
        return get_default_weekly_off_days()


def is_weekend(date_obj: date, weekly_off_days: Optional[str] = None) -> bool:
    """
    التحقق مما إذا كان التاريخ هو عطلة نهاية الأسبوع
    
    Args:
        date_obj: التاريخ المراد التحقق منه
        weekly_off_days: أيام العطل الأسبوعية (مثل "5,6")
    
    Returns:
        bool: True إذا كان عطلة نهاية الأسبوع
    """
    off_days = parse_weekly_off_days(weekly_off_days)
    return date_obj.weekday() in off_days


def get_day_name(date_obj: date) -> str:
    """
    الحصول على اسم اليوم
    
    Args:
        date_obj: التاريخ
    
    Returns:
        str: اسم اليوم بالعربية
    """
    days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
    return days[date_obj.weekday()]


def get_holiday_status(date_obj: date) -> str:
    """
    الحصول على حالة الإجازة
    
    Args:
        date_obj: تاريخ الإجازة
    
    Returns:
        str: حالة الإجازة (upcoming, today, past)
    """
    today = date.today()
    if date_obj == today:
        return "today"
    elif date_obj > today:
        return "upcoming"
    else:
        return "past"


def get_holiday_status_label(date_obj: date) -> str:
    """
    الحصول على تسمية حالة الإجازة
    
    Args:
        date_obj: تاريخ الإجازة
    
    Returns:
        str: تسمية الحالة
    """
    status = get_holiday_status(date_obj)
    labels = {
        "today": "📌 اليوم",
        "upcoming": "📅 قادمة",
        "past": "✅ منتهية"
    }
    return labels.get(status, "❓ غير معروف")


def is_date_in_holiday_range(holiday: Holiday, date_obj: date) -> bool:
    """
    التحقق مما إذا كان التاريخ يقع ضمن نطاق الإجازة
    
    Args:
        holiday: الإجازة
        date_obj: التاريخ المراد التحقق منه
    
    Returns:
        bool: True إذا كان التاريخ ضمن نطاق الإجازة
    """
    if holiday.start_date and holiday.end_date:
        return holiday.start_date <= date_obj <= holiday.end_date
    return holiday.date == date_obj


def get_holiday_date_range(holiday: Holiday) -> Tuple[date, date]:
    """
    الحصول على نطاق تاريخ الإجازة
    
    Args:
        holiday: الإجازة
    
    Returns:
        Tuple[date, date]: (تاريخ البداية, تاريخ النهاية)
    """
    if holiday.start_date and holiday.end_date:
        return (holiday.start_date, holiday.end_date)
    return (holiday.date, holiday.date)


def format_holiday_date_range(holiday: Holiday) -> str:
    """
    تنسيق نطاق تاريخ الإجازة للعرض
    
    Args:
        holiday: الإجازة
    
    Returns:
        str: النطاق المنسق
    """
    if holiday.is_multi_day:
        return f"{holiday.start_date.strftime('%d/%m/%Y')} - {holiday.end_date.strftime('%d/%m/%Y')}"
    return holiday.date.strftime('%d/%m/%Y')


# ============================================================
# ============ دوال للاستعلام عن الإجازات (Sync) ============
# ============================================================

def get_holidays_by_school_sync(
    db,
    school_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_active: bool = True
) -> List[Holiday]:
    """
    جلب الإجازات لمدرسة معينة (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        start_date: تاريخ البداية (اختياري)
        end_date: تاريخ النهاية (اختياري)
        is_active: حالة النشاط
    
    Returns:
        List[Holiday]: قائمة الإجازات
    """
    from sqlalchemy import select
    
    query = select(Holiday).where(Holiday.school_id == school_id)
    
    if start_date:
        query = query.where(Holiday.date >= start_date)
    
    if end_date:
        query = query.where(Holiday.date <= end_date)
    
    if is_active is not None:
        query = query.where(Holiday.is_active == is_active)
    
    query = query.order_by(Holiday.date)
    
    result = db.execute(query)
    return result.scalars().all()


def get_holiday_by_date_sync(
    db,
    school_id: str,
    date_obj: date
) -> Optional[Holiday]:
    """
    جلب الإجازة في تاريخ محدد (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        date_obj: التاريخ
    
    Returns:
        Optional[Holiday]: الإجازة إن وجدت
    """
    from sqlalchemy import select
    
    result = db.execute(
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date == date_obj.strftime('%Y-%m-%d'))
        .where(Holiday.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


def get_holidays_by_month_sync(
    db,
    school_id: str,
    year: int,
    month: int,
    is_active: bool = True
) -> List[Holiday]:
    """
    جلب الإجازات في شهر محدد (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        year: السنة
        month: الشهر
        is_active: حالة النشاط
    
    Returns:
        List[Holiday]: قائمة الإجازات في الشهر
    """
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return get_holidays_by_school_sync(db, school_id, start_date, end_date, is_active)


def get_holidays_by_year_sync(
    db,
    school_id: str,
    year: int,
    is_active: bool = True
) -> List[Holiday]:
    """
    جلب الإجازات في سنة محددة (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        year: السنة
        is_active: حالة النشاط
    
    Returns:
        List[Holiday]: قائمة الإجازات في السنة
    """
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    return get_holidays_by_school_sync(db, school_id, start_date, end_date, is_active)


def get_upcoming_holidays_sync(
    db,
    school_id: str,
    limit: int = 10,
    is_active: bool = True
) -> List[Holiday]:
    """
    جلب الإجازات القادمة (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        school_id: معرف المدرسة
        limit: عدد النتائج
        is_active: حالة النشاط
    
    Returns:
        List[Holiday]: قائمة الإجازات القادمة
    """
    from sqlalchemy import select
    
    today = date.today().strftime('%Y-%m-%d')
    
    query = (
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date >= today)
        .where(Holiday.is_active == is_active)
        .order_by(Holiday.date)
        .limit(limit)
    )
    
    result = db.execute(query)
    return result.scalars().all()


def create_holiday_sync(
    db,
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
    إنشاء إجازة جديدة (نسخة متزامنة)
    
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
    db.commit()
    db.refresh(holiday)
    
    return holiday


def update_holiday_sync(
    db,
    holiday_id: str,
    **kwargs
) -> Optional[Holiday]:
    """
    تحديث إجازة (نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
        **kwargs: الحقول المراد تحديثها
    
    Returns:
        Optional[Holiday]: الإجازة المحدثة أو None
    """
    from sqlalchemy import select
    
    result = db.execute(
        select(Holiday).where(Holiday.id == holiday_id)
    )
    holiday = result.scalar_one_or_none()
    
    if not holiday:
        return None
    
    for key, value in kwargs.items():
        if hasattr(holiday, key):
            setattr(holiday, key, value)
    
    holiday.updated_at = datetime.now()
    
    db.commit()
    db.refresh(holiday)
    
    return holiday


def delete_holiday_sync(
    db,
    holiday_id: str,
    updated_by: Optional[str] = None
) -> bool:
    """
    حذف إجازة (حذف منطقي - نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
        updated_by: من حذف
    
    Returns:
        bool: نجاح العملية
    """
    from sqlalchemy import select
    
    result = db.execute(
        select(Holiday).where(Holiday.id == holiday_id)
    )
    holiday = result.scalar_one_or_none()
    
    if not holiday:
        return False
    
    holiday.is_active = False
    holiday.is_deleted = True
    holiday.updated_at = datetime.now()
    holiday.updated_by = updated_by
    
    db.commit()
    return True


def delete_holidays_bulk_sync(
    db,
    holiday_ids: List[str],
    updated_by: Optional[str] = None
) -> int:
    """
    حذف إجازات متعددة (حذف منطقي - نسخة متزامنة)
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_ids: قائمة معرفات الإجازات
        updated_by: من حذف
    
    Returns:
        int: عدد الإجازات المحذوفة
    """
    from sqlalchemy import select
    
    result = db.execute(
        select(Holiday).where(Holiday.id.in_(holiday_ids))
    )
    holidays = result.scalars().all()
    
    count = 0
    for holiday in holidays:
        holiday.is_active = False
        holiday.is_deleted = True
        holiday.updated_at = datetime.now()
        holiday.updated_by = updated_by
        count += 1
    
    db.commit()
    return count
