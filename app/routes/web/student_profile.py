"""Student profile composite UI — أهم شاشة في النظام (مواصفات 10 + 11).

يجمع: المعلومات الأساسية | الحضور (بفلتر) | الأداء | الحالة الصحية | المرفقات |
نقل الطالب (مع الحفاظ على السجل).
"""
from datetime import date as _date, timedelta
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission, template_context
from app.core.exceptions import ForbiddenException, NotFoundException
from app.services.student_profile_service import StudentProfileService
from app.services.student_service import StudentService


router = APIRouter(prefix="/students", tags=["student-profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{student_id}/profile")
async def profile(
    student_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    preset: str = "last_30_days",
    date_from: str | None = None,
    date_to: str | None = None,
):
    svc = StudentProfileService(db)
    basic = await svc.basic(student_id)
    if not basic:
        raise NotFoundException("الطالب غير موجود")

    today = _date.today()
    if preset == "last_30_days":
        df = (today - timedelta(days=30)).isoformat()
        dt = today.isoformat()
    elif preset == "this_month":
        df = today.replace(day=1).isoformat()
        dt = today.isoformat()
    elif preset == "custom" and date_from and date_to:
        df, dt = date_from, date_to
    else:
        df = (today - timedelta(days=30)).isoformat()
        dt = today.isoformat()

    attendance = await svc.attendance_window(
        student_id, date_from=df, date_to=dt
    )
    performance = await svc.performance(student_id)
    leaves = await svc.excused_leaves(student_id)
    attachments = await svc.attachments(student_id)
    return templates.TemplateResponse(
        "students/profile_v2.html",
        {
            **ctx,
            "title": basic.get("full_name", student_id),
            "student": basic,
            "attendance": attendance,
            "performance": performance,
            "excused_leaves": leaves,
            "attachments": attachments,
            "preset": preset,
            "date_from": df,
            "date_to": dt,
        },
    )


@router.post("/{student_id}/transfer")
async def transfer(
    student_id: str,
    request: Request,
    user: CurrentUser = Depends(require_permission("students.transfer")),
    db: AsyncSession = Depends(get_db),
):
    """نقل الطالب — داخل الصف / مرحلة / مدرسة — مع **الحفاظ على السجل** عبر StudentEnrollment (status=transferred)."""
    form = await request.form()
    svc = StudentService(db)
    try:
        from app.schemas.students import TransferRequest
        req = TransferRequest(
            student_id=student_id,
            to_section_id=form.get("to_section_id"),
            year_id=form.get("year_id"),
        )
        await svc.transfer_student(user.school_id, req)
        from app.services.audit_service import AuditService
        await AuditService(db).log(
            school_id=user.school_id,
            actor_id=user.id,
            actor_role=user.primary_role,
            action="student.transfer",
            entity_type="student_enrollment",
            entity_id=student_id,
            details=f"نقل الطالب إلى الشعبة {form.get('to_section_id')}",
            extra={"to_section_id": form.get("to_section_id")},
        )
        return RedirectResponse(url=f"/students/{student_id}/profile?transferred=1", status_code=303)
    except Exception as e:
        from app.core.exceptions import AppException
        if isinstance(e, AppException):
            raise ForbiddenException(str(e))
        raise
