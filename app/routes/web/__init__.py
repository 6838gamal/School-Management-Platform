"""Web routes package."""
# Makes web a Python package
from app.routes.web.teachers import router as teachers_router



from fastapi import APIRouter
from app.routes.web import modules, grades

router = APIRouter()

# تسجيل الروات
router.include_router(modules.router)
router.include_router(grades.router)

# يمكنك أيضاً تصدير router مباشرة
__all__ = ["router","teachers_router"]
