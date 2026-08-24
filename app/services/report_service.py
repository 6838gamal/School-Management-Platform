"""Dashboard and reports service."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_report_link_token
from app.repositories.academics import SectionRepository, SubjectRepository
from app.repositories.activities import ActivityRepository, BehaviorRecordRepository
from app.repositories.attendance import StudentAttendanceRepository, TeacherAttendanceRepository
from app.repositories.notifications import NotificationRecipientRepository, ReportLinkRepository
from app.repositories.schedules import ScheduleEntryRepository
from app.repositories.students import StudentRepository
from app.repositories.teachers import TeacherRepository


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.students = StudentRepository(db)
        self.teachers = TeacherRepository(db)
        self.sections = SectionRepository(db)
        self.subjects = SubjectRepository(db)
        self.student_att = StudentAttendanceRepository(db)
        self.teacher_att = TeacherAttendanceRepository(db)
        self.entries = ScheduleEntryRepository(db)
        self.activities = ActivityRepository(db)
        self.behavior = BehaviorRecordRepository(db)
        self.notif_recipients = NotificationRecipientRepository(db)

    async def director_stats(self, school_id: str, user_id: str) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        students, total_students = await self.students.list_by_school(school_id, page=1, page_size=1)
        teachers, total_teachers = await self.teachers.list_by_school(school_id, page=1, page_size=1)
        sections = await self.sections.list_by_school(school_id)
        subjects = await self.subjects.list_by_school(school_id)
        att_summary = await self.student_att.summary(school_id, today)
        absent_teachers = await self.teacher_att.absent_teachers(school_id, today)
        affected = 0
        for at in absent_teachers:
            entries = await self.entries.list_by_teacher(at.teacher_id)
            affected += sum(1 for e in entries if e.day_of_week == datetime.now(timezone.utc).weekday())
        activities = await self.activities.list_by_school(school_id, status="upcoming")
        recent_behavior = await self.behavior.list_by_school(school_id, limit=5)
        unread = await self.notif_recipients.unread_count(user_id)
        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_sections": len(sections),
            "total_subjects": len(subjects),
            "attendance_today": att_summary,
            "absent_teachers_count": len(absent_teachers),
            "affected_lessons": affected,
            "upcoming_activities": len(activities),
            "recent_behavior_count": len(recent_behavior),
            "unread_notifications": unread,
        }

    async def teacher_stats(self, school_id: str, teacher_id: str, user_id: str) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entries = await self.entries.list_by_teacher(teacher_id)
        today_entries = [e for e in entries if e.day_of_week == datetime.now(timezone.utc).weekday()]
        unread = await self.notif_recipients.unread_count(user_id)
        return {
            "today_lessons": len(today_entries),
            "total_lessons": len(entries),
            "unread_notifications": unread,
        }

    async def deputy_stats(self, school_id: str, user_id: str) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        teachers, total_teachers = await self.teachers.list_by_school(school_id, page=1, page_size=1)
        absent_teachers = await self.teacher_att.absent_teachers(school_id, today)
        affected = 0
        for at in absent_teachers:
            entries = await self.entries.list_by_teacher(at.teacher_id)
            affected += sum(1 for e in entries if e.day_of_week == datetime.now(timezone.utc).weekday())
        unread = await self.notif_recipients.unread_count(user_id)
        return {
            "total_teachers": total_teachers,
            "absent_teachers": len(absent_teachers),
            "affected_lessons": affected,
            "unread_notifications": unread,
        }

    async def activities_manager_stats(self, school_id: str, user_id: str) -> dict:
        activities = await self.activities.list_by_school(school_id)
        upcoming = [a for a in activities if a.status == "upcoming"]
        ongoing = [a for a in activities if a.status == "ongoing"]
        recent_behavior = await self.behavior.list_by_school(school_id, limit=10)
        unread = await self.notif_recipients.unread_count(user_id)
        return {
            "total_activities": len(activities),
            "upcoming_activities": len(upcoming),
            "ongoing_activities": len(ongoing),
            "recent_behavior_count": len(recent_behavior),
            "unread_notifications": unread,
        }


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.links = ReportLinkRepository(db)
        self.students = StudentRepository(db)
        self.teachers = TeacherRepository(db)
        self.student_att = StudentAttendanceRepository(db)
        self.behavior = BehaviorRecordRepository(db)
        self.activities = ActivityRepository(db)

    async def generate_link(self, school_id: str, user_id: str, report_type: str, parameters: dict) -> dict:
        import json
        from datetime import timedelta
        token = generate_report_link_token(report_id=report_type)
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        link = await self.links.create(
            school_id=school_id,
            token=token,
            report_type=report_type,
            parameters=json.dumps(parameters),
            expires_at=expires,
            created_by=user_id,
            is_active=True,
        )
        return {"id": link.id, "token": token, "expires_at": expires}

    async def students_report(self, school_id: str) -> list[dict]:
        items, _ = await self.students.list_by_school(school_id, page=1, page_size=1000)
        return [
            {"student_number": s.student_number, "full_name": f"{s.first_name} {s.last_name}", "gender": s.gender, "is_active": s.is_active}
            for s in items
        ]

    async def attendance_report(self, school_id: str, date: str) -> dict:
        return await self.student_att.summary(school_id, date)

    async def teachers_report(self, school_id: str) -> list[dict]:
        items, _ = await self.teachers.list_by_school(school_id, page=1, page_size=1000)
        return [
            {"employee_number": t.employee_number, "full_name": f"{t.first_name} {t.last_name}", "specialization": t.specialization}
            for t in items
        ]

    async def behavior_report(self, school_id: str) -> list[dict]:
        items = await self.behavior.list_by_school(school_id, limit=100)
        return [
            {"student_id": r.student_id, "type": r.type, "severity": r.severity, "title": r.title, "date": r.date}
            for r in items
        ]

    async def activities_report(self, school_id: str) -> list[dict]:
        items = await self.activities.list_by_school(school_id)
        return [
            {"id": a.id, "title": a.title, "status": a.status, "start_date": a.start_date}
            for a in items
        ]
