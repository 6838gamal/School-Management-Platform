"""Auth web routes: login, register, logout."""
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import template_context
from app.services.auth_service import AuthService

router = APIRouter(prefix="", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


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
    role: str = Form(...),  # إضافة حقل الدور
    remember: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    
    # محاولة تسجيل الدخول
    result = await service.login(email, password)
    
    # التحقق من أن الدور المحدد يتطابق مع دور المستخدم
    if result.get("role") != role:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "تسجيل الدخول",
                "error": f"⚠️ الدور المحدد غير صحيح. دورك الحقيقي هو: {result.get('role_display', result.get('role'))}",
                "email": email,
                "selected_role": role,
                "current_user": None,
            }
        )
    
    # إنشاء رد مع توكن
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=result["token"],
        max_age=settings.SESSION_MAX_AGE * 7 if remember else settings.SESSION_MAX_AGE,  # تذكرني لـ 7 أيام
        httponly=settings.SESSION_HTTPONLY,
        secure=settings.SESSION_SECURE,
        samesite=settings.SESSION_SAMESITE,
    )
    return resp


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
    result = await service.register_school(
        RegisterSchoolRequest(
            school_name=school_name,
            school_code=school_code,
            director_name=director_name,
            director_email=director_email,
            director_password=director_password,
        )
    )
    # Auto-login
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
    return resp


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
    return resp
