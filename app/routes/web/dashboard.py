"""Dashboard and onboarding web routes."""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_user, template_context
from app.core.exceptions import ForbiddenException
from app.services.academic_service import AcademicService
from app.services.report_service import DashboardService

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
        # استدعاء الدالة بدون معاملات إضافية
        stats = await service.deputy_stats(user.school_id, user.id)
        
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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
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
    
    service = DashboardService(db)
    stats = await service.deputy_stats(user.school_id, user.id)
    
    # يمكن تحويل البيانات إلى CSV أو Excel أو PDF
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
    
    service = DashboardService(db)
    stats = await service.deputy_stats(user.school_id, user.id)
    
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
    
    # استخراج الفصول من stats
    sections = []
    
    # إذا كانت stats تحتوي على بيانات الفصول
    if "sections" in stats:
        for section in stats.get("sections", []):
            sections.append({
                "stage_name": section.get("stage_name", "المرحلة"),
                "grade_name": section.get("grade_name", "الصف"),
                "section_name": section.get("section_name", "فصل"),
                "enrolled_count": section.get("enrolled_count", 0),
                "periods_today": section.get("periods_today", [])
            })
    
    # إحصائيات الحضور
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
