"""Web routes package."""
from fastapi import APIRouter
from app.routes.web import modules, grades, teachers

# إنشاء الـ router الرئيسي
router = APIRouter()

# تسجيل جميع الروات
router.include_router(modules.router)
router.include_router(grades.router)
router.include_router(teachers.router)

# تصدير router و routers الأخرى للاستخدام الخارجي
__all__ = ["router"]
