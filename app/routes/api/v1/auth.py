"""Auth API v1."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import LoginRequest, RegisterSchoolRequest, SessionInfo
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse)
async def register(req: RegisterSchoolRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.register_school(req)
    return MessageResponse(message=f"تم إنشاء المدرسة بنجاح", success=True)


@router.post("/login", response_model=SessionInfo)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.login(req.email, req.password)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=result["token"],
        max_age=settings.SESSION_MAX_AGE,
        httponly=settings.SESSION_HTTPONLY,
        secure=settings.SESSION_SECURE,
        samesite=settings.SESSION_SAMESITE,
    )
    u = result["user"]
    return SessionInfo(
        user={
            "id": u["id"], "email": u["email"], "full_name": u["full_name"],
            "is_active": True, "school_id": u["school_id"], "roles": u["roles"],
        },
        school_id=u["school_id"],
        permissions=u["permissions"],
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return MessageResponse(message="تم تسجيل الخروج")
