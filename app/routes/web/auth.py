"""Auth web routes: login, register, logout."""
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
    return templates.TemplateResponse("auth/register.html", {**ctx, "title": "تسجيل مدرسة جديدة"})


@router.post("/register")
async def register_submit(
    request: Request,
    school_name: str = Form(...),
    school_code: str = Form(...),
    director_name: str = Form(...),
    director_email: str = Form(...),
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
                "title": "تسجيل مدرسة جديدة",
                "error": str(e),
                "school_name": school_name,
                "school_code": school_code,
                "director_name": director_name,
                "director_email": director_email,
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
