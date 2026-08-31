"""Deputy dashboard — يجمع معلومات الفصول والحضور وحالة المعلمين في يوم واحد."""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import (
    AcademicYear,
    Grade,
    Section,
    Stage,
)
from app.models.attendance import StudentAttendance
from app.models.schedules import Schedule, ScheduleEntry
from app.models.session_lifecycle import SessionLifecycle
from app.models.students import StudentEnrollment
from app.models.teachers import Teacher
from app.services.session_lifecycle_service import INDICATOR_COLORS


DAY_NAMES_AR = [
    "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت",
]


class DeputyDashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def dashboard(
        self, *, school_id: str, target_date: Optional[str] = None
    ) -> dict:
        target_date = target_date or _date.today().isoformat()
        # 1) Sections (الترتيب: من اليمين لليسار: grade ثم section)
        sections_rows = (
            await self.db.execute(
                select(Section, Grade, Stage)
                .join(Grade, Grade.id == Section.grade_id)
                .join(Stage, Stage.id == Grade.stage_id)
                .where(Section.school_id == school_id, Section.is_active == True)
                .order_by(Stage.order, Grade.order, Section.name)
            )
        ).all()

        section_cards: list[dict] = []
        for section, grade, stage in sections_rows:
            # current enrollment count
            enrolled = (
                await self.db.scalar(
                    select(func.count(distinct(StudentEnrollment.student_id))).where(
                        StudentEnrollment.section_id == section.id,
                        StudentEnrollment.status == "active",
                    )
                )
            ) or 0

            # scheduled periods today
            pydate = _date.fromisoformat(target_date)
            dow = pydate.weekday()  # 0 = Monday; convert to 0..6 starting Sun
            day_of_week = (pydate.weekday() + 1) % 7  # Sunday=0
            period_rows = (
                await self.db.execute(
                    select(ScheduleEntry)
                    .join(Schedule, Schedule.id == ScheduleEntry.schedule_id)
                    .where(
                        Schedule.section_id == section.id,
                        Schedule.is_active == True,
                        ScheduleEntry.day_of_week == day_of_week,
                    )
                    .order_by(ScheduleEntry.period_id)
                )
            ).scalars().all()

            period_cards: list[dict] = []
            for entry in period_rows:
                teacher = (
                    await self.db.execute(
                        select(Teacher).where(Teacher.id == entry.teacher_id)
                    )
                ).scalar_one_or_none()
                lifecycle = (
                    await self.db.execute(
                        select(SessionLifecycle).where(
                            SessionLifecycle.schedule_entry_id == entry.id,
                            SessionLifecycle.date == target_date,
                        )
                    )
                ).scalar_one_or_none()
                status = lifecycle.status if lifecycle else "scheduled"
                indicator, label = INDICATOR_COLORS.get(status, ("⚪", status))
                period_cards.append(
                    {
                        "schedule_entry_id": entry.id,
                        "period_id": entry.period_id,
                        "subject_id": entry.subject_id,
                        "teacher_id": entry.teacher_id,
                        "teacher_name": teacher.full_name if teacher else "—",
                        "status": status,
                        "indicator": indicator,
                        "status_label": label,
                    }
                )

            section_cards.append(
                {
                    "section_id": section.id,
                    "section_name": section.name,
                    "grade_name": grade.name,
                    "stage_name": stage.name,
                    "enrolled_count": int(enrolled),
                    "periods_today": period_cards,
                }
            )

        # 2) Attendance analytics — present/absent/late/excused/other for the day
        # status values we accept per spec: present, absent, late, excused, holiday
        summary_rows = (
            await self.db.execute(
                select(StudentAttendance.status, func.count(StudentAttendance.id))
                .where(
                    StudentAttendance.school_id == school_id,
                    StudentAttendance.date == target_date,
                )
                .group_by(StudentAttendance.status)
            )
        ).all()
        counts = {s: int(c) for s, c in summary_rows}
        total_records = sum(counts.values())
        late_arrivals_count = (
            await self.db.scalar(
                select(func.count(StudentAttendance.id)).where(
                    StudentAttendance.school_id == school_id,
                    StudentAttendance.date == target_date,
                    StudentAttendance.status == "late",
                )
            )
        ) or 0
        excused_count = counts.get("excused", 0)
        other_count = total_records - (
            counts.get("present", 0)
            + counts.get("absent", 0)
            + counts.get("late", 0)
            + counts.get("excused", 0)
        )

        return {
            "date": target_date,
            "day_name": DAY_NAMES_AR[(int(target_date.split("-")[2]) % 7)],  # placeholder
            "sections": section_cards,        # ترتيب من اليمين لليسار في القالب
            "analytics": {
                "present": counts.get("present", 0),
                "absent": counts.get("absent", 0),
                "late": counts.get("late", 0),
                "late_arrivals": late_arrivals_count,
                "excused": excused_count,
                "other": other_count,
                "total_records": total_records,
            },
        }
