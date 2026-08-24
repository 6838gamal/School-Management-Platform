"""Attendance repositories."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import StudentAttendance, TeacherAttendance
from app.repositories.base import BaseRepository


class StudentAttendanceRepository(BaseRepository[StudentAttendance]):
    model = StudentAttendance

    async def get_by_student_date(self, student_id: str, date: str, period_id: str | None = None) -> StudentAttendance | None:
        stmt = select(StudentAttendance).where(StudentAttendance.student_id == student_id, StudentAttendance.date == date)
        if period_id:
            stmt = stmt.where(StudentAttendance.period_id == period_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_section_date(self, section_id: str, date: str) -> list[StudentAttendance]:
        result = await self.db.execute(
            select(StudentAttendance).where(
                StudentAttendance.section_id == section_id,
                StudentAttendance.date == date,
            )
        )
        return list(result.scalars().all())

    async def list_by_date(self, school_id: str, date: str) -> list[StudentAttendance]:
        result = await self.db.execute(
            select(StudentAttendance).where(
                StudentAttendance.school_id == school_id,
                StudentAttendance.date == date,
            )
        )
        return list(result.scalars().all())

    async def summary(self, school_id: str, date: str) -> dict:
        records = await self.list_by_date(school_id, date)
        total = len(records)
        present = sum(1 for r in records if r.status == "present")
        absent = sum(1 for r in records if r.status == "absent")
        late = sum(1 for r in records if r.status == "late")
        excused = sum(1 for r in records if r.status == "excused")
        rate = (present / total * 100) if total else 0
        return {"date": date, "total": total, "present": present, "absent": absent, "late": late, "excused": excused, "rate": round(rate, 1)}


class TeacherAttendanceRepository(BaseRepository[TeacherAttendance]):
    model = TeacherAttendance

    async def get_by_teacher_date(self, teacher_id: str, date: str) -> TeacherAttendance | None:
        result = await self.db.execute(
            select(TeacherAttendance).where(TeacherAttendance.teacher_id == teacher_id, TeacherAttendance.date == date)
        )
        return result.scalar_one_or_none()

    async def list_by_date(self, school_id: str, date: str) -> list[TeacherAttendance]:
        result = await self.db.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.school_id == school_id,
                TeacherAttendance.date == date,
            )
        )
        return list(result.scalars().all())

    async def absent_teachers(self, school_id: str, date: str) -> list[TeacherAttendance]:
        result = await self.db.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.school_id == school_id,
                TeacherAttendance.date == date,
                TeacherAttendance.status.in_(["absent", "leave"]),
            )
        )
        return list(result.scalars().all())
