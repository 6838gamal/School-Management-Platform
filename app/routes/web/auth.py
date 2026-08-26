"""Auth web routes: login, register, logout."""
import os
import glob

@router.get("/debug/files")
async def debug_files():
    """عرض جميع ملفات models للتحقق"""
    models_path = "app/models/"
    files = []
    
    # البحث عن جميع الملفات في مجلد models
    for file in glob.glob(f"{models_path}**/*.py", recursive=True):
        files.append(file.replace("app/models/", ""))
    
    return {
        "models_directory": models_path,
        "files": files,
        "total": len(files)
    }

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import template_context
from app.core.exceptions import UnauthorizedException
from app.services.auth_service import AuthService

router = APIRouter(prefix="", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

# قاموس عرض الأدوار
ROLE_DISPLAY = {
    "director": "مدير",
    "vice_principal": "وكيل",
    "activities_officer": "مسؤول أنشطة",
    "teacher": "معلم"
}


@router.get("/login")
async def login_page(request: Request, ctx: dict = Depends(template_context)):
    if ctx.get("current_user"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/login.html", {**ctx, "title": "تسجيل الدخول"})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    remember: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    
    try:
        # تسجيل الدخول والحصول على بيانات المستخدم
        result = await service.login(email, password)
        
        # التحقق من أن المستخدم لديه الدور المحدد
        user_roles = result["user"]["roles"]
        if role not in user_roles:
            # عرض الأدوار المتاحة للمستخدم
            available_roles = [ROLE_DISPLAY.get(r, r) for r in user_roles]
            roles_text = "، ".join(available_roles)
            
            return templates.TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "title": "تسجيل الدخول",
                    "error": f"⚠️ الدور '{ROLE_DISPLAY.get(role, role)}' غير متاح لهذا الحساب. الأدوار المتاحة: {roles_text}",
                    "email": email,
                    "selected_role": role,
                    "current_user": None,
                }
            )
        
        # إنشاء رد مع توكن
        resp = RedirectResponse("/dashboard", status_code=302)
        
        # تحديد مدة انتهاء الجلسة
        max_age = settings.SESSION_MAX_AGE
        if remember:
            max_age = max_age * 7  # 7 أيام إذا اختار "تذكرني"
        
        resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=result["token"],
            max_age=max_age,
            httponly=settings.SESSION_HTTPONLY,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        
        # إضافة الدور المختار في الجلسة (يمكن استخدامه للتوجيه)
        resp.set_cookie(
            key="selected_role",
            value=role,
            max_age=max_age,
            httponly=True,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        
        return resp
        
    except UnauthorizedException as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "تسجيل الدخول",
                "error": str(e),
                "email": email,
                "selected_role": role,
                "current_user": None,
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "تسجيل الدخول",
                "error": "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى",
                "email": email,
                "selected_role": role,
                "current_user": None,
            }
        )


@router.get("/register")
async def register_page(request: Request, ctx: dict = Depends(template_context)):
    if ctx.get("current_user"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("auth/register.html", {**ctx, "title": "تسجيل مستخدم جديد"})


@router.post("/register")
async def register_submit(
    request: Request,
    school_name: str = Form(...),
    school_code: str = Form(...),
    director_name: str = Form(...),
    director_email: str = Form(...),
    director_phone: str = Form(None),  # اختياري
    director_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.auth import RegisterSchoolRequest
    service = AuthService(db)
    try:
        result = await service.register_school(
            RegisterSchoolRequest(
                school_name=school_name,
                school_code=school_code,
                director_name=director_name,
                director_email=director_email,
                director_phone=director_phone if director_phone else None,
                director_password=director_password,
            )
        )
        
        # تسجيل الدخول التلقائي
        login_result = await service.login(director_email, director_password)
        resp = RedirectResponse("/onboarding", status_code=302)
        resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=login_result["token"],
            max_age=settings.SESSION_MAX_AGE,
            httponly=settings.SESSION_HTTPONLY,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        # تعيين دور المدير
        resp.set_cookie(
            key="selected_role",
            value="director",
            max_age=settings.SESSION_MAX_AGE,
            httponly=True,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        return resp
        
    except Exception as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "title": "تسجيل مستخدم جديد",
                "error": str(e),
                "school_name": school_name,
                "school_code": school_code,
                "director_name": director_name,
                "director_email": director_email,
                "director_phone": director_phone,
                "current_user": None,
            }
        )


# ============================================
# ✅ مسارات تسجيل الوكيل ومسؤول الأنشطة والمعلم
# ============================================

@router.post("/register-agent")
async def register_agent(
    request: Request,
    agent_number: str = Form(...),
    agent_name: str = Form(...),
    agent_email: str = Form(...),
    agent_phone: str = Form(None),  # اختياري
    agent_password: str = Form(...),
    school_code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل وكيل جديد"""
    from app.schemas.auth import RegisterUserRequest
    service = AuthService(db)
    
    try:
        # إنشاء المستخدم كـ "وكيل"
        result = await service.register_user(
            RegisterUserRequest(
                email=agent_email,
                password=agent_password,
                full_name=agent_name,
                employee_number=agent_number,
                phone=agent_phone if agent_phone else None,
                school_code=school_code,
                role_name="vice_principal"  # وكيل
            )
        )
        
        # تسجيل الدخول التلقائي
        login_result = await service.login(agent_email, agent_password)
        resp = RedirectResponse("/onboarding", status_code=302)
        resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=login_result["token"],
            max_age=settings.SESSION_MAX_AGE,
            httponly=settings.SESSION_HTTPONLY,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        # تعيين دور الوكيل
        resp.set_cookie(
            key="selected_role",
            value="vice_principal",
            max_age=settings.SESSION_MAX_AGE,
            httponly=True,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        return resp
        
    except Exception as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "title": "تسجيل مستخدم جديد",
                "error": str(e),
                "agent_name": agent_name,
                "agent_email": agent_email,
                "agent_number": agent_number,
                "agent_phone": agent_phone,
                "current_user": None,
            }
        )


@router.post("/register-activity")
async def register_activity(
    request: Request,
    activity_number: str = Form(...),
    activity_name: str = Form(...),
    activity_email: str = Form(...),
    activity_phone: str = Form(None),  # اختياري
    activity_password: str = Form(...),
    school_code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل مسؤول أنشطة جديد"""
    from app.schemas.auth import RegisterUserRequest
    service = AuthService(db)
    
    try:
        # إنشاء المستخدم كـ "مسؤول أنشطة"
        result = await service.register_user(
            RegisterUserRequest(
                email=activity_email,
                password=activity_password,
                full_name=activity_name,
                employee_number=activity_number,
                phone=activity_phone if activity_phone else None,
                school_code=school_code,
                role_name="activities_officer"  # مسؤول أنشطة
            )
        )
        
        # تسجيل الدخول التلقائي
        login_result = await service.login(activity_email, activity_password)
        resp = RedirectResponse("/onboarding", status_code=302)
        resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=login_result["token"],
            max_age=settings.SESSION_MAX_AGE,
            httponly=settings.SESSION_HTTPONLY,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        # تعيين دور مسؤول الأنشطة
        resp.set_cookie(
            key="selected_role",
            value="activities_officer",
            max_age=settings.SESSION_MAX_AGE,
            httponly=True,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        return resp
        
    except Exception as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "title": "تسجيل مستخدم جديد",
                "error": str(e),
                "activity_name": activity_name,
                "activity_email": activity_email,
                "activity_number": activity_number,
                "activity_phone": activity_phone,
                "current_user": None,
            }
        )


@router.post("/register-teacher")
async def register_teacher(
    request: Request,
    teacher_number: str = Form(...),
    teacher_name: str = Form(...),
    teacher_email: str = Form(...),
    teacher_phone: str = Form(None),  # اختياري
    teacher_password: str = Form(...),
    school_code: str = Form(...),
    subject: str = Form(None),  # اختياري
    db: AsyncSession = Depends(get_db),
):
    """تسجيل معلم جديد"""
    from app.schemas.auth import RegisterUserRequest
    service = AuthService(db)
    
    try:
        # إنشاء المستخدم كـ "معلم"
        result = await service.register_user(
            RegisterUserRequest(
                email=teacher_email,
                password=teacher_password,
                full_name=teacher_name,
                employee_number=teacher_number,
                phone=teacher_phone if teacher_phone else None,
                school_code=school_code,
                role_name="teacher",  # معلم
                extra_data={"subject": subject} if subject else {}
            )
        )
        
        # تسجيل الدخول التلقائي
        login_result = await service.login(teacher_email, teacher_password)
        resp = RedirectResponse("/onboarding", status_code=302)
        resp.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=login_result["token"],
            max_age=settings.SESSION_MAX_AGE,
            httponly=settings.SESSION_HTTPONLY,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        # تعيين دور المعلم
        resp.set_cookie(
            key="selected_role",
            value="teacher",
            max_age=settings.SESSION_MAX_AGE,
            httponly=True,
            secure=settings.SESSION_SECURE,
            samesite=settings.SESSION_SAMESITE,
        )
        return resp
        
    except Exception as e:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "title": "تسجيل مستخدم جديد",
                "error": str(e),
                "teacher_name": teacher_name,
                "teacher_email": teacher_email,
                "teacher_number": teacher_number,
                "teacher_phone": teacher_phone,
                "subject": subject,
                "current_user": None,
            }
        )


@router.get("/forgot-password")
async def forgot_password_page(request: Request, ctx: dict = Depends(template_context)):
    return templates.TemplateResponse("auth/forgot_password.html", {**ctx, "title": "استعادة كلمة المرور"})


@router.get("/reset-password")
async def reset_password_page(request: Request, ctx: dict = Depends(template_context)):
    return templates.TemplateResponse("auth/reset_password.html", {**ctx, "title": "تعيين كلمة مرور جديدة"})


@router.post("/logout")
async def logout(request: Request):
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(settings.SESSION_COOKIE_NAME)
    resp.delete_cookie("selected_role")
    return resp


# ============================================
# مسارات Debug للتحقق
# ============================================

@router.get("/debug/users")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """عرض جميع المستخدمين للتحقق"""
    service = AuthService(db)
    users = await service.debug_get_all_users()
    return {"users": users, "count": len(users)}

@router.get("/debug/roles")
async def debug_roles(db: AsyncSession = Depends(get_db)):
    """عرض جميع الأدوار للتحقق"""
    service = AuthService(db)
    roles = await service.debug_get_all_roles()
    return {"roles": roles, "count": len(roles)}

@router.get("/debug/check-user/{email}")
async def debug_check_user(email: str, db: AsyncSession = Depends(get_db)):
    """التحقق من وجود مستخدم معين"""
    service = AuthService(db)
    user = await service._get_user_by_email(email)
    if user:
        roles = await service._get_user_roles(user)
        return {
            "exists": True,
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "school_id": user.school_id,
            "roles": roles,
        }
    return {"exists": False, "email": email}
