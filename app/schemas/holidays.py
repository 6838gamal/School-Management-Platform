"""Holiday schemas - الإجازات والعطل الرسمية"""
from typing import Optional, List, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


# ============================================================
# ============ Enums ============
# ============================================================

class HolidayType(str, Enum):
    """نوع الإجازة"""
    OFFICIAL = "official"  # رسمية (وطنية/دينية)
    WEEKLY = "weekly"      # أسبوعية (جمعة/سبت)
    RECURRING = "recurring" # متكررة سنوياً
    NORMAL = "normal"      # عادية


class HolidayStatus(str, Enum):
    """حالة الإجازة"""
    UPCOMING = "upcoming"   # قادمة
    TODAY = "today"         # اليوم
    PAST = "past"           # منتهية


class WeeklyOffDay(int, Enum):
    """أيام العطل الأسبوعية"""
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


# ============================================================
# ============ Base Schemas ============
# ============================================================

class HolidayBase(BaseModel):
    """القاعدة الأساسية للإجازة"""
    name: str = Field(..., min_length=2, max_length=200, description="اسم الإجازة")
    date: date = Field(..., description="تاريخ الإجازة")
    
    is_official: bool = Field(False, description="إجازة رسمية (وطنية/دينية)")
    is_weekly: bool = Field(False, description="إجازة أسبوعية")
    is_recurring: bool = Field(False, description="إجازة متكررة سنوياً")
    
    reason: Optional[str] = Field(None, max_length=500, description="سبب الإجازة")
    
    start_date: Optional[date] = Field(None, description="بداية الإجازة الممتدة")
    end_date: Optional[date] = Field(None, description="نهاية الإجازة الممتدة")
    
    recurring_month: Optional[int] = Field(None, ge=1, le=12, description="شهر التكرار")
    recurring_day: Optional[int] = Field(None, ge=1, le=31, description="يوم التكرار")
    
    weekly_off_days: Optional[str] = Field("5,6", max_length=20, description="أيام العطل الأسبوعية (مفصولة بفواصل)")
    
    is_active: bool = Field(True, description="هل الإجازة نشطة")

    @validator('weekly_off_days')
    def validate_weekly_off_days(cls, v):
        """التحقق من صحة أيام العطل الأسبوعية"""
        if not v:
            return "5,6"
        
        days = [d.strip() for d in v.split(',') if d.strip()]
        for day in days:
            try:
                day_num = int(day)
                if day_num < 0 or day_num > 6:
                    raise ValueError(f"يوم العطل غير صحيح: {day}. يجب أن يكون بين 0 و 6")
            except ValueError:
                raise ValueError(f"قيمة غير صحيحة: {day}. يجب أن تكون أرقام مفصولة بفواصل")
        
        return v

    @root_validator
    def validate_dates(cls, values):
        """التحقق من صحة التواريخ"""
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValueError("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        
        return values


class HolidayCreate(HolidayBase):
    """إنشاء إجازة جديدة"""
    created_by: Optional[str] = Field(None, description="من أنشأ")


class HolidayUpdate(BaseModel):
    """تحديث إجازة"""
    name: Optional[str] = Field(None, min_length=2, max_length=200, description="اسم الإجازة")
    date: Optional[date] = Field(None, description="تاريخ الإجازة")
    
    is_official: Optional[bool] = Field(None, description="إجازة رسمية")
    is_weekly: Optional[bool] = Field(None, description="إجازة أسبوعية")
    is_recurring: Optional[bool] = Field(None, description="إجازة متكررة")
    
    reason: Optional[str] = Field(None, max_length=500, description="سبب الإجازة")
    
    start_date: Optional[date] = Field(None, description="بداية الإجازة الممتدة")
    end_date: Optional[date] = Field(None, description="نهاية الإجازة الممتدة")
    
    recurring_month: Optional[int] = Field(None, ge=1, le=12, description="شهر التكرار")
    recurring_day: Optional[int] = Field(None, ge=1, le=31, description="يوم التكرار")
    
    weekly_off_days: Optional[str] = Field(None, max_length=20, description="أيام العطل الأسبوعية")
    
    is_active: Optional[bool] = Field(None, description="هل الإجازة نشطة")
    updated_by: Optional[str] = Field(None, description="من عدل")

    @validator('weekly_off_days')
    def validate_weekly_off_days(cls, v):
        if not v:
            return v
        days = [d.strip() for d in v.split(',') if d.strip()]
        for day in days:
            try:
                day_num = int(day)
                if day_num < 0 or day_num > 6:
                    raise ValueError(f"يوم العطل غير صحيح: {day}")
            except ValueError:
                raise ValueError(f"قيمة غير صحيحة: {day}")
        return v


# ============================================================
# ============ Response Schemas ============
# ============================================================

class HolidayResponse(HolidayBase):
    """استجابة الإجازة الكاملة"""
    id: str
    school_id: str
    
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    
    is_deleted: bool = False
    
    class Config:
        from_attributes = True


class HolidaySummary(BaseModel):
    """ملخص الإجازة (مختصر)"""
    id: str
    name: str
    date: date
    is_official: bool
    is_weekly: bool
    day_name: str
    status: HolidayStatus
    status_label: str
    
    class Config:
        from_attributes = True


class HolidayDetail(HolidayResponse):
    """تفاصيل الإجازة مع معلومات إضافية"""
    day_name: str
    display_date: str
    is_today: bool
    is_future: bool
    is_past: bool
    is_weekend: bool
    is_multi_day: bool
    duration_days: int
    status_label: str
    type_label: str
    
    class Config:
        from_attributes = True


# ============================================================
# ============ Request Schemas ============
# ============================================================

class HolidayFilterParams(BaseModel):
    """معاملات فلترة الإجازات"""
    school_id: Optional[str] = Field(None, description="معرف المدرسة")
    year: Optional[int] = Field(None, description="السنة")
    month: Optional[int] = Field(None, ge=1, le=12, description="الشهر")
    start_date: Optional[date] = Field(None, description="تاريخ البداية")
    end_date: Optional[date] = Field(None, description="تاريخ النهاية")
    
    is_official: Optional[bool] = Field(None, description="إجازة رسمية")
    is_weekly: Optional[bool] = Field(None, description="إجازة أسبوعية")
    is_recurring: Optional[bool] = Field(None, description="إجازة متكررة")
    
    is_active: Optional[bool] = Field(True, description="نشطة")
    
    search: Optional[str] = Field(None, description="بحث في الاسم")
    
    limit: int = Field(100, ge=1, le=500, description="عدد النتائج")
    offset: int = Field(0, ge=0, description="الإزاحة")


class HolidayBulkCreate(BaseModel):
    """إنشاء إجازات متعددة"""
    holidays: List[HolidayCreate]
    
    @validator('holidays')
    def validate_holidays(cls, v):
        if not v:
            raise ValueError("يجب إضافة على الأقل إجازة واحدة")
        if len(v) > 100:
            raise ValueError("لا يمكن إضافة أكثر من 100 إجازة في المرة الواحدة")
        return v


class HolidayBulkDelete(BaseModel):
    """حذف إجازات متعددة"""
    ids: List[str] = Field(..., description="قائمة المعرفات")
    
    @validator('ids')
    def validate_ids(cls, v):
        if not v:
            raise ValueError("يجب تحديد على الأقل معرف واحد")
        if len(v) > 100:
            raise ValueError("لا يمكن حذف أكثر من 100 إجازة في المرة الواحدة")
        return v


class HolidayCheckResponse(BaseModel):
    """التحقق من حالة التاريخ"""
    date: date
    day_name: str
    is_weekend: bool
    is_holiday: bool
    holiday: Optional[HolidaySummary] = None
    is_school_day: bool
    is_working_day: bool


# ============================================================
# ============ Statistics Schemas ============
# ============================================================

class HolidayStats(BaseModel):
    """إحصائيات الإجازات"""
    total: int = Field(0, description="الإجمالي")
    official: int = Field(0, description="الرسمية")
    weekly: int = Field(0, description="الأسبوعية")
    recurring: int = Field(0, description="المتكررة")
    upcoming: int = Field(0, description="القادمة")
    past: int = Field(0, description="المنتهية")
    
    by_month: Dict[int, int] = Field(default_factory=dict, description="حسب الشهر")
    by_year: Dict[int, int] = Field(default_factory=dict, description="حسب السنة")


class HolidayCalendarDay(BaseModel):
    """يوم في تقويم الإجازات"""
    date: date
    day_name: str
    is_weekend: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    holiday_id: Optional[str] = None
    is_today: bool = False
    is_past: bool = False
    is_future: bool = False


class HolidayCalendarResponse(BaseModel):
    """استجابة تقويم الإجازات"""
    year: int
    month: int
    days: List[HolidayCalendarDay]
    stats: HolidayStats


# ============================================================
# ============ Import/Export Schemas ============
# ============================================================

class HolidayImportRow(BaseModel):
    """صف واحد في استيراد الإجازات"""
    name: str = Field(..., description="اسم الإجازة")
    date: str = Field(..., description="التاريخ (YYYY-MM-DD)")
    is_official: bool = Field(False, description="رسمية")
    is_weekly: bool = Field(False, description="أسبوعية")
    reason: Optional[str] = Field(None, description="السبب")
    
    @validator('date')
    def validate_date(cls, v):
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"التاريخ غير صحيح: {v}. يجب أن يكون بصيغة YYYY-MM-DD")


class HolidayImportResult(BaseModel):
    """نتيجة استيراد الإجازات"""
    total: int = Field(0, description="الإجمالي")
    success: int = Field(0, description="الناجح")
    failed: int = Field(0, description="الفاشل")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="الأخطاء")


class HolidayExportData(BaseModel):
    """بيانات تصدير الإجازات"""
    school_id: str
    school_name: str
    export_date: datetime
    holidays: List[HolidayDetail]
    stats: HolidayStats


# ============================================================
# ============ Web/UI Schemas ============
# ============================================================

class HolidayUIItem(BaseModel):
    """عنصر واجهة المستخدم للإجازة"""
    id: str
    name: str
    date: date
    display_date: str
    day_name: str
    is_weekend: bool
    is_official: bool
    is_weekly: bool
    status_label: str
    type_icon: str = "📋"
    type_color: str = "slate"
    type_bg: str = "bg-slate-100"
    type_text: str = "text-slate-700"
    
    @root_validator
    def set_type_style(cls, values):
        """تحديد النمط حسب نوع الإجازة"""
        if values.get('is_official'):
            values['type_icon'] = "🏛️"
            values['type_color'] = "amber"
            values['type_bg'] = "bg-amber-100"
            values['type_text'] = "text-amber-700"
        elif values.get('is_weekly'):
            values['type_icon'] = "📆"
            values['type_color'] = "blue"
            values['type_bg'] = "bg-blue-100"
            values['type_text'] = "text-blue-700"
        elif values.get('is_weekend'):
            values['type_icon'] = "🏖️"
            values['type_color'] = "green"
            values['type_bg'] = "bg-green-100"
            values['type_text'] = "text-green-700"
        else:
            values['type_icon'] = "📋"
            values['type_color'] = "slate"
            values['type_bg'] = "bg-slate-100"
            values['type_text'] = "text-slate-700"
        
        return values


class HolidayWeekView(BaseModel):
    """عرض الإجازات على مستوى الأسبوع"""
    week_start: date
    week_end: date
    days: List[HolidayUIItem]


# ============================================================
# ============ Helper Functions ============
# ============================================================

def get_weekly_off_days_list(weekly_off_days: Optional[str] = None) -> List[int]:
    """
    تحويل أيام العطل الأسبوعية من نص إلى قائمة
    
    Args:
        weekly_off_days: نص أيام العطل (مثل "5,6")
    
    Returns:
        List[int]: قائمة أيام العطل
    """
    if not weekly_off_days:
        return [5, 6]  # الجمعة والسبت افتراضياً
    
    try:
        return [int(d.strip()) for d in weekly_off_days.split(',') if d.strip()]
    except:
        return [5, 6]


def get_weekend_label(day_num: int) -> str:
    """الحصول على تسمية يوم العطلة"""
    weekend_labels = {
        0: "الأحد",
        1: "الإثنين",
        2: "الثلاثاء",
        3: "الأربعاء",
        4: "الخميس",
        5: "الجمعة",
        6: "السبت"
    }
    return weekend_labels.get(day_num, "")


def get_holiday_status(holiday_date: date) -> str:
    """الحصول على حالة الإجازة"""
    today = date.today()
    if holiday_date == today:
        return "today"
    elif holiday_date > today:
        return "upcoming"
    else:
        return "past"


def get_holiday_status_label(holiday_date: date) -> str:
    """الحصول على تسمية حالة الإجازة"""
    status = get_holiday_status(holiday_date)
    labels = {
        "today": "📌 اليوم",
        "upcoming": "📅 قادمة",
        "past": "✅ منتهية"
    }
    return labels.get(status, "❓ غير معروف")


def get_holiday_type_icon(holiday: Any) -> str:
    """الحصول على أيقونة نوع الإجازة"""
    if holiday.is_official:
        return "🏛️"
    elif holiday.is_weekly:
        return "📆"
    elif holiday.is_weekend:
        return "🏖️"
    else:
        return "📋"


def get_holiday_type_label(holiday: Any) -> str:
    """الحصول على تسمية نوع الإجازة"""
    if holiday.is_official:
        return "رسمية"
    elif holiday.is_weekly:
        return "أسبوعية"
    elif holiday.is_recurring:
        return "متكررة"
    else:
        return "عادية"


# ============================================================
# ============ Example Usage ============
# ============================================================

if __name__ == "__main__":
    # مثال إنشاء إجازة
    holiday_data = {
        "name": "اليوم الوطني",
        "date": date(2026, 9, 23),
        "is_official": True,
        "reason": "اليوم الوطني السعودي",
        "weekly_off_days": "5,6"
    }
    
    # التحقق من صحة البيانات
    try:
        holiday = HolidayCreate(**holiday_data)
        print(f"✅ تم إنشاء الإجازة: {holiday.name}")
    except Exception as e:
        print(f"❌ خطأ: {e}")
    
    # مثال التحقق من تاريخ
    check_data = {
        "date": date(2026, 9, 23),
        "is_weekend": False,
        "is_holiday": True,
        "is_school_day": False,
        "is_working_day": False
    }
    check = HolidayCheckResponse(**check_data)
    print(f"📅 التاريخ: {check.date} - {'عطلة' if check.is_holiday else 'دوام'}")
