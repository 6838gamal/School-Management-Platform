"""Student profile composite — the "most important screen".

Spec (10): basic info | attendance (with 30-day/month/custom filter)
| academic performance | health | attachments.
"""
from __future__ import annotations

from datetime import date as _date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import Section, Grade, Stage, AcademicYear, Subject
from app.models.attachments import StudentAttachment
from app.models.attendance import StudentAttendance
from app.models.behavior import BehaviorRecord
from app.models.excused_leaves import ExcusedLeave
from app.models.grades import Grade as GradeEntry
from app.models.homework import Homework
from app.models.schedules import Period
from app.models.students import Student, StudentEnrollment
from app.models.teachers import Teacher


class StudentProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def basic(self, student_id: str) -> dict:
        s = (
            await self.db.execute(select(Student).where(Student.id == student_id))
        ).scalar_one_or_none()
        if not s:
            return {}
        record = {
            "id": s.id,
            "student_number": s.student_number,
            "national_id": s.national_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "full_name": s.full_name,
            "gender": s.gender,
            "birth_date": s.birth_date,
            "guardian_name": s.guardian_name,
            "guardian_phone": s.guardian_phone,
            "guardian_email": s.guardian_email,
            "address": s.address,
            "photo_url": s.photo_url,
            "is_active": s.is_active,
            "health_status": s.health_status,
            "health_notes": s.health_notes,
        }

        enrollment = (
            await self.db.execute(
                select(StudentEnrollment).where(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.status == "active",
                )
            )
        ).scalar_one_or_none()
        if enrollment:
            record.update(
                {
                    "section_id": enrollment.section_id,
                    "year_id": enrollment.year_id,
                }
            )
            if enrollment.section_id:
                section = (
                    await self.db.execute(
                        select(Section).where(Section.id == enrollment.section_id)
                    )
                ).scalar_one_or_none()
                if section:
                    record["section_name"] = section.name
                    if section.grade_id:
                        grade = (
                            await self.db.execute(
                                select(Grade).where(Grade.id == section.grade_id)
                            )
                        ).scalar_one_or_none()
                        if grade:
                            record["grade_name"] = grade.name
                            if grade.stage_id:
                                stage = (
                                    await self.db.execute(
                                        select(Stage).where(Stage.id == grade.stage_id)
                                    )
                                ).scalar_one_or_none()
                                if stage:
                                    record["stage_name"] = stage.name
            if enrollment.year_id:
                year = (
                    await self.db.execute(
                        select(AcademicYear).where(AcademicYear.id == enrollment.year_id)
                    )
                ).scalar_one_or_none()
                if year:
                    record["academic_year"] = year.name
        return record

    async def attendance_window(
        self,
        student_id: str,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> dict:
        # default: last 30 days
        today = _date.today()
        df = date_from or (today - timedelta(days=30)).isoformat()
        dt = date_to or today.isoformat()

        stmt = select(StudentAttendance).where(
            StudentAttendance.student_id == student_id,
            StudentAttendance.date >= df,
            StudentAttendance.date <= dt,
        ).order_by(StudentAttendance.date.desc())
        rows = (await self.db.execute(stmt)).scalars().all()

        # build per-day timeline for the calendar visualisation
        all_days = [
            (today - timedelta(days=i)).isoformat()
            for i in range((today - _date.fromisoformat(df)).days + 1)
        ]
        by_day = {r.date: r for r in rows}
        timeline = [
            {
                "date": d,
                "status": (by_day[d].status if d in by_day else None),
                "late_minutes": (by_day[d].late_arrival_minutes if d in by_day else None),
                "note": (by_day[d].note if d in by_day else None),
            }
            for d in all_days
        ]
        counts = {
            "present": sum(1 for r in rows if r.status == "present"),
            "absent":  sum(1 for r in rows if r.status == "absent"),
            "late":    sum(1 for r in rows if r.status == "late"),
            "excused": sum(1 for r in rows if r.status == "excused"),
        }
        return {
            "date_from": df, "date_to": dt,
            "timeline": timeline,
            "counts": counts,
            "rows": [
                {
                    "id": r.id, "date": r.date, "status": r.status,
                    "late_minutes": r.late_arrival_minutes,
                    "note": r.note,
                }
                for r in rows
            ],
        }

    async def performance(self, student_id: str) -> dict:
        # grades
        grade_rows = (
            await self.db.execute(
                select(GradeEntry).where(GradeEntry.student_id == student_id)
            )
        ).scalars().all()
        # homework participation
        hw_rows = (
            await self.db.execute(
                select(Homework).where(Homework.student_id == student_id)
            )
        ).scalars().all()
        bh_rows = (
            await self.db.execute(
                select(BehaviorRecord).where(BehaviorRecord.student_id == student_id)
            )
        ).scalars().all()
        return {
            "grades": [
                {
                    "id": r.id, "subject_id": r.subject_id,
                    "value": r.value, "max_value": r.max_value,
                    "term": getattr(r, "term", None), "date": str(getattr(r, "date", "")),
                }
                for r in grade_rows
            ],
            "homework": [
                {
                    "id": r.id, "title": getattr(r, "title", None),
                    "status": getattr(r, "status", None),
                    "due_date": str(getattr(r, "due_date", "")),
                }
                for r in hw_rows
            ],
            "behavior": [
                {
                    "id": r.id, "title": r.title, "type": r.type,
                    "severity": r.severity, "date": r.date,
                }
                for r in bh_rows
            ],
        }

    async def excused_leaves(self, student_id: str, limit: int = 30) -> list[dict]:
        rows = (
            await self.db.execute(
                select(ExcusedLeave)
                .where(ExcusedLeave.student_id == student_id)
                .order_by(ExcusedLeave.date.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "date": r.date,
                "exit_time": r.exit_time,
                "reason": r.reason,
                "guardian_name": r.guardian_name,
                "guardian_relation": r.guardian_relation,
            }
            for r in rows
        ]

    async def attachments(self, student_id: str) -> list[dict]:
        rows = (
            await self.db.execute(
                select(StudentAttachment)
                .where(StudentAttachment.student_id == student_id)
                .order_by(StudentAttachment.created_at.desc())
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "file_name": r.file_name,
                "file_url": r.file_url,
                "uploaded_by": r.uploaded_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
