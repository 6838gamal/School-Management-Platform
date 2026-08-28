from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/grades", tags=["grades"])
templates = Jinja2Templates(directory="app/templates")

# ============================================
# 🛠️ دوال مساعدة (مؤقتة - استبدلها بالخدمات الحقيقية)
# ============================================

async def get_all_assessments(search: Optional[str] = None, page: int = 1, page_size: int = 10):
    """جلب جميع التقييمات من قاعدة البيانات"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return []

async def get_assessment_by_id(id: str):
    """جلب تقييم محدد بواسطة ID"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return None

async def get_all_sections():
    """جلب جميع الشعب"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return []

async def get_all_subjects():
    """جلب جميع المواد"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return []

async def get_all_teachers():
    """جلب جميع المعلمين"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return []

async def create_assessment(data: dict):
    """إنشاء تقييم جديد"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return {"id": "new_id"}

async def update_assessment(id: str, data: dict):
    """تحديث تقييم"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return True

async def delete_assessment(id: str):
    """حذف تقييم"""
    # TODO: استبدل هذا بالخدمة الحقيقية
    return True

# ============================================
# 📌 روات إدارة الدرجات
# ============================================

@router.get("")
async def grades_page(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """عرض صفحة الدرجات الرئيسية"""
    assessments = await get_all_assessments(search=search, page=page, page_size=page_size)
    
    ctx = {
        "request": request,
        "title": "الدرجات",
        "assessments": assessments,
        "total": len(assessments),
        "page": page,
        "page_size": page_size,
        "search": search or "",
        "now": datetime.now(),
        "can": request.state.can if hasattr(request.state, 'can') else lambda x: True,
        "current_user": request.state.user if hasattr(request.state, 'user') else None,
    }
    return templates.TemplateResponse("grades/index.html", ctx)

@router.get("/create")
async def create_assessment_page(request: Request):
    """عرض صفحة إنشاء تقييم جديد"""
    sections = await get_all_sections()
    subjects = await get_all_subjects()
    teachers = await get_all_teachers()
    
    ctx = {
        "request": request,
        "title": "إنشاء تقييم جديد",
        "sections": sections,
        "subjects": subjects,
        "teachers": teachers,
        "current_user": request.state.user if hasattr(request.state, 'user') else None,
        "can": request.state.can if hasattr(request.state, 'can') else lambda x: True,
        "csrf_token": request.state.csrf_token if hasattr(request.state, 'csrf_token') else None,
    }
    return templates.TemplateResponse("grades/create.html", ctx)

@router.post("")
async def store_assessment(request: Request):
    """إنشاء تقييم جديد"""
    form_data = await request.form()
    data = dict(form_data)
    
    # تحويل البيانات إلى الصيغة المطلوبة
    assessment_data = {
        "title": data.get("title"),
        "section_id": data.get("section_id"),
        "subject_id": data.get("subject_id"),
        "assessment_type": data.get("assessment_type"),
        "date": data.get("date"),
        "max_score": float(data.get("max_score", 100)),
        "passing_score": float(data.get("passing_score", 50)),
        "weight": float(data.get("weight", 1.0)),
        "description": data.get("description"),
        "teacher_id": data.get("teacher_id"),
    }
    
    await create_assessment(assessment_data)
    return RedirectResponse(url="/grades?success=created", status_code=303)

@router.get("/{id}")
async def show_assessment(request: Request, id: str):
    """عرض تفاصيل تقييم محدد"""
    assessment = await get_assessment_by_id(id)
    
    ctx = {
        "request": request,
        "title": "تفاصيل التقييم",
        "assessment": assessment,
        "current_user": request.state.user if hasattr(request.state, 'user') else None,
        "now": datetime.now(),
    }
    return templates.TemplateResponse("grades/show.html", ctx)

@router.get("/{id}/update")
async def edit_assessment_page(request: Request, id: str):
    """عرض صفحة تعديل التقييم"""
    assessment = await get_assessment_by_id(id)
    sections = await get_all_sections()
    subjects = await get_all_subjects()
    teachers = await get_all_teachers()
    
    ctx = {
        "request": request,
        "title": "تعديل التقييم",
        "assessment": assessment,
        "sections": sections,
        "subjects": subjects,
        "teachers": teachers,
        "current_user": request.state.user if hasattr(request.state, 'user') else None,
        "can": request.state.can if hasattr(request.state, 'can') else lambda x: True,
        "csrf_token": request.state.csrf_token if hasattr(request.state, 'csrf_token') else None,
        "now": datetime.now(),
    }
    return templates.TemplateResponse("grades/update.html", ctx)

@router.post("/{id}/update")
async def update_assessment(request: Request, id: str):
    """تحديث التقييم"""
    form_data = await request.form()
    data = dict(form_data)
    
    # تحويل البيانات إلى الصيغة المطلوبة
    assessment_data = {
        "title": data.get("title"),
        "section_id": data.get("section_id"),
        "subject_id": data.get("subject_id"),
        "assessment_type": data.get("assessment_type"),
        "date": data.get("date"),
        "max_score": float(data.get("max_score", 100)),
        "passing_score": float(data.get("passing_score", 50)),
        "weight": float(data.get("weight", 1.0)),
        "description": data.get("description"),
        "teacher_id": data.get("teacher_id"),
    }
    
    await update_assessment(id, assessment_data)
    return RedirectResponse(url=f"/grades/{id}?success=updated", status_code=303)

@router.post("/{id}/delete")
async def delete_assessment(request: Request, id: str):
    """حذف التقييم"""
    await delete_assessment(id)
    return RedirectResponse(url="/grades?success=deleted", status_code=303)

# ============================================
# 📊 API Routes (للـ JSON)
# ============================================

@router.get("/api")
async def api_get_assessments(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """API لجلب التقييمات بصيغة JSON"""
    assessments = await get_all_assessments(search=search, page=page, page_size=page_size)
    return {
        "items": assessments,
        "total": len(assessments),
        "page": page,
        "page_size": page_size,
    }

@router.get("/api/{id}")
async def api_get_assessment(id: str):
    """API لجلب تقييم محدد بصيغة JSON"""
    assessment = await get_assessment_by_id(id)
    return assessment
