"""Holiday model - الإجازات الرسمية والعطل"""
from sqlalchemy import Column, String, Date, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date, datetime
from typing import Optional

from app.core.database import Base
from app.models.base import BaseModel


class Holiday(Base, BaseModel):
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
    
    # ============ العلاقات ============
    school = relationship("School", back_populates="holidays")
    
    def __repr__(self):
        return f"<Holiday {self.name} ({self.date})>"
    
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


# ============================================================
# ============ دوال مساعدة للإجازات ============
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
    
    # يمكن جلب الإعدادات من قاعدة البيانات حسب المدرسة
    # return await get_school_weekly_off_days(school_id) or default_days
    
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


def is_holiday(date_obj: date, school_id: str, db: AsyncSession) -> bool:
    """
    التحقق مما إذا كان التاريخ هو إجازة رسمية
    
    Args:
        date_obj: التاريخ المراد التحقق منه
        school_id: معرف المدرسة
        db: جلسة قاعدة البيانات
    
    Returns:
        bool: True إذا كان إجازة
    """
    from sqlalchemy import select
    
    result = db.execute(
        select(Holiday)
        .where(Holiday.school_id == school_id)
        .where(Holiday.date == date_obj.strftime('%Y-%m-%d'))
        .where(Holiday.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


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


async def delete_holiday(
    db: AsyncSession,
    holiday_id: str
) -> bool:
    """
    حذف إجازة (حذف منطقي)
    
    Args:
        db: جلسة قاعدة البيانات
        holiday_id: معرف الإجازة
    
    Returns:
        bool: نجاح العملية
    """
    result = await db.execute(
        select(Holiday).where(Holiday.id == holiday_id)
    )
    holiday = result.scalar_one_or_none()
    
    if not holiday:
        return False
    
    holiday.is_active = False
    holiday.is_deleted = True
    
    await db.commit()
    return True
