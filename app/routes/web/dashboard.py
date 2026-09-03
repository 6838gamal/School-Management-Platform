"""Dashboard and web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import io

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
from app.models.students import Student, StudentEnrollment
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
    target_date: Optional[str] = Query(None, description="تاريخ محدد"),
    days: Optional[int] = Query(30, description="عدد الأيام"),
    month: Optional[str] = Query(None, description="شهر محدد"),
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
        stats = await get_deputy_full_stats(
            db, user.school_id, user.id, target_date, days, month
        )
        return templates.TemplateResponse(
            "deputy/dashboard.html",
            {
                **ctx, 
                "title": "لوحة تحكم الوكيل",
                "stats": stats,
                "selected_date": target_date or date.today().isoformat(),
                "selected_month": month or date.today().strftime("%Y-%m"),
                "filter_days": days,
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
    user_id: str,
    target_date: Optional[str] = None,
    days: int = 30,
    month: Optional[str] = None
) -> Dict[str, Any]:
    """جلب جميع البيانات المطلوبة للوكيل مع الفلاتر"""
    
    # تحديد التاريخ
    if target_date:
        try:
            today = date.fromisoformat(target_date)
        except:
            today = date.today()
    else:
        today = date.today()
    
    today_str = today.strftime('%Y-%m-%d')
    
    # جلب السنة الدراسية النشطة (أو الأحدث)
    academic_year = await get_active_or_latest_academic_year(db, school_id)
    year_id = academic_year.id if academic_year else None
    
    # ============ الإحصائيات العامة ============
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
    
    # ============ إحصائيات الحضور ============
    attendance_stats = await get_attendance_stats(db, school_id, today)
    weekly_data = await get_weekly_attendance(db, school_id, days)
    
    # ============ إحصائيات المعلمين ============
    teachers_stats = await get_teachers_today_stats(db, school_id, today_str)
    absent_teachers = await get_absent_teachers(db, school_id, today_str)
    
    # ============ الهيكل الأكاديمي ============
    academic_structure = await build_academic_structure(
        db, school_id, year_id, today_str
    )
    
    return {
        'academic_year': academic_year.name if academic_year else 'السنة الحالية',
        'current_date': today_str,
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
        'teachers_stats': teachers_stats,
        'absent_teachers': absent_teachers,
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
    school_id: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """جلب بيانات الحضور لآخر N أيام"""
    results = []
    today = date.today()
    
    day_names = {0: 'الأحد', 1: 'الإثنين', 2: 'الثلاثاء', 3: 'الأربعاء', 4: 'الخميس', 5: 'الجمعة', 6: 'السبت'}
    
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        
        result = await db.execute(
            select(
                func.count().filter(StudentAttendance.status == 'present').label('present'),
                func.count().filter(StudentAttendance.status == 'absent').label('absent'),
                func.count().filter(StudentAttendance.status == 'late').label('late'),
                func.count().filter(StudentAttendance.status == 'excused').label('excused'),
                func.count().filter(StudentAttendance.status == 'sick').label('sick'),
            )
            .select_from(StudentAttendance)
            .where(StudentAttendance.school_id == school_id)
            .where(StudentAttendance.date == date_str)
        )
        row = result.first()
        
        results.append({
            'day': day_names.get(d.weekday(), ''),
            'date': d.strftime('%d/%m'),
            'present': row.present or 0,
            'absent': row.absent or 0,
            'late': row.late or 0,
            'excused': row.excused or 0,
            'sick': row.sick or 0,
            'is_today': i == 0
        })
    
    return results


async def get_teachers_today_stats(
    db: AsyncSession,
    school_id: str,
    date_str: str
) -> Dict[str, Any]:
    """جلب إحصائيات المعلمين اليوم"""
    teachers_result = await db.execute(
        select(Teacher).where(Teacher.school_id == school_id).where(Teacher.is_active == True)
    )
    all_teachers = teachers_result.scalars().all()
    total = len(all_teachers)
    
    attendance_result = await db.execute(
        select(TeacherAttendance)
        .where(TeacherAttendance.school_id == school_id)
        .where(TeacherAttendance.date == date_str)
    )
    attendances = attendance_result.scalars().all()
    
    present = 0
    absent = 0
    late = 0
    leave = 0
    
    for att in attendances:
        if att.status == 'present':
            present += 1
        elif att.status == 'absent':
            absent += 1
        elif att.status == 'late':
            late += 1
        elif att.status == 'leave':
            leave += 1
    
    recorded_ids = [att.teacher_id for att in attendances]
    unrecorded = [t for t in all_teachers if t.id not in recorded_ids]
    absent += len(unrecorded)
    
    rate = round((present / total) * 100, 1) if total > 0 else 0
    
    return {
        'total': total,
        'present': present,
        'absent': absent,
        'late': late,
        'leave': leave,
        'rate': rate,
        'unrecorded': len(unrecorded)
    }


async def get_absent_teachers(
    db: AsyncSession,
    school_id: str,
    date_str: str
) -> List[Dict[str, Any]]:
    """جلب قائمة المعلمين الغائبين"""
    teachers_result = await db.execute(
        select(Teacher).where(Teacher.school_id == school_id).where(Teacher.is_active == True)
    )
    all_teachers = teachers_result.scalars().all()
    
    attendance_result = await db.execute(
        select(TeacherAttendance)
        .where(TeacherAttendance.school_id == school_id)
        .where(TeacherAttendance.date == date_str)
    )
    attendances = attendance_result.scalars().all()
    
    recorded_ids = [att.teacher_id for att in attendances]
    absent_list = []
    
    for teacher in all_teachers:
        att = next((a for a in attendances if a.teacher_id == teacher.id), None)
        
        if att:
            if att.status in ['absent', 'late']:
                absent_list.append({
                    'id': teacher.id,
                    'name': teacher.full_name,
                    'specialization': teacher.specialization or 'غير محدد',
                    'status': att.status,
                    'status_label': 'غائب' if att.status == 'absent' else 'متأخر',
                    'note': att.note or ''
                })
        else:
            absent_list.append({
                'id': teacher.id,
                'name': teacher.full_name,
                'specialization': teacher.specialization or 'غير محدد',
                'status': 'absent',
                'status_label': 'غائب (غير مسجل)',
                'note': 'لم يتم تسجيل الحضور'
            })
    
    return absent_list


# ============================================================
# ============ بناء الهيكل الأكاديمي ============
# ============================================================

async def build_academic_structure(
    db: AsyncSession,
    school_id: str,
    year_id: Optional[str],
    date_str: str
) -> List[Dict[str, Any]]:
    """بناء الهيكل الأكاديمي مع جميع البيانات"""
    structure = []
    
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
                
                sections_result = await db.execute(
                    select(Section)
                    .where(Section.grade_id == grade.id)
                    .order_by(Section.name)
                )
                sections = sections_result.scalars().all()
                
                for section in sections:
                    section_data = await build_section_data(
                        db, section.id, year.id, date_str
                    )
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
    year_id: str,
    date_str: str
) -> Dict[str, Any]:
    """بناء بيانات الشعبة كاملة"""
    section_result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    
    if not section:
        return {}
    
    # ============ جلب المعلمين ============
    teachers_result = await db.execute(
        select(Teacher)
        .join(TeacherAssignment, TeacherAssignment.teacher_id == Teacher.id)
        .where(TeacherAssignment.section_id == section_id)
        .where(TeacherAssignment.year_id == year_id)
        .where(TeacherAssignment.status == 'active')
        .where(Teacher.is_active == True)
        .distinct()
    )
    assigned_teachers = teachers_result.scalars().all()
    
    # ============ جلب المعلمين رؤساء الفصل ============
    class_teachers = []
    if section.class_teacher_ids:
        teacher_ids = [tid.strip() for tid in section.class_teacher_ids.split(',') if tid.strip()]
        if teacher_ids:
            ct_result = await db.execute(
                select(Teacher)
                .where(Teacher.id.in_(teacher_ids))
                .where(Teacher.is_active == True)
            )
            class_teachers = ct_result.scalars().all()
    
    all_teachers = assigned_teachers.copy()
    for ct in class_teachers:
        if ct not in all_teachers:
            all_teachers.append(ct)
    
    # ============ جلب الطلاب ============
    students_result = await db.execute(
        select(Student)
        .where(Student.section_id == section_id)
        .where(Student.year_id == year_id)
        .where(Student.is_active == True)
        .order_by(Student.first_name)
    )
    students = students_result.scalars().all()
    
    # ============ جلب الحصص ============
    periods_result = await db.execute(
        select(Period)
        .where(Period.school_id == section.school_id)
        .order_by(Period.order)
    )
    all_periods = periods_result.scalars().all()
    
    # ============ جلب حضور المعلمين ============
    teacher_attendance_result = await db.execute(
        select(TeacherAttendance)
        .where(TeacherAttendance.school_id == section.school_id)
        .where(TeacherAttendance.date == date_str)
    )
    teacher_attendances = teacher_attendance_result.scalars().all()
    teacher_status_map = {att.teacher_id: att.status for att in teacher_attendances}
    
    # ============ بيانات المعلمين ============
    teachers_data = []
    for teacher in all_teachers:
        status = teacher_status_map.get(teacher.id, 'unrecorded')
        teachers_data.append({
            'id': teacher.id,
            'name': teacher.full_name,
            'specialization': teacher.specialization or 'غير محدد',
            'status': status,
            'status_label': get_teacher_status_label(status),
            'is_class_teacher': teacher in class_teachers
        })
    
    # ============ بيانات الحصص ============
    periods_data = []
    for period in all_periods:
        period_teacher = await get_period_teacher(db, section_id, period.id, year_id)
        
        if period_teacher:
            teacher_status = teacher_status_map.get(period_teacher.id, 'unrecorded')
            is_present = teacher_status == 'present'
            is_absent = teacher_status in ['absent', 'unrecorded']
            is_late = teacher_status == 'late'
        else:
            period_teacher = None
            is_present = False
            is_absent = True
            is_late = False
        
        periods_data.append({
            'period_id': period.id,
            'period_number': period.order,
            'name': period.name,
            'start_time': period.start_time,
            'end_time': period.end_time,
            'is_break': period.is_break,
            'teacher': {
                'id': period_teacher.id if period_teacher else None,
                'name': period_teacher.full_name if period_teacher else 'لا يوجد معلم',
                'is_present': is_present,
                'is_absent': is_absent,
                'is_late': is_late,
                'status_label': get_teacher_status_label(teacher_status_map.get(period_teacher.id, 'unrecorded')) if period_teacher else 'لا يوجد معلم'
            } if period_teacher else {
                'id': None,
                'name': 'لا يوجد معلم',
                'is_present': False,
                'is_absent': True,
                'is_late': False,
                'status_label': 'لا يوجد معلم'
            }
        })
    
    # ============ إحصائيات الحضور ============
    attendance_stats = await get_section_attendance(db, section_id, date_str)
    
    # ============ بيانات الطلاب ============
    students_data = []
    for student in students:
        student_attendance = await get_student_attendance_summary(db, student.id)
        student_today_status = await get_student_today_status(db, student.id, date_str)
        students_data.append({
            'id': student.id,
            'name': student.full_name,
            'attendance': student_attendance,
            'today_status': student_today_status,
            'today_status_label': get_student_status_label(student_today_status)
        })
    
    return {
        'section_id': section.id,
        'section_name': section.name,
        'total_students': len(students),
        'attendance': attendance_stats,
        'teachers': teachers_data,
        'students': students_data,
        'periods': periods_data,
        'has_class_teacher': len(class_teachers) > 0,
        'has_assigned_teachers': len(assigned_teachers) > 0
    }


async def get_period_teacher(
    db: AsyncSession,
    section_id: str,
    period_id: str,
    year_id: str
) -> Optional[Teacher]:
    """جلب المعلم المسؤول عن حصة معينة"""
    try:
        from app.models.schedules import ScheduleEntry
        result = await db.execute(
            select(Teacher)
            .join(ScheduleEntry, ScheduleEntry.teacher_id == Teacher.id)
            .where(ScheduleEntry.section_id == section_id)
            .where(ScheduleEntry.period_id == period_id)
            .where(ScheduleEntry.year_id == year_id)
            .where(Teacher.is_active == True)
            .limit(1)
        )
        teacher = result.scalar_one_or_none()
        if teacher:
            return teacher
    except:
        pass
    
    result = await db.execute(
        select(Teacher)
        .join(TeacherAssignment, TeacherAssignment.teacher_id == Teacher.id)
        .where(TeacherAssignment.section_id == section_id)
        .where(TeacherAssignment.year_id == year_id)
        .where(TeacherAssignment.status == 'active')
        .where(Teacher.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_section_attendance(
    db: AsyncSession,
    section_id: str,
    date_str: str
) -> Dict[str, int]:
    """جلب إحصائيات الحضور لشعبة معينة"""
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
                func.count().filter(StudentAttendance.status == 'sick').label('sick'),
            )
            .select_from(StudentAttendance)
            .where(StudentAttendance.student_id == student_id)
            .where(StudentAttendance.date >= start_date_str)
        )
        row = result.first()
        return {
            'present': row.present or 0,
            'absent': row.absent or 0,
            'late': row.late or 0,
            'excused': row.excused or 0,
            'sick': row.sick or 0
        }
    except:
        return {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'sick': 0}


async def get_student_today_status(
    db: AsyncSession,
    student_id: str,
    date_str: str
) -> str:
    """جلب حالة الطالب اليوم"""
    try:
        result = await db.execute(
            select(StudentAttendance.status)
            .where(StudentAttendance.student_id == student_id)
            .where(StudentAttendance.date == date_str)
        )
        status = result.scalar_one_or_none()
        return status or 'unrecorded'
    except:
        return 'unrecorded'


# ============================================================
# ============ دوال التسميات ============
# ============================================================

def get_teacher_status_label(status: str) -> str:
    labels = {
        'present': '✅ حاضر',
        'absent': '❌ غائب',
        'late': '🟠 متأخر',
        'leave': '📋 بإذن',
        'unrecorded': '⚠️ غير مسجل',
    }
    return labels.get(status, '❓ غير معروف')


def get_student_status_label(status: str) -> str:
    labels = {
        'present': '✅ حاضر',
        'absent': '❌ غائب',
        'late': '🟠 متأخر',
        'excused': '📋 بإذن',
        'sick': '🏥 مريض',
        'late_arrival': '⏰ تأخير صباحي',
        'unrecorded': '⚠️ غير مسجل'
    }
    return labels.get(status, '❓ غير معروف')


# ============================================================
# ============ مسارات الطالب ============
# ============================================================

@router.get("/deputy/student/{student_id}/profile")
async def student_profile(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة الملف الشخصي للطالب"""
    if user.primary_role not in ["deputy", "director", "teacher"]:
        raise ForbiddenException("غير مصرح")
    
    # جلب بيانات الطالب
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="الطالب غير موجود")
    
    # جلب بيانات الطالب الكاملة
    student_data = await get_student_full_data(db, student_id)
    
    return templates.TemplateResponse(
        "deputy/student_profile.html",
        {
            **ctx,
            "title": f"ملف الطالب - {student.full_name}",
            "student": student_data,
            "user": user,
        },
    )


@router.get("/deputy/student/{student_id}/attendance-report")
async def student_attendance_report(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    days: Optional[int] = Query(30, description="عدد الأيام"),
):
    """تقرير حضور الطالب"""
    if user.primary_role not in ["deputy", "director", "teacher"]:
        raise ForbiddenException("غير مصرح")
    
    # جلب بيانات الطالب
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="الطالب غير موجود")
    
    # جلب تقرير الحضور
    attendance_data = await get_student_attendance_report(db, student_id, days)
    
    return templates.TemplateResponse(
        "deputy/student_attendance_report.html",
        {
            **ctx,
            "title": f"تقرير حضور - {student.full_name}",
            "student": student,
            "attendance": attendance_data,
            "days": days,
            "user": user,
        },
    )


@router.get("/deputy/student/{student_id}/transfer")
async def student_transfer_page(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة نقل الطالب"""
    if user.primary_role not in ["deputy", "director"]:
        raise ForbiddenException("غير مصرح")
    
    # جلب بيانات الطالب
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="الطالب غير موجود")
    
    # جلب الخيارات المتاحة للنقل
    transfer_options = await get_transfer_options(db, student.school_id, student)
    
    return templates.TemplateResponse(
        "deputy/student_transfer.html",
        {
            **ctx,
            "title": f"نقل الطالب - {student.full_name}",
            "student": student,
            "options": transfer_options,
            "user": user,
        },
    )


@router.post("/deputy/student/{student_id}/transfer")
async def student_transfer(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """تنفيذ نقل الطالب"""
    if user.primary_role not in ["deputy", "director"]:
        raise ForbiddenException("غير مصرح")
    
    try:
        data = await request.form()
        transfer_type = data.get("transfer_type")  # grade / stage / section / school
        target_id = data.get("target_id")
        reason = data.get("reason", "")
        
        # تنفيذ النقل
        result = await execute_student_transfer(
            db, student_id, transfer_type, target_id, reason, user.id
        )
        
        return JSONResponse(content={
            "status": "success",
            "message": "تم نقل الطالب بنجاح",
            "data": result
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=400)


@router.get("/deputy/section/{section_id}/transfer")
async def section_transfer_page(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة نقل فصل كامل"""
    if user.primary_role not in ["deputy", "director"]:
        raise ForbiddenException("غير مصرح")
    
    # جلب بيانات الفصل
    section_result = await db.execute(
        select(Section).where(Section.id == section_id)
    )
    section = section_result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    # جلب خيارات النقل
    transfer_options = await get_transfer_options(db, section.school_id, section)
    
    return templates.TemplateResponse(
        "deputy/section_transfer.html",
        {
            **ctx,
            "title": f"نقل الفصل - {section.name}",
            "section": section,
            "options": transfer_options,
            "user": user,
        },
    )


@router.post("/deputy/section/{section_id}/transfer")
async def section_transfer(
    request: Request,
    section_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """تنفيذ نقل فصل كامل"""
    if user.primary_role not in ["deputy", "director"]:
        raise ForbiddenException("غير مصرح")
    
    try:
        data = await request.form()
        transfer_type = data.get("transfer_type")
        target_id = data.get("target_id")
        reason = data.get("reason", "")
        
        # جلب جميع طلاب الفصل
        students_result = await db.execute(
            select(Student)
            .where(Student.section_id == section_id)
            .where(Student.is_active == True)
        )
        students = students_result.scalars().all()
        
        results = []
        for student in students:
            result = await execute_student_transfer(
                db, student.id, transfer_type, target_id, 
                f"نقل فصل كامل: {reason}", user.id
            )
            results.append(result)
        
        return JSONResponse(content={
            "status": "success",
            "message": f"تم نقل {len(results)} طالب بنجاح",
            "data": results
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=400)


@router.get("/deputy/student/{student_id}/export/report")
async def export_student_report(
    request: Request,
    student_id: str,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    days: Optional[int] = Query(30),
):
    """تصدير تقرير الطالب"""
    if user.primary_role not in ["deputy", "director", "teacher"]:
        raise ForbiddenException("غير مصرح")
    
    student_data = await get_student_full_data(db, student_id)
    attendance_data = await get_student_attendance_report(db, student_id, days)
    
    return JSONResponse(content={
        "status": "success",
        "student": student_data,
        "attendance": attendance_data,
        "export_date": datetime.now().isoformat(),
        "message": "تم تصدير التقرير بنجاح"
    })


# ============================================================
# ============ دوال جلب بيانات الطالب ============
# ============================================================

async def get_student_full_data(
    db: AsyncSession,
    student_id: str
) -> Dict[str, Any]:
    """جلب بيانات الطالب الكاملة"""
    # جلب الطالب
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        return {}
    
    # جلب التسجيلات
    enrollments_result = await db.execute(
        select(StudentEnrollment)
        .where(StudentEnrollment.student_id == student_id)
        .order_by(StudentEnrollment.enrolled_at.desc())
    )
    enrollments = enrollments_result.scalars().all()
    
    # جلب إحصائيات الحضور
    attendance_stats = await get_student_attendance_summary(db, student_id)
    
    # جلب الحضور اليومي (آخر 30 يوم)
    daily_attendance = await get_student_daily_attendance(db, student_id, 30)
    
    return {
        'id': student.id,
        'name': student.full_name,
        'name_ar': student.full_name_ar,
        'student_number': student.student_number,
        'national_id': student.national_id,
        'gender': student.gender,
        'birth_date': student.birth_date,
        'age': student.age,
        'phone': student.phone,
        'address': student.address,
        'guardian_name': student.guardian_name,
        'guardian_phone': student.guardian_phone,
        'guardian_relation': student.guardian_relation,
        'enrollment_status': student.enrollment_status,
        'is_active': student.is_active,
        'enrollments': [
            {
                'id': e.id,
                'year_id': e.year_id,
                'section_id': e.section_id,
                'status': e.status,
                'enrolled_at': e.enrolled_at,
                'ended_at': e.ended_at,
                'notes': e.notes
            } for e in enrollments
        ],
        'attendance_stats': attendance_stats,
        'daily_attendance': daily_attendance
    }


async def get_student_attendance_report(
    db: AsyncSession,
    student_id: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """جلب تقرير حضور الطالب"""
    results = []
    today = date.today()
    
    start_date = today - timedelta(days=days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    # جلب سجلات الحضور
    result = await db.execute(
        select(StudentAttendance)
        .where(StudentAttendance.student_id == student_id)
        .where(StudentAttendance.date >= start_date_str)
        .order_by(StudentAttendance.date.desc())
    )
    attendances = result.scalars().all()
    
    # إنشاء قاموس للحضور
    attendance_map = {att.date: att.status for att in attendances}
    
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        status = attendance_map.get(date_str, 'unrecorded')
        
        results.append({
            'date': date_str,
            'day': d.strftime('%A'),
            'status': status,
            'status_label': get_student_status_label(status)
        })
    
    return results


async def get_student_daily_attendance(
    db: AsyncSession,
    student_id: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """جلب الحضور اليومي للطالب"""
    results = []
    today = date.today()
    
    day_names = {0: 'الأحد', 1: 'الإثنين', 2: 'الثلاثاء', 3: 'الأربعاء', 4: 'الخميس', 5: 'الجمعة', 6: 'السبت'}
    
    start_date = today - timedelta(days=days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    result = await db.execute(
        select(StudentAttendance)
        .where(StudentAttendance.student_id == student_id)
        .where(StudentAttendance.date >= start_date_str)
        .order_by(StudentAttendance.date)
    )
    attendances = result.scalars().all()
    
    attendance_map = {att.date: att.status for att in attendances}
    
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        status = attendance_map.get(date_str, 'unrecorded')
        
        results.append({
            'date': date_str,
            'day': day_names.get(d.weekday(), ''),
            'status': status,
            'status_label': get_student_status_label(status)
        })
    
    return results


# ============================================================
# ============ دوال النقل ============
# ============================================================

async def get_transfer_options(
    db: AsyncSession,
    school_id: str,
    entity: Any
) -> Dict[str, Any]:
    """جلب خيارات النقل المتاحة"""
    # جلب جميع السنوات الدراسية
    years_result = await db.execute(
        select(AcademicYear)
        .where(AcademicYear.school_id == school_id)
        .order_by(AcademicYear.start_date.desc())
    )
    years = years_result.scalars().all()
    
    # جلب جميع المراحل
    stages_result = await db.execute(
        select(Stage)
        .where(Stage.school_id == school_id)
        .order_by(Stage.order)
    )
    stages = stages_result.scalars().all()
    
    # جلب جميع الصفوف
    grades_result = await db.execute(
        select(Grade)
        .where(Grade.school_id == school_id)
        .order_by(Grade.order)
    )
    grades = grades_result.scalars().all()
    
    # جلب جميع الفصول
    sections_result = await db.execute(
        select(Section)
        .where(Section.school_id == school_id)
        .order_by(Section.name)
    )
    sections = sections_result.scalars().all()
    
    # جلب جميع المدارس (للنقل بين المدارس)
    schools_result = await db.execute(
        select(School)
        .where(School.id != school_id)
        .order_by(School.name)
    )
    schools = schools_result.scalars().all()
    
    return {
        'years': [{'id': y.id, 'name': y.name} for y in years],
        'stages': [{'id': s.id, 'name': s.name} for s in stages],
        'grades': [{'id': g.id, 'name': g.name} for g in grades],
        'sections': [{'id': s.id, 'name': s.name} for s in sections],
        'schools': [{'id': s.id, 'name': s.name} for s in schools]
    }


async def execute_student_transfer(
    db: AsyncSession,
    student_id: str,
    transfer_type: str,
    target_id: str,
    reason: str,
    user_id: str
) -> Dict[str, Any]:
    """تنفيذ نقل الطالب"""
    # جلب الطالب
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise ValueError("الطالب غير موجود")
    
    # إنهاء التسجيل الحالي
    current_enrollment = await db.execute(
        select(StudentEnrollment)
        .where(StudentEnrollment.student_id == student_id)
        .where(StudentEnrollment.status == 'active')
        .order_by(StudentEnrollment.enrolled_at.desc())
        .limit(1)
    )
    current = current_enrollment.scalar_one_or_none()
    
    if current:
        current.status = 'transferred'
        current.ended_at = date.today()
        current.notes = f"تم النقل: {reason}"
    
    # تحديث بيانات الطالب حسب نوع النقل
    if transfer_type == 'grade':
        student.grade_id = target_id
    elif transfer_type == 'section':
        student.section_id = target_id
    elif transfer_type == 'year':
        student.year_id = target_id
    elif transfer_type == 'school':
        student.school_id = target_id
    
    # إنشاء تسجيل جديد
    new_enrollment = StudentEnrollment(
        student_id=student_id,
        school_id=student.school_id,
        year_id=student.year_id,
        section_id=student.section_id,
        class_id=None,
        status='active',
        enrolled_at=date.today(),
        notes=f"نقل {transfer_type} إلى {target_id} - {reason}"
    )
    
    db.add(new_enrollment)
    await db.commit()
    await db.refresh(new_enrollment)
    
    return {
        'student_id': student_id,
        'transfer_type': transfer_type,
        'target_id': target_id,
        'reason': reason,
        'enrollment_id': new_enrollment.id
    }


# ============================================================
# ============ مسارات التصدير ============
# ============================================================

@router.get("/deputy/dashboard/export/report")
async def export_deputy_report(
    request: Request,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    target_date: Optional[str] = Query(None),
    days: Optional[int] = Query(30),
):
    """تصدير تقرير الوكيل"""
    if user.primary_role != "deputy":
        raise ForbiddenException("غير مصرح")
    
    stats = await get_deputy_full_stats(
        db, user.school_id, user.id, target_date, days
    )
    
    return JSONResponse(content={
        "status": "success",
        "data": stats,
        "export_date": datetime.now().isoformat(),
        "message": "تم تصدير التقرير بنجاح"
    })


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
            "title": f"حضور - {teacher.full_name}",
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
            "title": f"جدول - {teacher.full_name}",
            "teacher": teacher,
            "schedule": schedule,
            "user": user,
        },
    )


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
