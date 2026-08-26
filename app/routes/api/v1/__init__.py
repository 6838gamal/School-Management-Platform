"""API v1 routes package."""


"""API v1 routes."""
from fastapi import APIRouter

from app.routes.api.v1 import academics

router = APIRouter()

# تسجيل جميع مسارات API v1
router.include_router(academics.router)

__all__ = ["router"]
