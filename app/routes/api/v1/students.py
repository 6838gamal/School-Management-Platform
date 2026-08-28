"""Students API v1."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.schemas.common import MessageResponse
from app.schemas.students import StudentCreate, StudentUpdate, TransferRequest
from app.services.student_service import StudentService
from app.core.exceptions import NotFoundException, ConflictException, ValidationException

router = APIRouter(prefix="/students", tags=["students"])


# ============================================================
# 1️⃣ قائمة الطلاب
# ============================================================

@router.get("")
async def list_students(
    page: int = Query(1, ge=1, description="رقم الصفحة"),
    page_size: int = Query(20, ge=1, le=100, description="عدد العناصر في الصفحة"),
    search: str = Query("", description="كلمة البحث"),
    section_id: Optional[str] = Query(None, description="تصفية حسب الشعبة"),
    is_active: Optional[bool] = Query(True, description="تصفية حسب النشاط"),
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """جلب قائمة الطلاب مع البحث والترقيم."""
    service = StudentService(db)
    return await service.list_students(
        school_id=user.school_id,
        page=page,
        page_size=page_size,
        search=search or None,
        section_id=section_id,
        is_active=is_active,
    )


# ============================================================
# 2️⃣ إنشاء طالب جديد
# ============================================================

@router.post("", status_code=201)
async def create_student(
    req: StudentCreate,
    user: CurrentUser = Depends(require_permission("students.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    إنشاء طالب جديد.
    
    - **student_number**: رقم الطالب (يجب أن يكون فريداً)
    - **national_id**: الرقم الوطني (اختياري، يجب أن يكون فريداً)
    - **first_name**: الاسم الأول
    - **last_name**: اسم العائلة
    - **section_id**: معرف الشعبة (اختياري)
    - **year_id**: معرف العام الدراسي (اختياري)
    """
    service = StudentService(db)
    try:
        student = await service.create_student(
            data=req,
            user_id=user.id,
            school_id=user.school_id
        )
        return {
            "success": True,
            "message": "تم إضافة الطالب بنجاح",
            "data": {
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
            }
        }
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# 3️⃣ جلب تفاصيل طالب
# ============================================================

@router.get("/{student_id}")
async def get_student(
    student_id: str,
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """جلب تفاصيل الطالب مع معلومات من Academics Routes."""
    service = StudentService(db)
    try:
        student = await service.get_student_detail(student_id)
        
        # التحقق من أن الطالب ينتمي لنفس المدرسة
        if student.get("school_id") != user.school_id:
            raise HTTPException(
                status_code=403, 
                detail="ليس لديك صلاحية لعرض بيانات هذا الطالب"
            )
        
        return {
            "success": True,
            "data": student
        }
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# 4️⃣ تحديث بيانات طالب
# ============================================================

@router.put("/{student_id}")
async def update_student(
    student_id: str,
    req: StudentUpdate,
    user: CurrentUser = Depends(require_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    """تحديث بيانات الطالب."""
    service = StudentService(db)
    try:
        # التحقق من وجود الطالب أولاً
        existing = await service.get_student(student_id)
        if not existing:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # التحقق من أن الطالب ينتمي لنفس المدرسة
        if existing.school_id != user.school_id:
            raise HTTPException(
                status_code=403,
                detail="ليس لديك صلاحية لتعديل بيانات هذا الطالب"
            )
        
        student = await service.update_student(student_id, req)
        return {
            "success": True,
            "message": "تم تحديث بيانات الطالب بنجاح",
            "data": {
                "id": student.id,
                "student_number": student.student_number,
                "full_name": student.full_name,
            }
        }
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# 5️⃣ حذف طالب (تعطيل)
# ============================================================

@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    user: CurrentUser = Depends(require_permission("students.delete")),
    db: AsyncSession = Depends(get_db),
):
    """حذف طالب (تعطيل فقط، لا حذف فعلي)."""
    service = StudentService(db)
    try:
        # التحقق من وجود الطالب أولاً
        existing = await service.get_student(student_id)
        if not existing:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        # التحقق من أن الطالب ينتمي لنفس المدرسة
        if existing.school_id != user.school_id:
            raise HTTPException(
                status_code=403,
                detail="ليس لديك صلاحية لحذف هذا الطالب"
            )
        
        await service.delete_student(student_id)
        return {
            "success": True,
            "message": "تم حذف الطالب بنجاح"
        }
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# 6️⃣ نقل طالب بين الشعب (Transfer)
# ============================================================

@router.post("/transfer")
async def transfer_student(
    req: TransferRequest,
    user: CurrentUser = Depends(require_permission("students.transfer")),
    db: AsyncSession = Depends(get_db),
):
    """
    نقل طالب بين الشعب.
    
    - **student_id**: معرف الطالب
    - **from_section_id**: معرف الشعبة الحالية (اختياري)
    - **to_section_id**: معرف الشعبة الجديدة
    - **year_id**: معرف العام الدراسي (اختياري)
    """
    service = StudentService(db)
    try:
        # التحقق من وجود الطالب
        student = await service.get_student(req.student_id)
        if not student:
            raise NotFoundException(f"الطالب {req.student_id} غير موجود")
        
        # التحقق من أن الطالب ينتمي لنفس المدرسة
        if student.school_id != user.school_id:
            raise HTTPException(
                status_code=403,
                detail="ليس لديك صلاحية لنقل هذا الطالب"
            )
        
        # تنفيذ النقل
        result = await service.transfer_student(
            school_id=user.school_id,
            req=req
        )
        
        return {
            "success": True,
            "message": "تم نقل الطالب بنجاح",
            "data": result
        }
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# 7️⃣ جلب طلاب الشعبة (للتكامل مع Attendance)
# ============================================================

@router.get("/by-section/{section_id}")
async def get_students_by_section(
    section_id: str,
    is_active: bool = Query(True, description="تصفية حسب النشاط"),
    include_details: bool = Query(True, description="هل تشمل التفاصيل الإضافية؟"),
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """
    جلب جميع الطلاب في شعبة معينة.
    هذه النقطة تستخدم لتكامل Attendance مع Students.
    """
    service = StudentService(db)
    
    if include_details:
        # جلب الطلاب مع تفاصيل من Academics
        students = await service.get_students_with_details(
            school_id=user.school_id,
            section_id=section_id,
            is_active=is_active,
        )
    else:
        # جلب الطلاب فقط
        students = await service.get_by_section(
            school_id=user.school_id,
            section_id=section_id,
            is_active=is_active,
        )
    
    return {
        "success": True,
        "count": len(students),
        "data": students
    }


# ============================================================
# 8️⃣ البحث عن طالب (للتكامل مع Attendance)
# ============================================================

@router.get("/search")
async def search_students(
    query: str = Query(..., min_length=2, description="كلمة البحث"),
    limit: int = Query(10, ge=1, le=50, description="عدد النتائج"),
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """البحث عن طالب بالاسم أو رقم الطالب."""
    service = StudentService(db)
    students = await service.search_students(
        school_id=user.school_id,
        query=query,
        limit=limit
    )
    
    return {
        "success": True,
        "count": len(students),
        "data": students
    }


# ============================================================
# 9️⃣ إحصائيات الطلاب (للتكامل مع Attendance)
# ============================================================

@router.get("/stats")
async def get_student_stats(
    section_id: Optional[str] = Query(None, description="تصفية حسب الشعبة"),
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    """جلب إحصائيات الطلاب."""
    service = StudentService(db)
    stats = await service.get_stats(
        school_id=user.school_id,
        section_id=section_id
    )
    
    return {
        "success": True,
        "data": stats
    }
