"""Schedules web routes with full academic hierarchy support."""
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

# ============================================================
# استيراد الـ Schemas
# ============================================================
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)

# النماذج (للوصول المباشر عند الحاجة)
from app.models.schedules import Schedule, ScheduleEntry
from app.models.academics import Section, Subject, Grade, Stage, AcademicYear
from app.models.teachers import Teacher

router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دوال مساعدة مبسطة (تستخدم ScheduleService)
# ============================================================

async def get_hierarchy_data(
    db: AsyncSession,
    school_id: str,
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    جلب التسلسل الهرمي للبيانات باستخدام ScheduleService
    """
    try:
        service = ScheduleService(db)
        hierarchy = await service.get_full_hierarchy(
            school_id=school_id,
            year_id=year_id,
            stage_id=stage_id,
            grade_id=grade_id
        )
        return hierarchy
    except Exception as e:
        print(f"⚠️ Error in get_hierarchy_data: {str(e)}")
        traceback.print_exc()
        return {
            "years": [],
            "stages": [],
            "grades": [],
            "sections": [],
            "selected_year": year_id,
            "selected_stage": stage_id,
            "selected_grade": grade_id
        }


async def get_all_teachers(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب المعلمين باستخدام ScheduleService"""
    try:
        service = ScheduleService(db)
        return await service.get_all_teachers(school_id)
    except Exception as e:
        print(f"⚠️ Error in get_all_teachers: {str(e)}")
        return []


async def get_all_subjects(db: AsyncSession, school_id: str) -> List[Dict]:
    """جلب المواد باستخدام ScheduleService"""
    try:
        service = ScheduleService(db)
        return await service.get_all_subjects(school_id)
    except Exception as e:
        print(f"⚠️ Error in get_all_subjects: {str(e)}")
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
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    section_id: Optional[str] = None,
):
    """صفحة إنشاء جدول جديد مع التصفية المتدرجة"""
    try:
        print("=" * 50)
        print("📄 صفحة إنشاء جدول جديد")
        print(f"   user_id: {user.id}")
        print(f"   school_id: {user.school_id}")
        print(f"   year_id: {year_id}")
        print(f"   stage_id: {stage_id}")
        print(f"   grade_id: {grade_id}")
        print(f"   section_id: {section_id}")
        print("=" * 50)
        
        # ✅ جلب التسلسل الهرمي باستخدام ScheduleService
        service = ScheduleService(db)
        hierarchy = await service.get_full_hierarchy(
            school_id=user.school_id,
            year_id=year_id,
            stage_id=stage_id,
            grade_id=grade_id
        )
        
        # جلب المواد والمعلمين
        subjects = await service.get_all_subjects(user.school_id)
        teachers = await service.get_all_teachers(user.school_id)
        
        print(f"✅ تم جلب {len(hierarchy.get('years', []))} عام دراسي")
        print(f"✅ تم جلب {len(hierarchy.get('stages', []))} مرحلة")
        print(f"✅ تم جلب {len(hierarchy.get('grades', []))} صف")
        print(f"✅ تم جلب {len(hierarchy.get('sections', []))} شعبة")
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
                "years": hierarchy.get("years", []),
                "stages": hierarchy.get("stages", []),
                "grades": hierarchy.get("grades", []),
                "sections": hierarchy.get("sections", []),
                "subjects": subjects,
                "teachers": teachers,
                "teachers_json": teachers_json,
                "subjects_json": subjects_json,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
                "selected_section": section_id,
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
                "selected_year": None,
                "selected_stage": None,
                "selected_grade": None,
                "selected_section": None,
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
        hierarchy = await service.get_full_hierarchy(user.school_id)
        subjects = await service.get_all_subjects(user.school_id)
        teachers = await service.get_all_teachers(user.school_id)
        
        # تحويل البيانات إلى JSON
        teachers_json = json.dumps(teachers, ensure_ascii=False)
        subjects_json = json.dumps(subjects, ensure_ascii=False)
        
        return templates.TemplateResponse(
            "schedules/edit.html",
            {
                **ctx,
                "title": "تعديل جدول دراسي",
                "schedule": schedule,
                "years": hierarchy.get("years", []),
                "stages": hierarchy.get("stages", []),
                "grades": hierarchy.get("grades", []),
                "sections": hierarchy.get("sections", []),
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
# ✅ مسارات API للجداول
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
        content_type = request.headers.get("content-type", "")
        print(f"📥 Content-Type: {content_type}")
        
        body = await request.body()
        print(f"📦 Raw body length: {len(body)}")
        
        if "application/json" in content_type:
            # معالجة JSON
            data = await request.json()
            print(f"📦 JSON data received")
            schedule_data = ScheduleCreate(**data)
        else:
            # معالجة FormData
            form_data = await request.form()
            print(f"📦 FormData keys: {list(form_data.keys())}")
            
            # استخراج البيانات الأساسية
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
            
            # استخراج الحصص من FormData
            entries_dict = {}
            
            for key, value in form_data.items():
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
                
                elif key.startswith("entries[") and key.endswith("][subject_id]"):
                    match = re.search(r"entries\[(\d+)\]\[subject_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["subject_id"] = value
                
                elif key.startswith("entries[") and key.endswith("][teacher_id]"):
                    match = re.search(r"entries\[(\d+)\]\[teacher_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["teacher_id"] = value
                
                elif key.startswith("entries[") and key.endswith("][pair_id]"):
                    match = re.search(r"entries\[(\d+)\]\[pair_id\]", key)
                    if match:
                        row_id = int(match.group(1))
                        if row_id not in entries_dict:
                            entries_dict[row_id] = {}
                        entries_dict[row_id]["pair_id"] = value
            
            # إنشاء قائمة الحصص
            entries_list = []
            for row_id, entry_data in entries_dict.items():
                day = entry_data.get("day", 0)
                period = entry_data.get("period", 1)
                subject_id = entry_data.get("subject_id")
                teacher_id = entry_data.get("teacher_id")
                
                if (not subject_id or not teacher_id) and "pair_id" in entry_data and entry_data["pair_id"]:
                    pair_parts = entry_data["pair_id"].split("|")
                    if len(pair_parts) == 2:
                        subject_id = pair_parts[0]
                        teacher_id = pair_parts[1]
                
                if subject_id and teacher_id and subject_id != '' and teacher_id != '':
                    entries_list.append({
                        "day": day,
                        "period": period,
                        "subject_id": subject_id,
                        "teacher_id": teacher_id
                    })
            
            schedule_data = ScheduleCreate(
                name=name,
                year_id=year_id,
                stage_id=stage_id,
                grade_id=grade_id,
                section_id=section_id,
                is_active=is_active,
                entries=entries_list
            )
        
        if not schedule_data.entries:
            return JSONResponse(
                {"detail": "يجب إضافة حصة واحدة على الأقل مع اختيار المادة والمعلم"},
                status_code=422
            )
        
        print(f"✅ Total entries: {len(schedule_data.entries)}")
        
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
        return JSONResponse({"detail": str(e)}, status_code=422)
    except ValueError as e:
        await db.rollback()
        print(f"❌ Value error: {str(e)}")
        traceback.print_exc()
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        print(f"❌ Error creating schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


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
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        print(f"❌ Error updating schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=500)


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
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        print(f"❌ Error deleting schedule: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=500)


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
        return JSONResponse({"detail": str(e)}, status_code=404)
    except ValidationException as e:
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        print(f"❌ Error adding entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=500)


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
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        print(f"❌ Error updating entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=500)


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
        return JSONResponse({"detail": str(e)}, status_code=404)
    except Exception as e:
        print(f"❌ Error deleting entry: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=500)


# ============================================================
# مسارات التصحيح (Debug)
# ============================================================

@router.get("/debug/hierarchy")
async def debug_hierarchy(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
):
    """عرض التسلسل الهرمي للتصحيح"""
    try:
        service = ScheduleService(db)
        hierarchy = await service.get_full_hierarchy(
            school_id=user.school_id,
            year_id=year_id,
            stage_id=stage_id,
            grade_id=grade_id
        )
        
        return JSONResponse({
            "success": True,
            "hierarchy": hierarchy,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_hierarchy: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/data")
async def debug_schedule_data(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات الجداول للتصحيح"""
    try:
        service = ScheduleService(db)
        hierarchy = await service.get_full_hierarchy(user.school_id)
        subjects = await service.get_all_subjects(user.school_id)
        teachers = await service.get_all_teachers(user.school_id)
        schedules = await service.list_schedules(user.school_id)
        
        return JSONResponse({
            "years": hierarchy.get("years", []),
            "stages": hierarchy.get("stages", []),
            "grades": hierarchy.get("grades", []),
            "sections": hierarchy.get("sections", []),
            "subjects": subjects,
            "teachers": teachers,
            "schedules": schedules or [],
            "schedules_count": len(schedules) if schedules else 0,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_schedule_data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
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
        service = ScheduleService(db)
        teachers = await service.get_all_teachers(user.school_id)
        
        return JSONResponse({
            "total": len(teachers),
            "teachers": teachers,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_teachers: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/subjects")
async def debug_subjects(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات المواد للتصحيح"""
    try:
        service = ScheduleService(db)
        subjects = await service.get_all_subjects(user.school_id)
        
        return JSONResponse({
            "total": len(subjects),
            "subjects": subjects,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_subjects: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
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
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/check")
async def debug_check(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("schedules.view")),
    db: AsyncSession = Depends(get_db),
):
    """التحقق من البيانات المتاحة"""
    try:
        service = ScheduleService(db)
        result = await service.check_available_data(user.school_id)
        
        return JSONResponse({
            "success": True,
            "data": result,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_check: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )
