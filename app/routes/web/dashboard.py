"""Dashboard and web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_user, template_context
from app.core.exceptions import ForbiddenException
from app.services.academic_service import AcademicService
from app.services.report_service import DashboardService
from app.models.users import User
from app.models.schools import School
from app.models.academics import (
    AcademicYear, Stage, Grade, Section, Subject, Period, Room
)
from app.models.students import Student
from app.models.teachers import Teacher, TeacherAssignment
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
    
    role = user.primary_role
    
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
    
    raise ForbiddenException("دور غير معروف")


# ============================================================
# ============ دوال جلب البيانات للوكيل ============
# ============================================================

async def get_deputy_full_stats(
    db: AsyncSession,
    school_id: str,
    user_id: str
) -> Dict[str, Any]:
    """جلب جميع البيانات المطلوبة للوكيل مع الهيكل الأكاديمي الكامل"""
    today = date.today()
    
    # جلب السنة الدراسية النشطة (أو الأحدث)
    academic_year = await get_active_or_latest_academic_year(db, school_id)
    
    # الإحصائيات العامة
    total_students = await db.scalar(
        select(func.count()).select_from(Student)
        .where(Student.school_id == school_id)
        .where(Student.is_active == True)
    ) or 0
    
    total_teachers = await db.scalar(
        select(func.count()).select_from(Teacher)
        .where(Teacher.school_id == school_id)
        .where(Teacher.is_active == True)
    ) or 0
    
    total_sections = await db.scalar(
        select(func.count()).select_from(Section)
        .where(Section.school_id == school_id)
    ) or 0
    
    total_subjects = await db.scalar(
        select(func.count()).select_from(Subject)
        .where(Subject.school_id == school_id)
    ) or 0
    
    # إحصائيات الحضور
    attendance_stats = await get_attendance_stats(db, school_id, today)
    weekly_data = await get_weekly_attendance(db, school_id)
    
    # الهيكل الأكاديمي
    academic_structure = await build_academic_structure(db, school_id, academic_year.id if academic_year else None)
    
    return {
        'academic_year': academic_year.name if academic_year else 'السنة الحالية',
        'current_date': today.strftime('%Y-%m-%d'),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_sections': total_sections,
        'total_subjects': total_subjects,
        'total_present': attendance_stats.get('present', 0),
        'total_absent': attendance_stats.get('absent', 0),
        'total_late': attendance_stats.get('late', 0),
        'total_excused': attendance_stats.get('excused', 0),
        'total_sick': attendance_stats.get('sick', 0),
        'total_late_arrival': attendance_stats.get('late_arrival', 0),
        'attendance_rate': attendance_stats.get('rate', 0),
        'weekly_days': weekly_data,
        'academic_structure': academic_structure,
        'error': None
    }


async def get_active_or_latest_academic_year(
    db: AsyncSession,
    school_id: str
) -> Optional[AcademicYear]:
    """جلب السنة الدراسية النشطة، أو الأحدث"""
    result = await db.execute(
        select(AcademicYear)
        .where(AcademicYear.school_id == school_id)
        .where(AcademicYear.is_current == True)
        .limit(1)
    )
    year = result.scalar_one_or_none()
    
    if not year:
        result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.start_date.desc())
            .limit(1)
        )
        year = result.scalar_one_or_none()
    
    return year


async def get_attendance_stats(
    db: AsyncSession,
    school_id: str,
    target_date: date
) -> Dict[str, Any]:
    """جلب إحصائيات الحضور ليوم محدد"""
    date_str = target_date.strftime('%Y-%m-%d')
    
    result = await db.execute(
        select(StudentAttendance)
        .where(StudentAttendance.school_id == school_id)
        .where(StudentAttendance.date == date_str)
    )
    attendances = result.scalars().all()
    
    stats = {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'sick': 0, 'late_arrival': 0, 'rate': 0}
    total = 0
    
    for att in attendances:
        if att.status in stats:
            stats[att.status] += 1
            total += 1
    
    if total > 0:
        stats['rate'] = round((stats['present'] / total) * 100, 1)
    
    return stats


async def get_weekly_attendance(
    db: AsyncSession,
    school_id: str
) -> List[Dict[str, Any]]:
    """جلب بيانات الحضور لآخر 7 أيام"""
    days = []
    today = date.today()
    
    day_names = {0: 'الأحد', 1: 'الإثنين', 2: 'الثلاثاء', 3: 'الأربعاء', 4: 'الخميس', 5: 'الجمعة', 6: 'السبت'}
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        
        result = await db.execute(
            select(
                func.count().filter(StudentAttendance.status == 'present').label('present'),
                func.count().filter(StudentAttendance.status == 'absent').label('absent'),
                func.count().filter(StudentAttendance.status == 'late').label('late'),
            )
            .select_from(StudentAttendance)
            .where(StudentAttendance.school_id == school_id)
            .where(StudentAttendance.date == date_str)
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
    year_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    بناء الهيكل الأكاديمي: السنة ← المرحلة ← الصف ← الشعبة
    باستخدام العلاقات الصحيحة من النماذج
    """
    structure = []
    
    # جلب السنوات الدراسية
    years_query = select(AcademicYear).where(AcademicYear.school_id == school_id)
    if year_id:
        years_query = years_query.where(AcademicYear.id == year_id)
    years_query = years_query.order_by(AcademicYear.start_date.desc())
    
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
        
        # جلب المراحل لهذه السنة (year_id)
        stages_result = await db.execute(
            select(Stage)
            .where(Stage.school_id == school_id)
            .where(Stage.year_id == year.id)
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
            
            # جلب الصفوف لهذه المرحلة (stage_id)
            grades_result = await db.execute(
                select(Grade)
                .where(Grade.stage_id == stage.id)
                .where(Grade.year_id == year.id)
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
                
                # جلب الفصول (الشعب) لهذا الصف (grade_id)
                sections_result = await db.execute(
                    select(Section)
                    .where(Section.grade_id == grade.id)
                    .order_by(Section.name)
                )
                sections = sections_result.scalars().all()
                
                for section in sections:
                    section_data = await build_section_data(db, section.id, year.id)
                    grade_data['sections'].append(section_data)
                    
                    grade_data['total_students'] += section_data.get('total_students', 0)
                    grade_data['total_sections'] += 1
                    for key in ['present', 'absent', 'late']:
                        grade_data['attendance'][key] += section_data.get('attendance', {}).get(key, 0)
                
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
    section_id: str,
    year_id: str
) -> Dict[str, Any]:
    """بناء بيانات الشعبة كاملة مع المعلمين والطلاب والحصص"""
    
    # جلب الشعبة
    section_result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    
    if not section:
        return {}
    
    # ============ جلب المعلمين من خلال TeacherAssignment ============
    teachers_result = await db.execute(
        select(Teacher)
        .join(TeacherAssignment, TeacherAssignment.teacher_id == Teacher.id)
        .where(TeacherAssignment.section_id == section_id)
        .where(TeacherAssignment.year_id == year_id)
        .where(TeacherAssignment.status == 'active')
        .where(Teacher.is_active == True)
        .distinct()
    )
    teachers = teachers_result.scalars().all()
    
    # ============ جلب الطلاب ============
    students_result = await db.execute(
        select(Student)
        .where(Student.section_id == section_id)
        .where(Student.year_id == year_id)
        .where(Student.is_active == True)
        .order_by(Student.first_name)
    )
    students = students_result.scalars().all()
    
    # ============ جلب الحصص (Periods) ============
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    try:
        periods_result = await db.execute(
            select(Period)
            .where(Period.school_id == section.school_id)
            .order_by(Period.order)
        )
        periods = periods_result.scalars().all()
    except:
        periods = []
    
    # ============ إحصائيات الحضور للشعبة ============
    attendance_stats = await get_section_attendance(db, section_id, today_str)
    
    # ============ بيانات الطلاب ============
    students_data = []
    for student in students:
        student_attendance = await get_student_attendance_summary(db, student.id)
        student_today_status = await get_student_today_status(db, student.id, today_str)
        students_data.append({
            'name': student.full_name,
            'attendance': student_attendance,
            'today_status': student_today_status
        })
    
    # ============ بيانات المعلمين ============
    teachers_data = []
    for teacher in teachers:
        teacher_status = await get_teacher_daily_status(db, teacher.id, today_str)
        teachers_data.append({
            'name': teacher.full_name,
            'specialization': teacher.specialization or 'غير محدد',
            'status': teacher_status.get('status', 'present'),
            'status_label': get_status_label(teacher_status.get('status', 'present'))
        })
    
    # ============ بيانات الحصص ============
    periods_data = []
    for period in periods:
        periods_data.append({
            'period_number': period.order,
            'name': period.name,
            'start_time': period.start_time,
            'end_time': period.end_time,
            'is_break': period.is_break
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
    section_id: str,
    date_str: str
) -> Dict[str, int]:
    """جلب إحصائيات الحضور لشعبة معينة في تاريخ محدد"""
    try:
        result = await db.execute(
            select(
                func.count().filter(StudentAttendance.status == 'present').label('present'),
                func.count().filter(StudentAttendance.status == 'absent').label('absent'),
                func.count().filter(StudentAttendance.status == 'late').label('late'),
                func.count().filter(StudentAttendance.status == 'excused').label('excused'),
                func.count().filter(StudentAttendance.status == 'sick').label('sick'),
                func.count().filter(StudentAttendance.status == 'late_arrival').label('late_arrival'),
            )
            .select_from(StudentAttendance)
            .where(StudentAttendance.section_id == section_id)
            .where(StudentAttendance.date == date_str)
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
    except:
        return {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'sick': 0, 'late_arrival': 0}


async def get_student_attendance_summary(
    db: AsyncSession,
    student_id: str
) -> Dict[str, int]:
    """جلب ملخص حضور طالب (آخر 30 يوم)"""
    start_date = date.today() - timedelta(days=30)
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    try:
        result = await db.execute(
            select(
                func.count().filter(StudentAttendance.status == 'present').label('present'),
                func.count().filter(StudentAttendance.status == 'absent').label('absent'),
                func.count().filter(StudentAttendance.status == 'late').label('late'),
                func.count().filter(StudentAttendance.status == 'excused').label('excused'),
            )
            .select_from(StudentAttendance)
            .where(StudentAttendance.student_id == student_id)
            .where(StudentAttendance.date >= start_date_str)
        )
        row = result.first()
        return {'present': row.present or 0, 'absent': row.absent or 0, 'late': row.late or 0, 'excused': row.excused or 0}
    except:
        return {'present': 0, 'absent': 0, 'late': 0, 'excused': 0}


async def get_student_today_status(
    db: AsyncSession,
    student_id: str,
    date_str: str
) -> str:
    """جلب حالة الطالب في تاريخ محدد"""
    try:
        result = await db.execute(
            select(StudentAttendance.status)
            .where(StudentAttendance.student_id == student_id)
            .where(StudentAttendance.date == date_str)
        )
        status = result.scalar_one_or_none()
        return status or 'غير مسجل'
    except:
        return 'غير مسجل'


async def get_teacher_daily_status(
    db: AsyncSession,
    teacher_id: str,
    date_str: str
) -> Dict[str, str]:
    """جلب حالة المعلم في تاريخ محدد"""
    try:
        result = await db.execute(
            select(TeacherAttendance)
            .where(TeacherAttendance.teacher_id == teacher_id)
            .where(TeacherAttendance.date == date_str)
        )
        attendance = result.scalar_one_or_none()
        if attendance:
            return {'status': attendance.status}
        return {'status': 'present'}
    except:
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


# ============================================================
# مسارات الوكيل المباشرة
# ============================================================
@router.get("/deputy/dashboard")
async def deputy_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
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
    if user.primary_role != "director":
        raise ForbiddenException("هذه الصفحة مخصصة للمدير فقط")
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/activities/dashboard")
async def activities_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    if user.primary_role != "activities_manager":
        raise ForbiddenException("هذه الصفحة مخصصة لمسؤول الأنشطة فقط")
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/teacher/dashboard")
async def teacher_dashboard_redirect(
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    if user.primary_role != "teacher":
        raise ForbiddenException("هذه الصفحة مخصصة للمعلم فقط")
    return RedirectResponse("/dashboard", status_code=302)
