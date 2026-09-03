"""Dashboard and web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_user, template_context
from app.core.exceptions import ForbiddenException
from app.services.academic_service import AcademicService
from app.services.report_service import DashboardService
from app.models.users import User
from app.models.schools import School
from app.models.academics import Section, Grade, Stage, AcademicYear, Subject, Period
from app.models.students import Student
from app.models.teachers import Teacher
from app.models.schedules import Schedule
from app.models.attendance import StudentAttendance, TeacherAttendance

router = APIRouter(prefix="", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# مسار التهيئة (Onboarding)
# ============================================================
@router.get("/onboarding")
async def onboarding_page(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تهيئة المدرسة (للمدير فقط)"""
    if user.primary_role != "director":
        raise ForbiddenException("التهيئة متاحة للمدير فقط")
    
    service = AcademicService(db)
    data = await service.get_onboarding_data(user.school_id)
    
    return templates.TemplateResponse(
        "onboarding/onboarding.html",
        {**ctx, "title": "تهيئة المدرسة", "data": data},
    )


# ============================================================
# المسار الرئيسي للوحة التحكم
# ============================================================
@router.get("/dashboard")
async def dashboard_router(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """التوجيه إلى لوحة التحكم المناسبة حسب دور المستخدم"""
    service = DashboardService(db)
    
    # الحصول على الدور الأساسي للمستخدم
    role = user.primary_role
    
    # التوجيه حسب الدور
    if role == "director":
        stats = await service.director_stats(user.school_id, user.id)
        return templates.TemplateResponse(
            "director/dashboard.html",
            {
                **ctx, 
                "title": "لوحة تحكم المدير",
                "stats": stats,
                "role_name": "مدير",
                "role_icon": "👨‍💼"
            },
        )
    
    elif role == "deputy":
        # جلب البيانات الكاملة للوكيل
        stats = await get_deputy_full_stats(db, user.school_id, user.id)
        
        return templates.TemplateResponse(
            "deputy/dashboard.html",
            {
                **ctx, 
                "title": "لوحة تحكم الوكيل",
                "stats": stats,
                "selected_date": date.today().isoformat(),
                "role_name": "وكيل",
                "role_icon": "👨‍🏫",
                "user": user,
            },
        )
    
    elif role == "activities_manager":
        stats = await service.activities_manager_stats(user.school_id, user.id)
        return templates.TemplateResponse(
            "activities_manager/dashboard.html",
            {
                **ctx, 
                "title": "لوحة تحكم مسؤول الأنشطة",
                "stats": stats,
                "role_name": "مسؤول أنشطة",
                "role_icon": "🎯"
            },
        )
    
    elif role == "teacher":
        from app.repositories.teachers import TeacherRepository
        teacher_repo = TeacherRepository(db)
        teacher = await teacher_repo.get_by_user(user.id)
        teacher_id = teacher.id if teacher else ""
        stats = await service.teacher_stats(user.school_id, teacher_id, user.id)
        return templates.TemplateResponse(
            "teacher/dashboard.html",
            {
                **ctx, 
                "title": "لوحة تحكم المعلم",
                "stats": stats,
                "role_name": "معلم",
                "role_icon": "📚"
            },
        )
    
    # إذا كان الدور غير معروف
    raise ForbiddenException("دور غير معروف")


# ============================================================
# ============ دوال جلب البيانات للوكيل ============
# ============================================================

async def get_deputy_full_stats(
    db: AsyncSession,
    school_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    جلب جميع البيانات المطلوبة للوكيل مع الهيكل الأكاديمي الكامل
    """
    today = date.today()
    
    # ============ 1. البيانات الأساسية ============
    # جلب المدرسة
    school_result = await db.execute(
        select(School).where(School.id == school_id)
    )
    school = school_result.scalar_one_or_none()
    
    # جلب السنة الدراسية النشطة
    year_result = await db.execute(
        select(AcademicYear)
        .where(AcademicYear.school_id == school_id)
        .where(AcademicYear.is_active == True)
    )
    academic_year = year_result.scalar_one_or_none()
    
    # ============ 2. الإحصائيات العامة ============
    # جلب عدد الطلاب
    students_result = await db.execute(
        select(func.count()).select_from(Student)
        .where(Student.school_id == school_id)
        .where(Student.is_active == True)
    )
    total_students = students_result.scalar() or 0
    
    # جلب عدد المعلمين
    teachers_result = await db.execute(
        select(func.count()).select_from(Teacher)
        .where(Teacher.school_id == school_id)
        .where(Teacher.is_active == True)
    )
    total_teachers = teachers_result.scalar() or 0
    
    # جلب عدد الفصول
    sections_result = await db.execute(
        select(func.count()).select_from(Section)
        .where(Section.school_id == school_id)
    )
    total_sections = sections_result.scalar() or 0
    
    # ============ 3. إحصائيات الحضور اليوم ============
    attendance_stats = await get_attendance_stats(db, school_id, today)
    
    # ============ 4. بيانات الأسبوع ============
    weekly_data = await get_weekly_attendance(db, school_id)
    
    # ============ 5. الهيكل الأكاديمي الكامل ============
    academic_structure = await build_academic_structure(
        db, school_id, academic_year.id if academic_year else None
    )
    
    # ============ 6. تجميع النتيجة ============
    return {
        # معلومات عامة
        'academic_year': academic_year.name if academic_year else 'السنة الحالية',
        'current_date': today.strftime('%Y-%m-%d'),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_sections': total_sections,
        
        # إحصائيات الحضور
        'total_present': attendance_stats.get('present', 0),
        'total_absent': attendance_stats.get('absent', 0),
        'total_late': attendance_stats.get('late', 0),
        'total_excused': attendance_stats.get('excused', 0),
        'total_sick': attendance_stats.get('sick', 0),
        'total_late_arrival': attendance_stats.get('late_arrival', 0),
        'attendance_rate': attendance_stats.get('rate', 0),
        
        # بيانات الأسبوع
        'weekly_days': weekly_data,
        
        # الهيكل الأكاديمي
        'academic_structure': academic_structure,
        
        'error': None
    }


async def get_attendance_stats(
    db: AsyncSession,
    school_id: str,
    target_date: date
) -> Dict[str, Any]:
    """جلب إحصائيات الحضور ليوم محدد"""
    from app.models import Attendance
    
    # جلب جميع سجلات الحضور لهذا اليوم
    result = await db.execute(
        select(Attendance)
        .where(Attendance.school_id == school_id)
        .where(Attendance.date == target_date)
    )
    attendances = result.scalars().all()
    
    stats = {
        'present': 0,
        'absent': 0,
        'late': 0,
        'excused': 0,
        'sick': 0,
        'late_arrival': 0,
        'rate': 0
    }
    
    total = 0
    for att in attendances:
        status = att.status
        if status in stats:
            stats[status] += 1
            total += 1
    
    if total > 0:
        stats['rate'] = round((stats['present'] / total) * 100, 1)
    
    return stats


async def get_weekly_attendance(
    db: AsyncSession,
    school_id: str
) -> List[Dict[str, Any]]:
    """جلب بيانات الحضور لآخر 7 أيام"""
    from app.models import Attendance
    
    days = []
    today = date.today()
    
    # أسماء الأيام بالأسبوع
    day_names = {
        0: 'الأحد', 1: 'الإثنين', 2: 'الثلاثاء',
        3: 'الأربعاء', 4: 'الخميس', 5: 'الجمعة', 6: 'السبت'
    }
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        
        # جلب إحصائيات اليوم
        result = await db.execute(
            select(
                func.count().filter(Attendance.status == 'present').label('present'),
                func.count().filter(Attendance.status == 'absent').label('absent'),
                func.count().filter(Attendance.status == 'late').label('late'),
            )
            .select_from(Attendance)
            .where(Attendance.school_id == school_id)
            .where(Attendance.date == d)
        )
        row = result.first()
        
        days.append({
            'day': day_names.get(d.weekday(), ''),
            'date': d.strftime('%d/%m'),
            'present': row.present or 0,
            'absent': row.absent or 0,
            'late': row.late or 0,
            'is_today': i == 0
        })
    
    return days


async def build_academic_structure(
    db: AsyncSession,
    school_id: str,
    academic_year_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    بناء الهيكل الأكاديمي: السنة ← المرحلة ← الصف ← الشعبة
    """
    structure = []
    
    # جلب السنوات الدراسية
    years_query = select(AcademicYear).where(AcademicYear.school_id == school_id)
    if academic_year_id:
        years_query = years_query.where(AcademicYear.id == academic_year_id)
    
    years_result = await db.execute(years_query)
    years = years_result.scalars().all()
    
    for year in years:
        year_data = {
            'year_id': year.id,
            'year_name': year.name,
            'total_students': 0,
            'total_sections': 0,
            'attendance': {'present': 0, 'absent': 0, 'late': 0},
            'stages': []
        }
        
        # جلب المراحل لهذه السنة
        stages_result = await db.execute(
            select(Stage)
            .where(Stage.school_id == school_id)
            .where(Stage.academic_year_id == year.id)
            .order_by(Stage.order)
        )
        stages = stages_result.scalars().all()
        
        for stage in stages:
            stage_data = {
                'stage_id': stage.id,
                'stage_name': stage.name,
                'total_students': 0,
                'total_sections': 0,
                'attendance': {'present': 0, 'absent': 0, 'late': 0},
                'grades': []
            }
            
            # جلب الصفوف لهذه المرحلة
            grades_result = await db.execute(
                select(Grade)
                .where(Grade.stage_id == stage.id)
                .order_by(Grade.order)
            )
            grades = grades_result.scalars().all()
            
            for grade in grades:
                grade_data = {
                    'grade_id': grade.id,
                    'grade_name': grade.name,
                    'total_students': 0,
                    'total_sections': 0,
                    'attendance': {'present': 0, 'absent': 0, 'late': 0, 'excused': 0},
                    'sections': []
                }
                
                # جلب الفصول (الشعب) لهذا الصف
                sections_result = await db.execute(
                    select(Section)
                    .where(Section.grade_id == grade.id)
                    .order_by(Section.name)
                )
                sections = sections_result.scalars().all()
                
                for section in sections:
                    section_data = await build_section_data(db, section.id)
                    grade_data['sections'].append(section_data)
                    
                    # تجميع الإحصائيات
                    grade_data['total_students'] += section_data['total_students']
                    grade_data['total_sections'] += 1
                    for key in ['present', 'absent', 'late']:
                        grade_data['attendance'][key] += section_data['attendance'].get(key, 0)
                
                stage_data['grades'].append(grade_data)
                stage_data['total_students'] += grade_data['total_students']
                stage_data['total_sections'] += grade_data['total_sections']
                for key in ['present', 'absent', 'late']:
                    stage_data['attendance'][key] += grade_data['attendance'][key]
            
            year_data['stages'].append(stage_data)
            year_data['total_students'] += stage_data['total_students']
            year_data['total_sections'] += stage_data['total_sections']
            for key in ['present', 'absent', 'late']:
                year_data['attendance'][key] += stage_data['attendance'][key]
        
        structure.append(year_data)
    
    return structure


async def build_section_data(
    db: AsyncSession,
    section_id: str
) -> Dict[str, Any]:
    """بناء بيانات الشعبة كاملة مع المعلمين والطلاب والحصص"""
    from app.models import Section, Teacher, Student, Period, Schedule
    
    # جلب الشعبة
    section_result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    
    if not section:
        return {}
    
    # جلب المعلمين
    teachers_result = await db.execute(
        select(Teacher)
        .where(Teacher.section_id == section_id)
        .where(Teacher.is_active == True)
    )
    teachers = teachers_result.scalars().all()
    
    # جلب الطلاب
    students_result = await db.execute(
        select(Student)
        .where(Student.section_id == section_id)
        .where(Student.is_active == True)
    )
    students = students_result.scalars().all()
    
    # جلب الحصص اليوم
    today = date.today()
    periods_result = await db.execute(
        select(Period)
        .where(Period.section_id == section_id)
        .where(Period.date == today)
        .order_by(Period.period_number)
    )
    periods = periods_result.scalars().all()
    
    # ============ بناء بيانات الحضور للشعبة ============
    attendance_stats = await get_section_attendance(db, section_id)
    
    # ============ بناء بيانات الطلاب مع إحصائياتهم ============
    students_data = []
    for student in students:
        student_attendance = await get_student_attendance_summary(db, student.id)
        students_data.append({
            'name': student.name,
            'attendance': student_attendance
        })
    
    # ============ بناء بيانات المعلمين ============
    teachers_data = []
    for teacher in teachers:
        # جلب حالة المعلم اليوم
        teacher_status = await get_teacher_daily_status(db, teacher.id)
        teachers_data.append({
            'name': teacher.name,
            'specialization': teacher.specialization,
            'status': teacher_status.get('status', 'present'),
            'status_label': get_status_label(teacher_status.get('status', 'present'))
        })
    
    # ============ بناء بيانات الحصص ============
    periods_data = []
    for period in periods:
        periods_data.append({
            'period_number': f'الحصة {period.period_number}',
            'subject': period.subject.name if period.subject else '',
            'teacher': period.teacher.name if period.teacher else '',
            'status': period.status or 'scheduled',
            'status_label': get_period_status_label(period.status)
        })
    
    return {
        'section_id': section.id,
        'section_name': section.name,
        'total_students': len(students),
        'attendance': attendance_stats,
        'teachers': teachers_data,
        'students': students_data,
        'periods': periods_data
    }


async def get_section_attendance(
    db: AsyncSession,
    section_id: str
) -> Dict[str, int]:
    """جلب إحصائيات الحضور لشعبة معينة اليوم"""
    from app.models import Attendance
    
    today = date.today()
    result = await db.execute(
        select(
            func.count().filter(Attendance.status == 'present').label('present'),
            func.count().filter(Attendance.status == 'absent').label('absent'),
            func.count().filter(Attendance.status == 'late').label('late'),
            func.count().filter(Attendance.status == 'excused').label('excused'),
            func.count().filter(Attendance.status == 'sick').label('sick'),
            func.count().filter(Attendance.status == 'late_arrival').label('late_arrival'),
        )
        .select_from(Attendance)
        .where(Attendance.section_id == section_id)
        .where(Attendance.date == today)
    )
    row = result.first()
    
    return {
        'present': row.present or 0,
        'absent': row.absent or 0,
        'late': row.late or 0,
        'excused': row.excused or 0,
        'sick': row.sick or 0,
        'late_arrival': row.late_arrival or 0
    }


async def get_student_attendance_summary(
    db: AsyncSession,
    student_id: str
) -> Dict[str, int]:
    """جلب ملخص حضور طالب معين"""
    from app.models import Attendance
    
    # جلب آخر 30 يوم
    start_date = date.today() - timedelta(days=30)
    
    result = await db.execute(
        select(
            func.count().filter(Attendance.status == 'present').label('present'),
            func.count().filter(Attendance.status == 'absent').label('absent'),
            func.count().filter(Attendance.status == 'late').label('late'),
            func.count().filter(Attendance.status == 'excused').label('excused'),
        )
        .select_from(Attendance)
        .where(Attendance.student_id == student_id)
        .where(Attendance.date >= start_date)
    )
    row = result.first()
    
    return {
        'present': row.present or 0,
        'absent': row.absent or 0,
        'late': row.late or 0,
        'excused': row.excused or 0
    }


async def get_teacher_daily_status(
    db: AsyncSession,
    teacher_id: str
) -> Dict[str, str]:
    """جلب حالة المعلم اليوم"""
    from app.models import TeacherAttendance
    
    today = date.today()
    result = await db.execute(
        select(TeacherAttendance)
        .where(TeacherAttendance.teacher_id == teacher_id)
        .where(TeacherAttendance.date == today)
    )
    attendance = result.scalar_one_or_none()
    
    if attendance:
        return {'status': attendance.status}
    return {'status': 'present'}


def get_status_label(status: str) -> str:
    """تحويل حالة إلى تسمية عربية"""
    labels = {
        'present': 'حاضر',
        'absent': 'غائب',
        'late': 'متأخر',
        'excused': 'بإذن',
        'sick': 'مريض',
        'late_arrival': 'تأخير صباحي'
    }
    return labels.get(status, 'غير محدد')


def get_period_status_label(status: Optional[str]) -> str:
    """تحويل حالة الحصة إلى تسمية عربية"""
    labels = {
        'scheduled': 'مجدولة',
        'completed': 'منفذة',
        'cancelled': 'ملغية',
        'delayed': 'متأخرة',
        'in_progress': 'قيد التنفيذ'
    }
    return labels.get(status, 'قادم')


# ============================================================
# مسارات الوكيل المباشرة
# ============================================================
@router.get("/deputy/dashboard")
async def deputy_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    """إعادة توجيه إلى لوحة تحكم الوكيل"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/deputy/section/{section_id}/attendance")
async def deputy_section_attendance(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تسجيل حضور فصل معين"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    
    from app.repositories.sections import SectionRepository
    from app.repositories.students import StudentRepository
    
    section_repo = SectionRepository(db)
    student_repo = StudentRepository(db)
    
    section = await section_repo.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    students = await student_repo.get_by_section(section_id)
    
    return templates.TemplateResponse(
        "deputy/section_attendance.html",
        {
            **ctx,
            "title": f"تسجيل حضور - {section.name}",
            "section": section,
            "students": students,
            "user": user,
        },
    )


@router.get("/deputy/section/{section_id}/students")
async def deputy_section_students(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة عرض طلاب فصل معين"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    
    from app.repositories.sections import SectionRepository
    from app.repositories.students import StudentRepository
    
    section_repo = SectionRepository(db)
    student_repo = StudentRepository(db)
    
    section = await section_repo.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    students = await student_repo.get_by_section(section_id)
    
    return templates.TemplateResponse(
        "deputy/section_students.html",
        {
            **ctx,
            "title": f"طلاب - {section.name}",
            "section": section,
            "students": students,
            "user": user,
        },
    )


@router.get("/deputy/section/{section_id}/report")
async def deputy_section_report(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """تقرير فصل معين"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    
    service = DashboardService(db)
    report = await service.section_report(section_id, user.school_id)
    
    return templates.TemplateResponse(
        "deputy/section_report.html",
        {
            **ctx,
            "title": f"تقرير الفصل",
            "report": report,
            "user": user,
        },
    )


@router.get("/deputy/teacher/{teacher_id}/attendance")
async def deputy_teacher_attendance(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة حضور معلم معين"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    
    from app.repositories.teachers import TeacherRepository
    
    teacher_repo = TeacherRepository(db)
    teacher = await teacher_repo.get_by_id(teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="المعلم غير موجود")
    
    return templates.TemplateResponse(
        "deputy/teacher_attendance.html",
        {
            **ctx,
            "title": f"حضور - {teacher.name}",
            "teacher": teacher,
            "user": user,
        },
    )


@router.get("/deputy/teacher/{teacher_id}/schedule")
async def deputy_teacher_schedule(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """جدول معلم معين"""
    if user.primary_role != "deputy":
        raise ForbiddenException("هذه الصفحة مخصصة للوكيل فقط")
    
    from app.repositories.teachers import TeacherRepository
    
    teacher_repo = TeacherRepository(db)
    teacher = await teacher_repo.get_by_id(teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="المعلم غير موجود")
    
    service = DashboardService(db)
    schedule = await service.teacher_schedule(teacher_id, user.school_id)
    
    return templates.TemplateResponse(
        "deputy/teacher_schedule.html",
        {
            **ctx,
            "title": f"جدول - {teacher.name}",
            "teacher": teacher,
            "schedule": schedule,
            "user": user,
        },
    )


@router.get("/deputy/dashboard/export/report")
async def export_deputy_report(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """تصدير تقرير الوكيل"""
    if user.primary_role != "deputy":
        raise ForbiddenException("غير مصرح")
    
    stats = await get_deputy_full_stats(db, user.school_id, user.id)
    
    return JSONResponse(content={
        "status": "success",
        "data": stats,
        "export_date": datetime.now().isoformat(),
        "message": "تم تصدير التقرير بنجاح"
    })


@router.get("/deputy/debug/simple")
async def deputy_debug_simple(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """صفحة تصحيح بسيطة لعرض البيانات الخام"""
    if user.primary_role != "deputy":
        raise ForbiddenException("غير مصرح")
    
    stats = await get_deputy_full_stats(db, user.school_id, user.id)
    
    return templates.TemplateResponse(
        "deputy/debug.html",
        {
            "request": request,
            "stats": stats,
            "user": user,
            "title": "تصحيح البيانات",
        },
    )


# ============================================================
# مسارات الأدوار الأخرى
# ============================================================
@router.get("/director/dashboard")
async def director_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    """إعادة توجيه إلى لوحة تحكم المدير"""
    if user.primary_role != "director":
        raise ForbiddenException("هذه الصفحة مخصصة للمدير فقط")
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/activities/dashboard")
async def activities_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    """إعادة توجيه إلى لوحة تحكم مسؤول الأنشطة"""
    if user.primary_role != "activities_manager":
        raise ForbiddenException("هذه الصفحة مخصصة لمسؤول الأنشطة فقط")
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/teacher/dashboard")
async def teacher_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    """إعادة توجيه إلى لوحة تحكم المعلم"""
    if user.primary_role != "teacher":
        raise ForbiddenException("هذه الصفحة مخصصة للمعلم فقط")
    return RedirectResponse("/dashboard", status_code=302)


# ============================================================
# دوال مساعدة
# ============================================================
def convert_stats_to_dashboard(stats: dict, school_id: str) -> dict:
    """
    تحويل بيانات stats من DashboardService إلى الهيكل المطلوب للقالب
    (للتوافق مع الإصدارات السابقة)
    """
    from datetime import date as _date
    
    sections = []
    
    if "sections" in stats:
        for section in stats.get("sections", []):
            sections.append({
                "stage_name": section.get("stage_name", "المرحلة"),
                "grade_name": section.get("grade_name", "الصف"),
                "section_name": section.get("section_name", "فصل"),
                "enrolled_count": section.get("enrolled_count", 0),
                "periods_today": section.get("periods_today", [])
            })
    
    analytics = {
        "present": stats.get("present_count", 0),
        "absent": stats.get("absent_count", 0),
        "late": stats.get("late_count", 0),
        "late_arrivals": stats.get("late_arrivals_count", 0),
        "excused": stats.get("excused_count", 0),
        "other": stats.get("other_count", 0),
        "total_records": stats.get("total_records", 0)
    }
    
    return {
        "date": _date.today().isoformat(),
        "sections": sections,
        "analytics": analytics
    }
