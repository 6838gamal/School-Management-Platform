"""Attendance API — late_arrival + deputy-only enforcement."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.core.exceptions import ForbiddenException
from app.models.attendance import StudentAttendance
from app.models.students import Student
from app.services.audit_service import AuditService
from sqlalchemy import select


router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/late")
async def record_late(
    student_id: str,
    date: str,
    late_arrival_minutes: int,
    note: str = "",
    period_id: Optional[str] = None,
    section_id: Optional[str] = None,
    user: CurrentUser = Depends(require_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل تأخير صباحي للطالب — backend RBAC.

    > المعلم يستطيع تسجيل التأخير (لاحظ حالة "حاضر متأخر")، لكن لا يستطيع تعديل غياب أو استئذان.
    """
    student = (
        await db.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if not student or student.school_id != user.school_id:
        raise HTTPException(404, detail="الطالب غير موجود")
    row = (
        await db.execute(
            select(StudentAttendance).where(
                StudentAttendance.student_id == student_id,
                StudentAttendance.date == date,
                StudentAttendance.period_id == period_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        row = StudentAttendance(
            school_id=user.school_id,
            student_id=student_id,
            section_id=section_id or student.section_id,
            period_id=period_id,
            date=date,
            status="late",
            late_arrival_minutes=late_arrival_minutes,
            note=note,
            recorded_by=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.status = "late"
        row.late_arrival_minutes = late_arrival_minutes
        row.note = note
        row.recorded_by = user.id
        row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await AuditService(db).log(
        school_id=user.school_id,
        actor_id=user.id,
        actor_role=user.primary_role,
        action="attendance.late_record",
        entity_type="student_attendance",
        entity_id=row.id,
        details=f"تأخير {late_arrival_minutes} دقيقة للطالب {student.full_name} يوم {date}",
        extra={"student_id": student_id, "date": date, "late_minutes": late_arrival_minutes},
    )
    return {"id": row.id, "status": row.status, "late_arrival_minutes": late_arrival_minutes}


@router.post("/absent")
async def record_absent(
    student_id: str,
    date: str,
    note: str = "",
    period_id: Optional[str] = None,
    section_id: Optional[str] = None,
    user: CurrentUser = Depends(require_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل غياب — **الوكيل فقط** (لا يستطيع المعلم)."""
    if "attendance.create" not in user.permissions:
        raise ForbiddenException("لا تملك صلاحية تسجيل غياب")
    if user.primary_role == "teacher":
        raise ForbiddenException(
            "النظام يفرض على الـbackend: المعلم لا يستطيع تسجيل الغياب، وإن أخفى الزر"
        )
    student = (
        await db.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if not student or student.school_id != user.school_id:
        raise HTTPException(404, detail="الطالب غير موجود")
    row = (
        await db.execute(
            select(StudentAttendance).where(
                StudentAttendance.student_id == student_id,
                StudentAttendance.date == date,
                StudentAttendance.period_id == period_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        row = StudentAttendance(
            school_id=user.school_id,
            student_id=student_id,
            section_id=section_id or student.section_id,
            period_id=period_id,
            date=date,
            status="absent",
            note=note,
            recorded_by=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.status = "absent"
        row.note = note
        row.recorded_by = user.id
        row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await AuditService(db).log(
        school_id=user.school_id,
        actor_id=user.id,
        actor_role=user.primary_role,
        action="attendance.absent_record",
        entity_type="student_attendance",
        entity_id=row.id,
        details=f"تسجيل غياب للطالب {student.full_name} يوم {date}",
        extra={"student_id": student_id, "date": date},
    )
    return {"id": row.id, "status": row.status}
