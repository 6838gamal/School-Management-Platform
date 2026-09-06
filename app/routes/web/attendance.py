"""Attendance web routes with full academic hierarchy - Like schedules module."""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Dict, Any
import uuid
import traceback
import json
import re
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.attendance_service import AttendanceService
from app.core.exceptions import NotFoundException, AppException, ValidationException

# ============================================================
# استيراد الـ Schemas
# ============================================================
from app.schemas.attendance import (
    StudentAttendanceCreate,
    StudentAttendanceBatch,
    StudentAttendanceStatus,
    TeacherAttendanceCreate,
    TeacherAttendanceStatus,
)

# النماذج
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.students import Student
from app.models.teachers import Teacher

router = APIRouter(prefix="/attendance", tags=["attendance"])
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 1️⃣ الصفحة الرئيسية للحضور
# ============================================================

@router.get("")
async def attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """الصفحة الرئيسية للحضور"""
    try:
        service = AttendanceService(db)
        
        # ✅ جلب التسلسل الهرمي الكامل
        hierarchy = await service.get_full_hierarchy(user.school_id)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        print("=" * 50)
        print("📊 الصفحة الرئيسية للحضور")
        print(f"   years: {len(hierarchy.get('years', []))}")
        print(f"   stages: {len(hierarchy.get('stages', []))}")
        print(f"   grades: {len(hierarchy.get('grades', []))}")
        print(f"   sections: {len(hierarchy.get('sections', []))}")
        print("=" * 50)
        
        return templates.TemplateResponse(
            "attendance/index.html",
            {
                **ctx,
                "title": "الحضور والغياب",
                "years": hierarchy.get("years", []),
                "stages": hierarchy.get("stages", []),
                "grades": hierarchy.get("grades", []),
                "sections": hierarchy.get("sections", []),
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/index.html",
            {
                **ctx,
                "title": "الحضور والغياب",
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 2️⃣ قائمة حضور الطلاب (مع التصفية المتدرجة)
# ============================================================

@router.get("/students")
async def student_attendance_list(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    date: Optional[str] = None,
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    section_id: Optional[str] = None,
    period_id: Optional[str] = None,
):
    """عرض قائمة حضور الطلاب مع التصفية المتدرجة"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        print("=" * 50)
        print("📊 صفحة حضور الطلاب (قائمة)")
        print(f"   date: {selected_date}")
        print(f"   year_id: {year_id}")
        print(f"   stage_id: {stage_id}")
        print(f"   grade_id: {grade_id}")
        print(f"   section_id: {section_id}")
        print("=" * 50)
        
        service = AttendanceService(db)
        
        # ✅ جلب التسلسل الهرمي الكامل مع التصفية
        hierarchy = await service.get_full_hierarchy(
            school_id=user.school_id,
            year_id=year_id,
            stage_id=stage_id,
            grade_id=grade_id
        )
        
        # ✅ جلب جميع البيانات للقوائم المنسدلة (حتى بدون تصفية)
        all_hierarchy = await service.get_full_hierarchy(user.school_id)
        
        # ✅ جلب all_stages و all_sections للـ JavaScript
        all_stages = all_hierarchy.get("stages", [])
        all_sections = all_hierarchy.get("sections", [])
        
        print(f"📊 hierarchy keys: {hierarchy.keys()}")
        print(f"   years: {len(hierarchy.get('years', []))}")
        print(f"   stages: {len(hierarchy.get('stages', []))}")
        print(f"   grades: {len(hierarchy.get('grades', []))}")
        print(f"   sections: {len(hierarchy.get('sections', []))}")
        print(f"   all_stages: {len(all_stages)}")
        print(f"   all_sections: {len(all_sections)}")
        
        # جلب سجلات الحضور
        records = []
        summary = {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0}
        section_name = None
        
        if section_id and section_id != "None":
            # ✅ جلب سجلات الحضور مع التفاصيل
            records = await service.get_attendance_records_with_details(
                school_id=user.school_id,
                date=selected_date,
                section_id=section_id,
                period_id=period_id
            )
            
            # جلب ملخص الحضور
            summary = await service.student_summary(
                user.school_id, selected_date, section_id
            )
            
            # جلب اسم الشعبة
            for section in hierarchy.get("sections", []):
                if section.get("id") == section_id:
                    section_name = section.get("display_name") or section.get("name")
                    break
        
        return templates.TemplateResponse(
            "attendance/students/list.html",
            {
                **ctx,
                "title": "حضور الطلاب",
                "records": records,
                "summary": summary,
                # ✅ البيانات المصفاة
                "years": hierarchy.get("years", []),
                "stages": hierarchy.get("stages", []),
                "grades": hierarchy.get("grades", []),
                "sections": hierarchy.get("sections", []),
                # ✅ جميع البيانات (للـ JavaScript)
                "all_stages": all_stages,
                "all_sections": all_sections,
                # ✅ القيم المحددة
                "selected_date": selected_date,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
                "selected_section": section_id,
                "section_name": section_name,
                "selected_period": period_id,
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in student_attendance_list: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/students/list.html",
            {
                **ctx,
                "title": "حضور الطلاب",
                "records": [],
                "summary": {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0},
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "all_stages": [],
                "all_sections": [],
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "selected_year": None,
                "selected_stage": None,
                "selected_grade": None,
                "selected_section": None,
                "section_name": None,
                "selected_period": None,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 3️⃣ نموذج تسجيل حضور الطلاب (محدث مع ضمان جلب البيانات)
# ============================================================

@router.get("/students/create")
async def create_student_attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    section_id: Optional[str] = None,
    date: Optional[str] = None,
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
    period_id: Optional[str] = None,
):
    """صفحة تسجيل حضور الطلاب مع التصفية المتدرجة"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        print("=" * 60)
        print("📝 صفحة تسجيل حضور الطلاب - CREATE")
        print("=" * 60)
        print(f"📌 المعاملات الواردة:")
        print(f"   section_id: {section_id}")
        print(f"   date: {selected_date}")
        print(f"   year_id: {year_id}")
        print(f"   stage_id: {stage_id}")
        print(f"   grade_id: {grade_id}")
        print(f"   period_id: {period_id}")
        print("=" * 60)
        
        # ✅ إنشاء خدمة الحضور
        service = AttendanceService(db)
        
        # ✅ ✅ ✅ تنفيذ استعلام جلب البيانات (مهم!)
        print("🔄 جاري تنفيذ استعلام جلب البيانات من قاعدة البيانات...")
        
        # جلب السنوات الدراسية
        years = await service.get_academic_years(user.school_id)
        print(f"   ✅ years: {len(years)} - {[y.get('name') for y in years]}")
        
        # جلب المراحل (حسب السنة إذا كانت محددة)
        stages = await service.get_stages_by_year(user.school_id, year_id)
        print(f"   ✅ stages: {len(stages)} - {[s.get('name') for s in stages]}")
        
        # جلب الصفوف (حسب المرحلة والسنة إذا كانت محددة)
        grades = await service.get_grades_by_stage(user.school_id, stage_id, year_id)
        print(f"   ✅ grades: {len(grades)} - {[g.get('name') for g in grades]}")
        
        # جلب الشعب (حسب الصف إذا كان محددا)
        sections = await service.get_sections_by_grade(user.school_id, grade_id, year_id, stage_id)
        print(f"   ✅ sections: {len(sections)} - {[s.get('name') for s in sections]}")
        
        # ✅ جلب جميع البيانات للـ JavaScript (بدون تصفية)
        all_stages = await service.get_stages_by_year(user.school_id)
        all_sections = await service.get_sections_by_grade(user.school_id, include_all=True)
        
        print(f"   ✅ all_stages: {len(all_stages)}")
        print(f"   ✅ all_sections: {len(all_sections)}")
        
        # ✅ التحقق من البيانات
        if not years:
            print("⚠️ تحذير: لا توجد سنوات دراسية! تأكد من وجود بيانات في جدول academic_years")
        if not stages:
            print("⚠️ تحذير: لا توجد مراحل! تأكد من وجود بيانات في جدول stages")
        if not grades:
            print("⚠️ تحذير: لا توجد صفوف! تأكد من وجود بيانات في جدول grades")
        if not sections:
            print("⚠️ تحذير: لا توجد شعب! تأكد من وجود بيانات في جدول sections")
        
        # جلب الطلاب
        students = []
        section_name = None
        grade_name = None
        stage_name = None
        year_name = None
        
        if section_id and section_id != "None":
            print(f"🔍 جلب الطلاب للشعبة: {section_id}")
            students = await service.get_students_with_details(
                school_id=user.school_id,
                section_id=section_id,
                date=selected_date,
                period_id=period_id,
                include_attendance=True
            )
            
            # جلب تفاصيل الشعبة من sections
            for section in sections:
                if section.get("id") == section_id:
                    section_name = section.get("display_name") or section.get("name")
                    grade_name = section.get("grade_name")
                    stage_name = section.get("stage_name")
                    year_name = section.get("year_name")
                    break
            
            print(f"   ✅ تم جلب {len(students)} طالب")
            print(f"   📚 اسم الشعبة: {section_name}")
            print(f"   📚 الصف: {grade_name}")
            print(f"   📚 المرحلة: {stage_name}")
            print(f"   📚 السنة: {year_name}")
        else:
            print("⚠️ لم يتم تحديد شعبة بعد")
        
        print("=" * 60)
        print("📤 إرسال البيانات إلى القالب:")
        print(f"   years: {len(years)}")
        print(f"   stages: {len(stages)}")
        print(f"   grades: {len(grades)}")
        print(f"   sections: {len(sections)}")
        print(f"   students: {len(students)}")
        print("=" * 60)
        
        return templates.TemplateResponse(
            "attendance/students/create.html",
            {
                **ctx,
                "title": "تسجيل حضور الطلاب",
                # ✅ البيانات المصفاة
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                # ✅ جميع البيانات (للـ JavaScript)
                "all_stages": all_stages,
                "all_sections": all_sections,
                # ✅ الطلاب
                "students": students,
                # ✅ التفاصيل
                "section_name": section_name,
                "grade_name": grade_name,
                "stage_name": stage_name,
                "year_name": year_name,
                # ✅ القيم المحددة
                "selected_date": selected_date,
                "selected_section": section_id,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
                "selected_period": period_id,
                "today": today,
                "statuses": [
                    {"value": "present", "label": "✅ حاضر", "color": "green"},
                    {"value": "absent", "label": "❌ غائب", "color": "red"},
                    {"value": "late", "label": "⏰ متأخر", "color": "yellow"},
                    {"value": "excused", "label": "📝 معذور", "color": "blue"},
                ],
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in create_student_attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/students/create.html",
            {
                **ctx,
                "title": "تسجيل حضور الطلاب",
                "years": [],
                "stages": [],
                "grades": [],
                "sections": [],
                "all_stages": [],
                "all_sections": [],
                "students": [],
                "section_name": None,
                "grade_name": None,
                "stage_name": None,
                "year_name": None,
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "selected_section": None,
                "selected_year": None,
                "selected_stage": None,
                "selected_grade": None,
                "selected_period": None,
                "today": datetime.now().strftime("%Y-%m-%d"),
                "statuses": [],
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 4️⃣ API: تسجيل حضور الطلاب (دفعة)
# ============================================================

@router.post("/api/v1/students")
async def create_student_attendance_api(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل حضور الطلاب عبر API"""
    try:
        content_type = request.headers.get("content-type", "")
        print(f"📥 Content-Type: {content_type}")
        
        body = await request.body()
        print(f"📦 Raw body length: {len(body)}")
        
        if "application/json" in content_type:
            data = await request.json()
            date_val = data.get("date")
            section_id = data.get("section_id")
            period_id = data.get("period_id")
            records = data.get("records", [])
        else:
            form_data = await request.form()
            date_val = form_data.get("date")
            section_id = form_data.get("section_id")
            period_id = form_data.get("period_id")
            
            records = []
            for key, value in form_data.items():
                if key.startswith("status_"):
                    student_id = key.replace("status_", "")
                    status = value
                    note = form_data.get(f"note_{student_id}", "")
                    records.append({
                        "student_id": student_id,
                        "status": status,
                        "note": note
                    })
        
        if not date_val:
            return JSONResponse({"detail": "التاريخ مطلوب"}, status_code=422)
        
        if not section_id or section_id == "None":
            return JSONResponse({"detail": "الشعبة مطلوبة"}, status_code=422)
        
        if not records:
            return JSONResponse({"detail": "يجب تحديد طالب واحد على الأقل"}, status_code=422)
        
        service = AttendanceService(db)
        
        saved_count = 0
        for record in records:
            try:
                attendance_data = StudentAttendanceCreate(
                    student_id=record["student_id"],
                    section_id=section_id,
                    period_id=period_id,
                    date=date_val,
                    status=record["status"],
                    note=record.get("note", "")
                )
                await service.record_student(
                    school_id=user.school_id,
                    user_id=user.id,
                    req=attendance_data
                )
                saved_count += 1
            except Exception as e:
                print(f"⚠️ Error saving record for student {record.get('student_id')}: {str(e)}")
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"تم تسجيل حضور {saved_count} طالب بنجاح",
            "total": len(records),
            "saved": saved_count
        }
        
    except ValidationException as e:
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        print(f"❌ Error creating attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 5️⃣ API: تحديث حضور طالب
# ============================================================

@router.put("/api/v1/students/{attendance_id}")
async def update_student_attendance_api(
    attendance_id: str,
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث سجل حضور طالب"""
    try:
        data = await request.json()
        
        result = await db.execute(
            select(StudentAttendance).where(StudentAttendance.id == attendance_id)
        )
        attendance = result.scalar_one_or_none()
        
        if not attendance:
            return JSONResponse({"detail": "سجل الحضور غير موجود"}, status_code=404)
        
        if "status" in data:
            attendance.status = data["status"]
        if "note" in data:
            attendance.note = data["note"]
        
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تحديث سجل الحضور بنجاح",
            "id": attendance_id
        }
        
    except Exception as e:
        print(f"❌ Error updating attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 6️⃣ API: حذف سجل حضور
# ============================================================

@router.delete("/api/v1/students/{attendance_id}")
async def delete_student_attendance_api(
    attendance_id: str,
    user: CurrentUser = Depends(require_any_permission("attendance.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف سجل حضور طالب"""
    try:
        result = await db.execute(
            select(StudentAttendance).where(StudentAttendance.id == attendance_id)
        )
        attendance = result.scalar_one_or_none()
        
        if not attendance:
            return JSONResponse({"detail": "سجل الحضور غير موجود"}, status_code=404)
        
        await db.delete(attendance)
        await db.commit()
        
        return {
            "success": True,
            "message": "تم حذف سجل الحضور بنجاح"
        }
        
    except Exception as e:
        print(f"❌ Error deleting attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 7️⃣ API: جلب إحصائيات الحضور
# ============================================================

@router.get("/api/v1/stats")
async def get_attendance_stats(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = None,
    section_id: Optional[str] = None,
):
    """جلب إحصائيات الحضور"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        service = AttendanceService(db)
        summary = await service.student_summary(
            user.school_id, selected_date, section_id
        )
        
        return JSONResponse({
            "success": True,
            "date": selected_date,
            "summary": summary
        })
        
    except Exception as e:
        print(f"❌ Error getting attendance stats: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


# ============================================================
# 8️⃣ API: جلب الطلاب حسب الشعبة
# ============================================================

@router.get("/api/v1/sections/{section_id}/students")
async def get_section_students_api(
    section_id: str,
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    date: Optional[str] = None,
):
    """جلب طلاب الشعبة مع حالة الحضور"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        service = AttendanceService(db)
        students = await service.get_students_with_details(
            school_id=user.school_id,
            section_id=section_id,
            date=selected_date,
            include_attendance=True
        )
        
        return JSONResponse({
            "success": True,
            "students": students,
            "count": len(students)
        })
        
    except Exception as e:
        print(f"❌ Error getting section students: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


# ============================================================
# 9️⃣ صفحة حضور المعلمين
# ============================================================

@router.get("/teachers")
async def teacher_attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    date: Optional[str] = None,
):
    """صفحة حضور المعلمين"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        teachers_result = await db.execute(
            select(Teacher).where(
                Teacher.school_id == user.school_id,
                Teacher.is_active == True
            ).order_by(Teacher.first_name, Teacher.last_name)
        )
        teachers = teachers_result.scalars().all()
        
        attendance_result = await db.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.school_id == user.school_id,
                TeacherAttendance.date == selected_date
            )
        )
        attendance_records = attendance_result.scalars().all()
        
        attendance_map = {str(a.teacher_id): a for a in attendance_records}
        
        teachers_data = []
        for teacher in teachers:
            record = attendance_map.get(str(teacher.id))
            teachers_data.append({
                "id": str(teacher.id),
                "full_name": teacher.full_name,
                "employee_number": teacher.employee_number,
                "specialization": teacher.specialization,
                "attendance_id": str(record.id) if record else None,
                "status": record.status if record else None,
                "note": record.note if record else None,
                "has_attendance": record is not None
            })
        
        return templates.TemplateResponse(
            "attendance/teachers/list.html",
            {
                **ctx,
                "title": "حضور المعلمين",
                "teachers": teachers_data,
                "selected_date": selected_date,
                "today": today,
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in teacher_attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/teachers/list.html",
            {
                **ctx,
                "title": "حضور المعلمين",
                "teachers": [],
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "today": datetime.now().strftime("%Y-%m-%d"),
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 🔟 صفحة تسجيل حضور معلم
# ============================================================

@router.get("/teachers/create")
async def create_teacher_attendance_page(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
    date: Optional[str] = None,
):
    """صفحة تسجيل حضور معلمين"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = date or today
        
        teachers_result = await db.execute(
            select(Teacher).where(
                Teacher.school_id == user.school_id,
                Teacher.is_active == True
            ).order_by(Teacher.first_name, Teacher.last_name)
        )
        teachers = teachers_result.scalars().all()
        
        return templates.TemplateResponse(
            "attendance/teachers/create.html",
            {
                **ctx,
                "title": "تسجيل حضور المعلمين",
                "teachers": teachers,
                "selected_date": selected_date,
                "today": today,
                "statuses": [
                    {"value": "present", "label": "✅ حاضر", "color": "green"},
                    {"value": "absent", "label": "❌ غائب", "color": "red"},
                    {"value": "late", "label": "⏰ متأخر", "color": "yellow"},
                    {"value": "leave", "label": "📝 إجازة", "color": "blue"},
                ],
                "error": None
            }
        )
    except Exception as e:
        print(f"❌ Error in create_teacher_attendance_page: {str(e)}")
        traceback.print_exc()
        return templates.TemplateResponse(
            "attendance/teachers/create.html",
            {
                **ctx,
                "title": "تسجيل حضور المعلمين",
                "teachers": [],
                "selected_date": datetime.now().strftime("%Y-%m-%d"),
                "today": datetime.now().strftime("%Y-%m-%d"),
                "statuses": [],
                "error": f"حدث خطأ: {str(e)}"
            },
            status_code=400
        )


# ============================================================
# 1️⃣1️⃣ API: تسجيل حضور معلم
# ============================================================

@router.post("/api/v1/teachers")
async def create_teacher_attendance_api(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.create")),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل حضور معلم عبر API"""
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
            teacher_id = data.get("teacher_id")
            date_val = data.get("date")
            status = data.get("status")
            note = data.get("note", "")
        else:
            form_data = await request.form()
            teacher_id = form_data.get("teacher_id")
            date_val = form_data.get("date")
            status = form_data.get("status")
            note = form_data.get("note", "")
        
        if not teacher_id:
            return JSONResponse({"detail": "معرف المعلم مطلوب"}, status_code=422)
        
        if not date_val:
            return JSONResponse({"detail": "التاريخ مطلوب"}, status_code=422)
        
        if not status:
            return JSONResponse({"detail": "الحالة مطلوبة"}, status_code=422)
        
        req = TeacherAttendanceCreate(
            teacher_id=teacher_id,
            date=date_val,
            status=status,
            note=note
        )
        
        service = AttendanceService(db)
        result = await service.record_teacher(
            school_id=user.school_id,
            user_id=user.id,
            req=req
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "تم تسجيل حضور المعلم بنجاح",
            "data": result
        }
        
    except ValidationException as e:
        await db.rollback()
        return JSONResponse({"detail": str(e)}, status_code=422)
    except Exception as e:
        print(f"❌ Error creating teacher attendance: {str(e)}")
        traceback.print_exc()
        await db.rollback()
        return JSONResponse({"detail": f"حدث خطأ: {str(e)}"}, status_code=500)


# ============================================================
# 1️⃣2️⃣ مسارات التصحيح (Debug)
# ============================================================

@router.get("/debug/hierarchy")
async def debug_hierarchy(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    year_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    grade_id: Optional[str] = None,
):
    """عرض التسلسل الهرمي للتصحيح"""
    try:
        service = AttendanceService(db)
        hierarchy = await service.get_full_hierarchy(
            school_id=user.school_id,
            year_id=year_id,
            stage_id=stage_id,
            grade_id=grade_id
        )
        
        print("=" * 60)
        print("🔍 DEBUG HIERARCHY")
        print(f"   years: {len(hierarchy.get('years', []))}")
        print(f"   stages: {len(hierarchy.get('stages', []))}")
        print(f"   grades: {len(hierarchy.get('grades', []))}")
        print(f"   sections: {len(hierarchy.get('sections', []))}")
        print("=" * 60)
        
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
async def debug_attendance_data(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
):
    """عرض بيانات الحضور للتصحيح"""
    try:
        service = AttendanceService(db)
        hierarchy = await service.get_full_hierarchy(user.school_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        count_result = await db.execute(
            select(func.count(StudentAttendance.id)).where(
                StudentAttendance.school_id == user.school_id
            )
        )
        attendance_count = count_result.scalar() or 0
        
        today_result = await db.execute(
            select(func.count(StudentAttendance.id)).where(
                StudentAttendance.school_id == user.school_id,
                StudentAttendance.date == today
            )
        )
        today_attendance = today_result.scalar() or 0
        
        return JSONResponse({
            "years": hierarchy.get("years", []),
            "stages": hierarchy.get("stages", []),
            "grades": hierarchy.get("grades", []),
            "sections": hierarchy.get("sections", []),
            "attendance_count": attendance_count,
            "today_attendance": today_attendance,
            "today": today,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_attendance_data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/students")
async def debug_students(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
    section_id: Optional[str] = None,
):
    """عرض بيانات الطلاب للتصحيح"""
    try:
        service = AttendanceService(db)
        students = await service.get_students_with_details(
            school_id=user.school_id,
            section_id=section_id,
            include_attendance=False
        )
        
        return JSONResponse({
            "total": len(students),
            "students": students,
            "school_id": str(user.school_id),
            "section_id": section_id
        })
        
    except Exception as e:
        print(f"❌ Error in debug_students: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@router.get("/debug/check")
async def debug_check(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("attendance.view")),
    db: AsyncSession = Depends(get_db),
):
    """التحقق من البيانات المتاحة"""
    try:
        service = AttendanceService(db)
        hierarchy = await service.get_full_hierarchy(user.school_id)
        
        count_result = await db.execute(
            select(func.count(StudentAttendance.id)).where(
                StudentAttendance.school_id == user.school_id
            )
        )
        
        return JSONResponse({
            "success": True,
            "years_count": len(hierarchy.get("years", [])),
            "stages_count": len(hierarchy.get("stages", [])),
            "grades_count": len(hierarchy.get("grades", [])),
            "sections_count": len(hierarchy.get("sections", [])),
            "attendance_records_count": count_result.scalar() or 0,
            "school_id": str(user.school_id)
        })
        
    except Exception as e:
        print(f"❌ Error in debug_check: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )
