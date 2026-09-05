"""Schedules web routes."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid
import traceback
import json
import re
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.schedule_service import ScheduleService
from app.core.exceptions import NotFoundException, AppException, ValidationException
from app.core.security import hash_password

# ============================================================
# استيراد الـ Schemas
# ============================================================
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)

# النماذج
from app.models.schedules import Schedule, ScheduleEntry
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear
from app.models.teachers import Teacher
from app.models.users import User, UserRole, Role

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة لجلب البيانات
# ============================================================

async def get_sections_with_details(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب الفصول مع تفاصيلها (الصف والمرحلة)"""
    try:
        result = await db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.grade_id, Section.name)
        )
        sections = result.scalars().all()
        
        return [
            {
                "id": str(section.id),
                "name": section.name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "grade_name": section.grade.name if section.grade else "غير محدد",
                "stage_name": section.grade.stage.name if section.grade and section.grade.stage else "غير محدد",
                "display_name": f"{section.grade.stage.name if section.grade and section.grade.stage else ''} - {section.grade.name if section.grade else ''} - {section.name}",
                "capacity": section.capacity,
                "is_active": section.is_active
            }
            for section in sections
        ]
    except Exception as e:
        print(f"⚠️ Error in get_sections_with_details: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def get_academic_years(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب السنوات الدراسية"""
    try:
        result = await db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .where(AcademicYear.is_active == True)
            .order_by(AcademicYear.start_date.desc())
        )
        years = result.scalars().all()
        
        return [
            {
                "id": str(year.id),
                "name": year.name,
                "start_date": year.start_date,
                "end_date": year.end_date,
                "is_current": year.is_current,
                "is_active": year.is_active
            }
            for year in years
        ]
    except Exception as e:
        print(f"⚠️ Error in get_academic_years: {str(e)}")
        return []


async def get_stages(db: AsyncSession, school_id: str, year_id: Optional[str] = None) -> List[Dict]:
    """جلب المراحل حسب السنة الدراسية"""
    try:
        stmt = select(Stage).where(Stage.school_id == school_id)
        if year_id:
            stmt = stmt.where(Stage.year_id == year_id)
        stmt = stmt.order_by(Stage.order)
        
        result = await db.execute(stmt)
        stages = result.scalars().all()
        
        return [
            {
                "id": str(stage.id),
                "name": stage.name,
                "name_en": stage.name_en,
                "year_id": str(stage.year_id) if stage.year_id else None,
                "order": stage.order
            }
            for stage in stages
        ]
    except Exception as e:
        print(f"⚠️ Error in get_stages: {str(e)}")
        return []


async def get_grades(db: AsyncSession, school_id: str, stage_id: Optional[str] = None) -> List[Dict]:
    """جلب الصفوف حسب المرحلة"""
    try:
        stmt = select(Grade).where(
            Grade.school_id == school_id,
            Grade.is_active == True
        )
        if stage_id:
            stmt = stmt.where(Grade.stage_id == stage_id)
        stmt = stmt.order_by(Grade.order)
        
        result = await db.execute(stmt)
        grades = result.scalars().all()
        
        return [
            {
                "id": str(grade.id),
                "name": grade.name,
                "name_en": grade.name_en,
                "stage_id": str(grade.stage_id) if grade.stage_id else None,
                "year_id": str(grade.year_id) if grade.year_id else None,
                "order": grade.order,
                "is_active": grade.is_active
            }
            for grade in grades
        ]
    except Exception as e:
        print(f"⚠️ Error in get_grades: {str(e)}")
        return []


async def get_subjects(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب المواد الدراسية"""
    try:
        result = await db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .where(Subject.is_active == True)
            .order_by(Subject.name)
        )
        subjects = result.scalars().all()
        
        return [
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code if hasattr(subject, 'code') else None,
                "color": subject.color if hasattr(subject, 'color') else None,
                "is_active": subject.is_active
            }
            for subject in subjects
        ]
    except Exception as e:
        print(f"⚠️ Error in get_subjects: {str(e)}")
        return []


async def get_teachers(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب المعلمين مع المواد التي يدرسونها"""
    try:
        result = await db.execute(
            select(Teacher)
            .where(Teacher.school_id == school_id)
            .where(Teacher.is_active == True)
            .order_by(Teacher.first_name, Teacher.last_name)
        )
        teachers = result.scalars().all()
        
        if not teachers:
            return []
        
        teachers_data = []
        for teacher in teachers:
            # جلب المواد التي يدرسها المعلم
            subject_ids = []
            subject_names = []
            
            # محاولة جلب المواد من علاقة teacher_subjects إذا كانت موجودة
            try:
                from app.models.teacher_subject import TeacherSubject
                subject_result = await db.execute(
                    select(Subject)
                    .join(TeacherSubject, TeacherSubject.subject_id == Subject.id)
                    .where(TeacherSubject.teacher_id == teacher.id)
                    .where(Subject.is_active == True)
                )
                subjects = subject_result.scalars().all()
                subject_ids = [str(s.id) for s in subjects]
                subject_names = [s.name for s in subjects]
            except Exception:
                # إذا لم يكن هناك جدول وسيط، نستخدم التخصص
                if teacher.specialization:
                    subject_result = await db.execute(
                        select(Subject)
                        .where(Subject.name == teacher.specialization)
                        .where(Subject.school_id == school_id)
                    )
                    subject = subject_result.scalar_one_or_none()
                    if subject:
                        subject_ids = [str(subject.id)]
                        subject_names = [subject.name]
                    else:
                        subject_ids = [teacher.specialization]
                        subject_names = [teacher.specialization]
            
            teachers_data.append({
                "id": str(teacher.id),
                "name": f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name,
                "full_name": f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name,
                "first_name": teacher.first_name,
                "last_name": teacher.last_name,
                "employee_number": teacher.employee_number,
                "email": teacher.email,
                "specialization": teacher.specialization,
                "subject_ids": subject_ids,
                "subject_names": subject_names,
                "subject_id": subject_ids[0] if subject_ids else None,
            })
        
        return teachers_data
    except Exception as e:
        print(f"⚠️ Error in get_teachers: {str(e)}")
        traceback.print_exc()
        return []


# ============================================================
# المسارات الرئيسية
# ============================================================

@router.get("")
async def schedules_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة الجداول الدراسية الرئيسية"""
    try:
        service = ScheduleService(db)
        schedules = await service.list_schedules(user.school_id)
        
        print(f"📊 Found {len(schedules) if schedules else 0} schedules")
        
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": schedules or [], 
                "type": "schedules",
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in schedules_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": [], 
                "type": "schedules",
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/list")
async def list_schedules(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة قائمة الجداول الدراسية"""
    try:
        service = ScheduleService(db)
        schedules = await service.list_schedules(user.school_id)
        
        if schedules is None:
            schedules = []
        
        print(f"📊 Found {len(schedules)} schedules in list")
        
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": schedules, 
                "type": "schedules",
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in list_schedules: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/list.html",
            {
                **ctx, 
                "title": "الجداول الدراسية", 
                "items": [], 
                "type": "schedules",
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/create")
async def create_schedule_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة إنشاء جدول جديد"""
    try:
        print("=" * 50)
        print("📄 صفحة إنشاء جدول جديد")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print("=" * 50)
        
        # جلب البيانات المطلوبة
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id)
        grades = await get_grades(db, user.school_id)
        sections = await get_sections_with_details(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        print(f"✅ تم جلب {len(years)} عام دراسي")
        print(f"✅ تم جلب {len(stages)} مرحلة")
        print(f"✅ تم جلب {len(grades)} صف")
        print(f"✅ تم جلب {len(sections)} شعبة")
        print(f"✅ تم جلب {len(subjects)} مادة")
        print(f"✅ تم جلب {len(teachers)} معلم")
        
        # تحويل البيانات إلى JSON للاستخدام في JavaScript
        teachers_json = json.dumps(teachers, ensure_ascii=False)
        subjects_json = json.dumps(subjects, ensure_ascii=False)
        
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "subjects": subjects,
                "teachers": teachers,
                "teachers_json": teachers_json,
                "subjects_json": subjects_json,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ خطأ في صفحة إنشاء الجدول: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "schedules/create.html",
            {
                **ctx,
                "title": "إنشاء جدول دراسي",
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "subjects": [],
                "teachers": [],
                "teachers_json": "[]",
                "subjects_json": "[]",
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


@router.get("/{schedule_id}")
async def view_schedule_page(
    request: Request,
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة عرض الجدول"""
    try:
        service = ScheduleService(db)
        schedule = await service.get_schedule_with_entries(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="الجدول غير موجود")
        
        # جلب أسماء المواد والمعلمين للعرض
        entries_data = []
        for entry in schedule.get("entries", []):
            # جلب المادة
            subject_name = None
            if entry.get("subject_id"):
                subject_result = await db.execute(
                    select(Subject).where(Subject.id == entry["subject_id"])
                )
                subject = subject_result.scalar_one_or_none()
                if subject:
                    subject_name = subject.name
            
            # جلب المعلم
            teacher_name = None
            if entry.get("teacher_id"):
                teacher_result = await db.execute(
                    select(Teacher).where(Teacher.id == entry["teacher_id"])
                )
                teacher = teacher_result.scalar_one_or_none()
                if teacher:
                    teacher_name = f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name
            
            entries_data.append({
                **entry,
                "subject_name": subject_name,
                "teacher_name": teacher_name,
            })
        
        schedule["entries"] = entries_data
        
        return templates.TemplateResponse(
            "schedules/view.html",
            {
                **ctx,
                "title": "عرض الجدول الدراسي",
                "schedule": schedule,
                "days": ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"],
                "periods": ["الحصة الأولى", "الحصة الثانية", "الحصة الثالثة", "الحصة الرابعة", "الحصة الخامسة", "الحصة السادسة"],
                "error": None
            }
        )
    except HTTPException:
        raise
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Error in view_schedule_page: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"حدث خطأ: {str(e)}")


@router.get("/{schedule_id}/edit")
async def edit_schedule_page(
    request: Request,
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """صفحة تعديل جدول"""
    try:
        service = ScheduleService(db)
        schedule = await service.get_schedule_with_entries(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="الجدول غير موجود")
        
        # جلب البيانات المطلوبة
        years = await get_academic_years(db, user.school_id)
        stages = await get_stages(db, user.school_id)
        grades = await get_grades(db, user.school_id)
        sections = await get_sections_with_details(db, user.school_id)
        subjects = await get_subjects(db, user.school_id)
        teachers = await get_teachers(db, user.school_id)
        
        # تحويل البيانات إلى JSON
        teachers_json = json.dumps(teachers, ensure_ascii=False)
        subjects_json = json.dumps(subjects, ensure_ascii=False)
        
        return templates.TemplateResponse(
            "schedules/edit.html",
            {
                **ctx,
                "title": "تعديل جدول دراسي",
                "schedule": schedule,
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "subjects": subjects,
                "teachers": teachers,
                "teachers_json": teachers_json,
                "subjects_json": subjects_json,
                "days": ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"],
                "periods": ["الحصة الأولى", "الحصة الثانية", "الحصة الثالثة", "الحصة الرابعة", "الحصة الخامسة", "الحصة السادسة"],
                "error": None
            }
        )
    except HTTPException:
        raise
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Error in edit_schedule_page: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"حدث خطأ: {str(e)}")


# ============================================================
# ✅ مسارات API للجداول (محدثة)
# ============================================================

@router.post("/api/v1/schedules")
async def create_schedule_api(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء جدول جديد عبر API
    يدعم كلاً من JSON و FormData
    """
    try:
        # قراءة البيانات
        content_type = request.headers.get("content-type", "")
        print(f"📥 Content-Type: {content_type}")
        
        # ✅ قراءة البيانات الخام
        body = await request.body()
        print(f"📦 Raw body length: {len(body)}")
        
        if "application/json" in content_type:
            # ✅ معالجة JSON
            data = await request.json()
            print(f"📦 JSON data received")
            
            # تحويل البيانات إلى Schema
            schedule_data = ScheduleCreate(**data)
            
        else:
            # ✅ معالجة FormData
            form_data = await request.form()
            print(f"📦 FormData keys: {list(form_data.keys())}")
            
            # ✅ استخراج البيانات الأساسية
            name = form_data.get("name")
            year_id = form_data.get("year_id")
            stage_id = form_data.get("stage_id")
            grade_id = form_data.get("grade_id")
            section_id = form_data.get("section_id")
            is_active = form_data.get("is_active") == "true"
            
            print(f"📝 name: {name}")
            print(f"📝 year_id: {year_id}")
            print(f"📝 stage_id: {stage_id}")
            print(f"📝 grade_id: {grade_id}")
            print(f"📝 section_id: {section_id}")
            print(f"📝 is_active: {is_active}")
            
            # ✅ استخراج الحصص من FormData
            entries_dict = {}
            
            for key, value in form_data.items():
                # استخراج day
                if key.startswith("entries[") and key.endswith("][day]"):
                    match = re.search(r"entries\[(\d+)\]\[day\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        try:
                            entries_dict[row_id]["day"] = int(value)
                        except ValueError:
                            entries_dict[row_id]["day"] = 0
                        print(f"   ✅ day[{row_id}] = {value}")
                
                # استخراج period
                elif key.startswith("entries[") and key.endswith("][period]"):
                    match = re.search(r"entries\[(\d+)\]\[period\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        try:
                            entries_dict[row_id]["period"] = int(value)
                        except ValueError:
                            entries_dict[row_id]["period"] = 1
                        print(f"   ✅ period[{row_id}] = {value}")
                
                # ✅ استخراج subject_id (من الحقل المخفي)
                elif key.startswith("entries[") and key.endswith("][subject_id]"):
                    match = re.search(r"entries\[(\d+)\]\[subject_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["subject_id"] = value
                        print(f"   ✅ subject_id[{row_id}] = {value}")
                
                # ✅ استخراج teacher_id (من الحقل المخفي)
                elif key.startswith("entries[") and key.endswith("][teacher_id]"):
                    match = re.search(r"entries\[(\d+)\]\[teacher_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["teacher_id"] = value
                        print(f"   ✅ teacher_id[{row_id}] = {value}")
                
                # استخراج pair_id (كاحتياطي)
                elif key.startswith("entries[") and key.endswith("][pair_id]"):
                    match = re.search(r"entries\[(\d+)\]\[pair_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["pair_id"] = value
                        print(f"   ✅ pair_id[{row_id}] = {value}")
            
            # ✅ إنشاء قائمة الحصص
            entries_list = []
            for row_id, entry_data in entries_dict.items():
                day = entry_data.get("day", 0)
                period = entry_data.get("period", 1)
                subject_id = entry_data.get("subject_id")
                teacher_id = entry_data.get("teacher_id")
                
                # ✅ إذا كان هناك pair_id فقط، استخراج subject_id و teacher_id منه
                if (not subject_id or not teacher_id) and "pair_id" in entry_data and entry_data["pair_id"]:
                    pair_parts = entry_data["pair_id"].split("|")
                    if len(pair_parts) == 2:
                        subject_id = pair_parts[0]
                        teacher_id = pair_parts[1]
                        print(f"   ✅ استخراج من pair_id: subject={subject_id}, teacher={teacher_id}")
                
                # ✅ إضافة الحصة إذا كانت البيانات مكتملة
                if subject_id and teacher_id and subject_id != '' and teacher_id != '':
                    entries_list.append({
                        "day": day,
                        "period": period,
                        "subject_id": subject_id,
                        "teacher_id": teacher_id
                    })
                    print(f"   ✅ Added entry: day={day}, period={period}, subject={subject_id}, teacher={teacher_id}")
                else:
                    print(f"   ⚠️ Skipping entry {row_id}: missing subject or teacher")
            
            # ✅ إنشاء كائن ScheduleCreate
            schedule_data = ScheduleCreate(
                name=name,
                year_id=year_id,
                stage_id=stage_id,
                grade_id=grade_id,
                section_id=section_id,
                is_active=is_active,
                entries=entries_list
            )
        
        # ✅ التحقق من وجود حصص
        if not schedule_data.entries:
            return JSONResponse(
                {"detail": "يجب إضافة حصة واحدة على الأقل مع اختيار المادة والمعلم"},
                status_code=422
            )
        
        print(f"✅ Total entries: {len(schedule_data.entries)}")
        
        # ✅ إنشاء الجدول
        service = ScheduleService(db)
        schedule = await service.create_schedule(user.school_id, schedule_data)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم إنشاء الجدول بنجاح",
            "id": str(schedule.id),
            "name": schedule.name,
            "entries_count": len(schedule_data.entries)
        }
        
    except ValidationException as e:
        await db.rollback()
        print(f"❌ Validation error: {str(e)}")
        return JSONResponse(
            {"detail": str(e)},
            status_code=422
        )
    except ValueError as e:
        await db.rollback()
        print(f"❌ Value error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"detail": str(e)},
            status_code=422
        )
    except Exception as e:
        print(f"❌ Error creating schedule: {str(e)}")
        import traceback
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": f"حدث خطأ: {str(e)}"},
            status_code=500
        )


@router.put("/api/v1/schedules/{schedule_id}")
async def update_schedule_api(
    schedule_id: str,
    req: ScheduleUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث جدول عبر API"""
    try:
        service = ScheduleService(db)
        schedule = await service.update_schedule(schedule_id, req)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تحديث الجدول بنجاح",
            "id": str(schedule.id)
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error updating schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.delete("/api/v1/schedules/{schedule_id}")
async def delete_schedule_api(
    schedule_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف جدول عبر API"""
    try:
        service = ScheduleService(db)
        await service.delete_schedule(schedule_id)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم حذف الجدول بنجاح"
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error deleting schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.post("/api/v1/schedules/{schedule_id}/entries")
async def add_entry_api(
    schedule_id: str,
    req: ScheduleEntryCreate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """إضافة حصة جديدة إلى الجدول عبر API"""
    try:
        service = ScheduleService(db)
        entry = await service.add_entry(schedule_id, req)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم إضافة الحصة بنجاح",
            "id": str(entry.id)
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except ValidationException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=422
        )
    except Exception as e:
        print(f"❌ Error adding entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.put("/api/v1/entries/{entry_id}")
async def update_entry_api(
    entry_id: str,
    req: ScheduleEntryUpdate,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث حصة في الجدول عبر API"""
    try:
        service = ScheduleService(db)
        entry = await service.update_entry(entry_id, req)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تحديث الحصة بنجاح",
            "id": str(entry.id)
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error updating entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


@router.delete("/api/v1/entries/{entry_id}")
async def delete_entry_api(
    entry_id: str,
    user: CurrentUser = Depends(require_any_permission("schedules.update")),
    db: AsyncSession = Depends(get_db),
):
    """حذف حصة من الجدول عبر API"""
    try:
        service = ScheduleService(db)
        await service.delete_entry(entry_id)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم حذف الحصة بنجاح"
        }
        
    except NotFoundException as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=404
        )
    except Exception as e:
        print(f"❌ Error deleting entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse(
            {"detail": str(e)},
            status_code=500
        )


# ============================================================
# مسارات التصحيح
# ============================================================

@router.get("/debug/data")
async def debug_schedule_data(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات الجداول للتصحيح"""
    try:
        result = {
            "years": await get_academic_years(db, user.school_id),
            "stages": await get_stages(db, user.school_id),
            "grades": await get_grades(db, user.school_id),
            "sections": await get_sections_with_details(db, user.school_id),
            "subjects": await get_subjects(db, user.school_id),
            "teachers": await get_teachers(db, user.school_id),
        }
        
        # جلب الجداول الموجودة
        try:
            service = ScheduleService(db)
            schedules = await service.list_schedules(user.school_id)
            result["schedules"] = schedules or []
            result["schedules_count"] = len(schedules) if schedules else 0
        except Exception as e:
            result["schedules_error"] = str(e)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"❌ Error in debug_schedule_data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            status_code=500
        )


@router.get("/debug/teachers")
async def debug_teachers(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات المعلمين للتصحيح"""
    try:
        teachers = await get_teachers(db, user.school_id)
        
        return JSONResponse({
            "total": len(teachers),
            "teachers": teachers,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_teachers: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            status_code=500
        )


@router.get("/debug/schedules")
async def debug_schedules(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض الجداول للتصحيح"""
    try:
        service = ScheduleService(db)
        schedules = await service.list_schedules(user.school_id)
        
        return JSONResponse({
            "count": len(schedules) if schedules else 0,
            "schedules": schedules or [],
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_schedules: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            status_code=500
        )
