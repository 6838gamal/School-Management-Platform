"""Attendance service for students and teachers."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.repositories.attendance import StudentAttendanceRepository, TeacherAttendanceRepository
from app.schemas.attendance import StudentAttendanceBatch, StudentAttendanceCreate, TeacherAttendanceCreate


class AttendanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.student_att = StudentAttendanceRepository(db)
        self.teacher_att = TeacherAttendanceRepository(db)

    async def record_student(self, school_id: str, user_id: str, req: StudentAttendanceCreate) -> dict:
        existing = await self.student_att.get_by_student_date(req.student_id, req.date, req.period_id)
        if existing:
            existing.status = req.status
            existing.note = req.note
            existing.recorded_by = user_id
            await self.db.flush()
            return {"id": existing.id}
        record = await self.student_att.create(
            school_id=school_id,
            student_id=req.student_id,
            section_id=req.section_id,
            period_id=req.period_id,
            schedule_entry_id=req.schedule_entry_id,
            date=req.date,
            status=req.status,
            note=req.note,
            recorded_by=user_id,
        )
        return {"id": record.id}

    async def batch_record(self, school_id: str, user_id: str, req: StudentAttendanceBatch) -> dict:
        count = 0
        for r in req.records:
            student_id = r.get("student_id")
            status = r.get("status")
            if not student_id or not status:
                continue
            note = r.get("note")
            existing = await self.student_att.get_by_student_date(student_id, req.date, req.period_id)
            if existing:
                existing.status = status
                existing.note = note
                existing.recorded_by = user_id
            else:
                await self.student_att.create(
                    school_id=school_id,
                    student_id=student_id,
                    section_id=req.section_id,
                    period_id=req.period_id,
                    date=req.date,
                    status=status,
                    note=note,
                    recorded_by=user_id,
                )
            count += 1
        await self.db.flush()
        return {"recorded": count}

    async def record_teacher(self, school_id: str, user_id: str, req: TeacherAttendanceCreate) -> dict:
        existing = await self.teacher_att.get_by_teacher_date(req.teacher_id, req.date)
        if existing:
            existing.status = req.status
            existing.note = req.note
            existing.recorded_by = user_id
            await self.db.flush()
            return {"id": existing.id}
        record = await self.teacher_att.create(
            school_id=school_id,
            teacher_id=req.teacher_id,
            date=req.date,
            status=req.status,
            note=req.note,
            recorded_by=user_id,
        )
        return {"id": record.id}

    async def student_summary(self, school_id: str, date: str) -> dict:
        return await self.student_att.summary(school_id, date)

    async def absent_teachers(self, school_id: str, date: str) -> list[dict]:
        records = await self.teacher_att.absent_teachers(school_id, date)
        return [{"teacher_id": r.teacher_id, "status": r.status, "note": r.note} for r in records]

    async def section_attendance(self, section_id: str, date: str) -> list[dict]:
        records = await self.student_att.list_by_section_date(section_id, date)
        return [{"student_id": r.student_id, "status": r.status, "note": r.note} for r in records]
