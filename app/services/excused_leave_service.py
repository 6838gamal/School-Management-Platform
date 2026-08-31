"""Excused leave (استئذان) — صلاحية حصرية للوكيل."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import PERMISSIONS
from app.models.excused_leaves import ExcusedLeave
from app.models.students import Student, StudentEnrollment
from app.services.audit_service import AuditService


# Helper — backend-enforced RBAC for the excused_leaves "create" action.
def _assert_can_create_excused(user_permissions: set[str], primary_role: str) -> None:
    """رفض من المعلم في الـbackend — لا يكفي إخفاء الزر."""
    if primary_role == "teacher":
        raise ForbiddenException(
            "تسجيل الاستئذان صلاحية حصرية للوكيل — لا يستطيع المعلم إنشاؤه أو تعديله"
        )
    if "excused_leaves.create" not in user_permissions:
        raise ForbiddenException("لا تملك صلاحية تسجيل استئذان")


class ExcusedLeaveService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def create(
        self,
        *,
        school_id: str,
        actor_id: str,
        actor_role: str,
        user_permissions: set[str],
        student_id: str,
        date: str,
        requested_at: str,
        exit_time: str,
        reason: str,
        guardian_name: str,
        guardian_relation: str,
        guardian_phone: str,
        notes: str | None = None,
    ) -> ExcusedLeave:
        _assert_can_create_excused(user_permissions, actor_role)

        student = (
            await self.db.execute(
                select(Student).where(
                    Student.id == student_id, Student.school_id == school_id
                )
            )
        ).scalar_one_or_none()
        if not student:
            raise NotFoundException("الطالب غير موجود")
        if not student.is_active:
            raise ValidationException("الطالب غير نشط")

        # resolve current section for traceability
        section_id: Optional[str] = None
        enrollment = (
            await self.db.execute(
                select(StudentEnrollment).where(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.status == "active",
                )
            )
        ).scalar_one_or_none()
        if enrollment:
            section_id = enrollment.section_id

        if not reason or len(reason.strip()) < 3:
            raise ValidationException("سبب الاستئذان مطلوب")

        leave = ExcusedLeave(
            school_id=school_id,
            student_id=student_id,
            section_id=section_id,
            date=date,
            requested_at=requested_at,
            exit_time=exit_time,
            reason=reason.strip(),
            guardian_name=guardian_name.strip(),
            guardian_relation=guardian_relation.strip(),
            guardian_phone=guardian_phone.strip(),
            notes=(notes.strip() if notes else None),
            recorded_by=actor_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(leave)
        await self.db.flush()
        await self.db.refresh(leave)

        await self.audit.log(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="excused_leave.create",
            entity_type="excused_leave",
            entity_id=leave.id,
            details=f"استئذان الطالب {student.full_name} يوم {date}",
            extra={
                "student_id": student_id,
                "section_id": section_id,
                "guardian_relation": guardian_relation,
            },
        )
        return leave

    async def list_for_section(
        self, school_id: str, section_id: str, date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        stmt = select(ExcusedLeave).where(
            ExcusedLeave.school_id == school_id,
            ExcusedLeave.section_id == section_id,
        )
        if date_from:
            stmt = stmt.where(ExcusedLeave.date >= date_from)
        if date_to:
            stmt = stmt.where(ExcusedLeave.date <= date_to)
        stmt = stmt.order_by(ExcusedLeave.date.desc(), ExcusedLeave.exit_time.desc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "date": r.date,
                "requested_at": r.requested_at,
                "exit_time": r.exit_time,
                "reason": r.reason,
                "guardian_name": r.guardian_name,
                "guardian_relation": r.guardian_relation,
                "guardian_phone": r.guardian_phone,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def list_for_student(
        self, school_id: str, student_id: str, limit: int = 50
    ) -> list[dict]:
        rows = (
            await self.db.execute(
                select(ExcusedLeave)
                .where(
                    ExcusedLeave.school_id == school_id,
                    ExcusedLeave.student_id == student_id,
                )
                .order_by(ExcusedLeave.date.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "date": r.date,
                "requested_at": r.requested_at,
                "exit_time": r.exit_time,
                "reason": r.reason,
                "guardian_name": r.guardian_name,
                "guardian_relation": r.guardian_relation,
                "guardian_phone": r.guardian_phone,
                "notes": r.notes,
            }
            for r in rows
        ]
