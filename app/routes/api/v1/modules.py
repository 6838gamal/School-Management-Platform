"""Academic structure, attendance, grades, schedules, homework, activities, behavior, notifications, reports API v1."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.schemas.academics import (
    AcademicYearCreate, GradeCreate, PeriodCreate, RoomCreate,
    SectionCreate, StageCreate, SubjectCreate,
)
from app.schemas.activities import ActivityCreate, ActivityUpdate, ParticipantAdd
from app.schemas.attendance import StudentAttendanceBatch, StudentAttendanceCreate, TeacherAttendanceCreate
from app.schemas.behavior import BehaviorCategoryCreate, BehaviorRecordCreate, BehaviorRecordUpdate
from app.schemas.grades import AssessmentCreate, AssessmentUpdate, GradeRecordBatch, GradeRecordCreate
from app.schemas.homework import HomeworkCreate, HomeworkUpdate, SubmissionUpdate
from app.schemas.notifications import NotificationCreate
from app.schemas.schedules import ScheduleEntryCreate, ScheduleEntryUpdate
from app.services.academic_service import AcademicService
from app.services.activity_service import ActivityService, BehaviorService
from app.services.attendance_service import AttendanceService
from app.services.grade_service import GradeService
from app.services.homework_service import HomeworkService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.services.schedule_service import ScheduleService

# ------------------------------------------------------------------
# Academics
# ------------------------------------------------------------------
academics_router = APIRouter(prefix="/academics", tags=["academics"])


@academics_router.get("/tree")
async def academic_tree(
    user: CurrentUser = Depends(require_permission("academics.view")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.get_full_tree(user.school_id)


@academics_router.post("/years")
async def create_year(
    req: AcademicYearCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_year(user.school_id, req)


@academics_router.post("/stages")
async def create_stage(
    req: StageCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_stage(user.school_id, req)


@academics_router.post("/grades")
async def create_grade(
    req: GradeCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_grade(user.school_id, req)


@academics_router.post("/sections")
async def create_section(
    req: SectionCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_section(user.school_id, req)


@academics_router.post("/subjects")
async def create_subject(
    req: SubjectCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_subject(user.school_id, req)


@academics_router.post("/rooms")
async def create_room(
    req: RoomCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_room(user.school_id, req)


@academics_router.post("/periods")
async def create_period(
    req: PeriodCreate,
    user: CurrentUser = Depends(require_permission("academics.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AcademicService(db)
    return await service.create_period(user.school_id, req)


# ------------------------------------------------------------------
# Attendance
# ------------------------------------------------------------------
attendance_router = APIRouter(prefix="/attendance", tags=["attendance"])


@attendance_router.post("/student")
async def record_student(
    req: StudentAttendanceCreate,
    user: CurrentUser = Depends(require_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AttendanceService(db)
    return await service.record_student(user.school_id, user.id, req)


@attendance_router.post("/student/batch")
async def batch_record(
    req: StudentAttendanceBatch,
    user: CurrentUser = Depends(require_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AttendanceService(db)
    return await service.batch_record(user.school_id, user.id, req)


@attendance_router.post("/teacher")
async def record_teacher(
    req: TeacherAttendanceCreate,
    user: CurrentUser = Depends(require_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    service = AttendanceService(db)
    return await service.record_teacher(user.school_id, user.id, req)


@attendance_router.get("/summary")
async def attendance_summary(
    date: str = Query(...),
    user: CurrentUser = Depends(require_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
):
    service = AttendanceService(db)
    return await service.student_summary(user.school_id, date)


# ------------------------------------------------------------------
# Grades
# ------------------------------------------------------------------
grades_router = APIRouter(prefix="/grades", tags=["grades"])


@grades_router.post("/assessments")
async def create_assessment(
    req: AssessmentCreate,
    user: CurrentUser = Depends(require_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.create_assessment(user.school_id, req)


@grades_router.put("/assessments/{assessment_id}")
async def update_assessment(
    assessment_id: str,
    req: AssessmentUpdate,
    user: CurrentUser = Depends(require_permission("grades.update")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.update_assessment(assessment_id, req)


@grades_router.get("/assessments/section/{section_id}")
async def list_assessments(
    section_id: str,
    user: CurrentUser = Depends(require_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.list_assessments(section_id)


@grades_router.post("/record")
async def record_grade(
    req: GradeRecordCreate,
    user: CurrentUser = Depends(require_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.record_grade(user.id, req)


@grades_router.post("/batch")
async def batch_grades(
    req: GradeRecordBatch,
    user: CurrentUser = Depends(require_permission("grades.create")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.batch_record(user.id, req)


@grades_router.get("/student/{student_id}")
async def student_grades(
    student_id: str,
    user: CurrentUser = Depends(require_permission("grades.view")),
    db: AsyncSession = Depends(get_db),
):
    service = GradeService(db)
    return await service.student_grades(student_id)


# ------------------------------------------------------------------
# Schedules
# ------------------------------------------------------------------
schedules_router = APIRouter(prefix="/schedules", tags=["schedules"])


@schedules_router.get("/{schedule_id}/grid")
async def get_grid(
    schedule_id: str,
    user: CurrentUser = Depends(require_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.get_weekly_grid(schedule_id)


@schedules_router.post("/{schedule_id}/entries")
async def add_entry(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.add_entry(user.school_id, schedule_id, req)


@schedules_router.put("/entries/{entry_id}")
async def update_entry(
    entry_id: str,
    req: ScheduleEntryUpdate,
    user: CurrentUser = Depends(require_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.update_entry(entry_id, req)


@schedules_router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    user: CurrentUser = Depends(require_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    await service.delete_entry(entry_id)
    return {"message": "تم الحذف"}


@schedules_router.get("/replacements/{teacher_id}")
async def suggest_replacements(
    teacher_id: str,
    date: str = Query(...),
    user: CurrentUser = Depends(require_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.suggest_replacements(user.school_id, teacher_id, date)


# ------------------------------------------------------------------
# Homework
# ------------------------------------------------------------------
homework_router = APIRouter(prefix="/homework", tags=["homework"])


@homework_router.post("")
async def create_homework(
    req: HomeworkCreate,
    user: CurrentUser = Depends(require_permission("homework.create")),
    db: AsyncSession = Depends(get_db),
):
    service = HomeworkService(db)
    return await service.create(user.school_id, req)


@homework_router.put("/{homework_id}")
async def update_homework(
    homework_id: str,
    req: HomeworkUpdate,
    user: CurrentUser = Depends(require_permission("homework.update")),
    db: AsyncSession = Depends(get_db),
):
    service = HomeworkService(db)
    return await service.update(homework_id, req)


@homework_router.delete("/{homework_id}")
async def delete_homework(
    homework_id: str,
    user: CurrentUser = Depends(require_permission("homework.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = HomeworkService(db)
    await service.delete(homework_id)
    return {"message": "تم الحذف"}


@homework_router.get("/section/{section_id}")
async def list_homework(
    section_id: str,
    user: CurrentUser = Depends(require_permission("homework.view")),
    db: AsyncSession = Depends(get_db),
):
    service = HomeworkService(db)
    return await service.list_by_section(section_id)


@homework_router.put("/{homework_id}/submission/{student_id}")
async def update_submission(
    homework_id: str,
    student_id: str,
    req: SubmissionUpdate,
    user: CurrentUser = Depends(require_permission("homework.update")),
    db: AsyncSession = Depends(get_db),
):
    service = HomeworkService(db)
    return await service.update_submission(homework_id, student_id, req)


# ------------------------------------------------------------------
# Activities
# ------------------------------------------------------------------
activities_router = APIRouter(prefix="/activities", tags=["activities"])


@activities_router.get("")
async def list_activities(
    status: str = "",
    user: CurrentUser = Depends(require_permission("activities.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.list_activities(user.school_id, status or None)


@activities_router.post("")
async def create_activity(
    req: ActivityCreate,
    user: CurrentUser = Depends(require_permission("activities.create")),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.create(user.school_id, req)


@activities_router.put("/{activity_id}")
async def update_activity(
    activity_id: str,
    req: ActivityUpdate,
    user: CurrentUser = Depends(require_permission("activities.update")),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.update(activity_id, req)


@activities_router.delete("/{activity_id}")
async def delete_activity(
    activity_id: str,
    user: CurrentUser = Depends(require_permission("activities.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    await service.delete(activity_id)
    return {"message": "تم الحذف"}


@activities_router.post("/{activity_id}/participants")
async def add_participant(
    activity_id: str,
    req: ParticipantAdd,
    user: CurrentUser = Depends(require_permission("activities.update")),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.add_participant(req)


# ------------------------------------------------------------------
# Behavior
# ------------------------------------------------------------------
behavior_router = APIRouter(prefix="/behavior", tags=["behavior"])


@behavior_router.get("/categories")
async def list_categories(
    user: CurrentUser = Depends(require_permission("behavior.view")),
    db: AsyncSession = Depends(get_db),
):
    service = BehaviorService(db)
    return await service.list_categories(user.school_id)


@behavior_router.post("/categories")
async def create_category(
    req: BehaviorCategoryCreate,
    user: CurrentUser = Depends(require_permission("behavior.create")),
    db: AsyncSession = Depends(get_db),
):
    service = BehaviorService(db)
    return await service.create_category(user.school_id, req)


@behavior_router.post("/records")
async def create_record(
    req: BehaviorRecordCreate,
    user: CurrentUser = Depends(require_permission("behavior.create")),
    db: AsyncSession = Depends(get_db),
):
    service = BehaviorService(db)
    return await service.create_record(user.school_id, user.id, req)


@behavior_router.put("/records/{record_id}")
async def update_record(
    record_id: str,
    req: BehaviorRecordUpdate,
    user: CurrentUser = Depends(require_permission("behavior.update")),
    db: AsyncSession = Depends(get_db),
):
    service = BehaviorService(db)
    return await service.update_record(record_id, req)


@behavior_router.get("/student/{student_id}")
async def student_records(
    student_id: str,
    user: CurrentUser = Depends(require_permission("behavior.view")),
    db: AsyncSession = Depends(get_db),
):
    service = BehaviorService(db)
    return await service.student_records(student_id)


# ------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("")
async def list_notifications(
    unread_only: bool = False,
    user: CurrentUser = Depends(require_permission("notifications.view")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.list_for_user(user.id, unread_only)


@notifications_router.get("/unread-count")
async def unread_count(
    user: CurrentUser = Depends(require_permission("notifications.view")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return {"count": await service.unread_count(user.id)}


@notifications_router.post("")
async def send_notification(
    req: NotificationCreate,
    user: CurrentUser = Depends(require_permission("notifications.create")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.send(user.school_id, user.id, req)


@notifications_router.put("/{recipient_id}/read")
async def mark_read(
    recipient_id: str,
    user: CurrentUser = Depends(require_permission("notifications.view")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.mark_read(recipient_id)


@notifications_router.put("/read-all")
async def mark_all_read(
    user: CurrentUser = Depends(require_permission("notifications.view")),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.mark_all_read(user.id)


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------
reports_router = APIRouter(prefix="/reports", tags=["reports"])


@reports_router.post("/generate-link")
async def generate_link(
    report_type: str = Query(...),
    user: CurrentUser = Depends(require_permission("reports.share")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.generate_link(user.school_id, user.id, report_type, {})


@reports_router.get("/students")
async def students_report(
    user: CurrentUser = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.students_report(user.school_id)


@reports_router.get("/attendance")
async def attendance_report(
    date: str = Query(...),
    user: CurrentUser = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.attendance_report(user.school_id, date)


@reports_router.get("/teachers")
async def teachers_report(
    user: CurrentUser = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.teachers_report(user.school_id)


@reports_router.get("/behavior")
async def behavior_report(
    user: CurrentUser = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.behavior_report(user.school_id)


@reports_router.get("/activities")
async def activities_report(
    user: CurrentUser = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.activities_report(user.school_id)
