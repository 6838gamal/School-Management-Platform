"""API v1 routes package."""


"""API routes."""
from fastapi import APIRouter

from app.routes.api import v1

router = APIRouter(prefix="/api")

# تسجيل جميع إصدارات API
router.include_router(v1.router, prefix="/v1")

__all__ = ["router"]
