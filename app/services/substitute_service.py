"""Substitute teacher service — تكليف معلم بديل."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.academics import Subject
from app.models.schedules import ScheduleEntry
from app.models.session_lifecycle import SessionLifecycle
from app.models.substitute_assignments import (
    SUBSTITUTE_STATUSES,
    SubstituteAssignment,
)
from app.models.teachers import Teacher, TeacherAssignment
from app.services.audit_service import AuditService


async def _specialist_ids(db: AsyncSession, school_id: str, subject_id: str) -> list[str]:
    rows = (
        await db.execute(
            select(TeacherAssignment.teacher_id).where(
                TeacherAssignment.school_id == school_id,
                TeacherAssignment.subject_id == subject_id,
                TeacherAssignment.status == "active",
            )
        )
    ).scalars().all()
    return list(rows)


async def _other_specialist_ids(
    db: AsyncSession, school_id: str, exclude_teacher_id: str
) -> list[str]:
    """أي معلم آخر مكلف في المدرسة (تخصص مختلف)."""
    rows = (
        await db.execute(
            select(TeacherAssignment.teacher_id).where(
                TeacherAssignment.school_id == school_id,
                TeacherAssignment.status == "active",
                TeacherAssignment.teacher_id != exclude_teacher_id,
            ).distinct()
        )
    ).scalars().all()
    return list(rows)


class SubstituteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_alternatives(
        self, *, school_id: str, schedule_entry_id: str, date: str
    ) -> dict:
        """يعرض البدلاء مقسمين حسب تخصص المادة نفسها / تخصص آخر."""
        entry = (
            await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.id == schedule_entry_id)
            )
        ).scalar_one_or_none()
        if not entry:
            raise NotFoundException("المدخل غير موجود")

        same_subj = await _specialist_ids(self.db, school_id, entry.subject_id)
        same_subj = [t for t in same_subj if t != entry.teacher_id]
        other_subj = await _other_specialist_ids(
            self.db, school_id, entry.teacher_id
        )
        # remove overlap
        other_subj = [t for t in other_subj if t not in same_subj]

        async def hydrate(ids: list[str]) -> list[dict]:
            if not ids:
                return []
            rows = (
                await self.db.execute(
                    select(Teacher).where(
                        Teacher.school_id == school_id,
                        Teacher.id.in_(ids),
                        Teacher.is_active == True,
                    )
                )
            ).scalars().all()
            return [
                {
                    "id": t.id,
                    "full_name": t.full_name,
                    "employee_number": t.employee_number,
                    "specialization": t.specialization,
                }
                for t in rows
            ]

        return {
            "schedule_entry_id": schedule_entry_id,
            "date": date,
            "absent_teacher_id": entry.teacher_id,
            "same_specialty": await hydrate(same_subj),
            "other_specialty": await hydrate(other_subj),
        }

    async def request(
        self,
        *,
        school_id: str,
        actor_id: str,
        actor_role: str,
        user_permissions: set[str],
        schedule_entry_id: str,
        absent_teacher_id: str,
        substitute_teacher_id: str,
        date: str,
        reason: str | None = None,
    ) -> SubstituteAssignment:
        if "substitutes.create" not in user_permissions:
            raise ForbiddenException("لا تملك صلاحية تكليف معلم بديل")
        if absent_teacher_id == substitute_teacher_id:
            raise ValidationException("لا يمكن تكليف نفس المعلم بديلاً عن نفسه")
        sa = SubstituteAssignment(
            school_id=school_id,
            schedule_entry_id=schedule_entry_id,
            absent_teacher_id=absent_teacher_id,
            substitute_teacher_id=substitute_teacher_id,
            date=date,
            status="pending",
            reason=reason,
            requested_by=actor_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(sa)
        await self.db.flush()
        await self.db.refresh(sa)
        # Auto-transition session lifecycle to substitute_required
        sess = (
            await self.db.execute(
                select(SessionLifecycle).where(
                    SessionLifecycle.schedule_entry_id == schedule_entry_id,
                    SessionLifecycle.date == date,
                )
            )
        ).scalar_one_or_none()
        if sess and sess.status in ("teacher_absent", "scheduled"):
            sess.status = "substitute_required"
            sess.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
        await self.audit.log(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="substitute.create",
            entity_type="substitute_assignment",
            entity_id=sa.id,
            details=f"تكليف بديل: {absent_teacher_id} -> {substitute_teacher_id} يوم {date}",
            extra={"date": date, "reason": reason},
        )
        return sa

    async def respond(
        self,
        *,
        school_id: str,
        actor_id: str,
        actor_role: str,
        user_permissions: set[str],
        assignment_id: str,
        accept: bool,
        reason: str | None = None,
    ) -> SubstituteAssignment:
        if "substitutes.respond" not in user_permissions:
            raise ForbiddenException("لا تملك صلاحية الرد على التكليف")
        sa = (
            await self.db.execute(
                select(SubstituteAssignment).where(
                    SubstituteAssignment.id == assignment_id,
                    SubstituteAssignment.school_id == school_id,
                )
            )
        ).scalar_one_or_none()
        if not sa:
            raise NotFoundException("التكليف غير موجود")
        if sa.status != "pending":
            raise ConflictException(f"لا يمكن تغيير حالة تكليف بحالة {sa.status}")

        now = datetime.now(timezone.utc).isoformat()
        if accept:
            sa.status = "accepted"
            sa.accepted_at = now
            sess = (
                await self.db.execute(
                    select(SessionLifecycle).where(
                        SessionLifecycle.schedule_entry_id == sa.schedule_entry_id,
                        SessionLifecycle.date == sa.date,
                    )
                )
            ).scalar_one_or_none()
            if sess:
                sess.status = "substitute_accepted"
                sess.substitute_teacher_id = sa.substitute_teacher_id
                sess.updated_at = datetime.now(timezone.utc)
                await self.db.flush()
        else:
            sa.status = "rejected"
            sa.rejected_at = now
            sa.cancel_reason = reason

        await self.db.flush()
        await self.audit.log(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="substitute.respond",
            entity_type="substitute_assignment",
            entity_id=sa.id,
            details=("accepted" if accept else f"rejected ({reason})"),
            extra={"accepted": accept},
        )
        return sa

    async def list_inbox(self, school_id: str, substitute_user_id: str) -> list[dict]:
        # resolve substitute teacher id from user_id
        teacher = (
            await self.db.execute(
                select(Teacher).where(Teacher.user_id == substitute_user_id)
            )
        ).scalar_one_or_none()
        if not teacher:
            return []
        rows = (
            await self.db.execute(
                select(SubstituteAssignment)
                .where(
                    SubstituteAssignment.school_id == school_id,
                    SubstituteAssignment.substitute_teacher_id == teacher.id,
                    SubstituteAssignment.status == "pending",
                )
                .order_by(SubstituteAssignment.date.desc())
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "absent_teacher_id": r.absent_teacher_id,
                "date": r.date,
                "reason": r.reason,
                "status": r.status,
                "schedule_entry_id": r.schedule_entry_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
