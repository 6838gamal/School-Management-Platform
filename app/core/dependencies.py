"""
FastAPI dependencies: session user, school scope, permission enforcement.

The ``current_user`` dependency decodes the session cookie, loads the user
with their roles and permissions, and attaches the active school context.
All downstream services rely on these dependencies — routes never access
the database directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Optional
from datetime import datetime, timedelta

from fastapi import Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_session, encode_session
from app.core.config import settings
from app.models.schools import School
from app.models.users import User
from app.models.users import UserRole, Role, Permission, RolePermission

# ------------------------------------------------------------------
# Session context
# ------------------------------------------------------------------


@dataclass
class CurrentUser:
    """Resolved user context shared with every protected route."""

    id: str
    email: str
    full_name: str
    school_id: str | None
    roles: list[str]
    permissions: set[str]
    user: User  # underlying ORM object

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else "guest"

    @property
    def role_label(self) -> str:
        from app.core.permissions import ROLE_LABELS

        return ROLE_LABELS.get(self.primary_role, {}).get("ar", self.primary_role)

    def has_permission(self, key: str) -> bool:
        return key in self.permissions

    def has_any_permission(self, *keys: str) -> bool:
        return any(k in self.permissions for k in keys)

    def has_all_permissions(self, *keys: str) -> bool:
        return all(k in self.permissions for k in keys)


# ------------------------------------------------------------------
# Cookie helpers
# ------------------------------------------------------------------


def _read_session_cookie(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    return decode_session(token)


def _refresh_session_cookie(response: Response, payload: dict[str, Any]) -> None:
    """Refresh session cookie with new expiry."""
    # تحديث وقت الإنشاء
    payload["_created"] = datetime.now().isoformat()
    
    # إعادة ترميز الجلسة
    token = encode_session(payload)
    
    # تعيين الكوكي مع مدة صلاحية جديدة
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE,
        httponly=settings.SESSION_HTTPONLY,
        secure=settings.SESSION_SECURE,
        samesite=settings.SESSION_SAMESITE,
        path="/",
    )


# ------------------------------------------------------------------
# Core dependencies
# ------------------------------------------------------------------


async def get_current_user(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser | None:
    """Resolve the current user from the session cookie. Returns None if no session."""
    payload = _read_session_cookie(request)
    if not payload:
        return None

    # استخدام "user_id" بدلاً من "uid" (مطابق لـ auth_service.py)
    user_id = payload.get("user_id")
    if not user_id:
        return None

    # ✅ التحقق من انتهاء الجلسة
    created_at = payload.get("_created")
    if created_at:
        try:
            created_time = datetime.fromisoformat(created_at)
            max_age = payload.get("_max_age", settings.SESSION_MAX_AGE)
            if datetime.now() - created_time > timedelta(seconds=max_age):
                # الجلسة منتهية
                return None
        except (ValueError, TypeError):
            pass

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    # جلب الأدوار والصلاحيات عبر استعلامات مباشرة
    roles: list[str] = []
    permissions: set[str] = set()
    
    # 1. جلب أدوار المستخدم
    result = await db.execute(
        select(Role.key)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = list(result.scalars().all())
    
    # 2. جلب صلاحيات المستخدم من خلال أدواره
    if roles:
        result = await db.execute(
            select(Permission.key)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user.id)
        )
        permissions = set(result.scalars().all())

    if not roles:
        roles = ["guest"]

    # ✅ تجديد الجلسة إذا كان مفعلاً
    if settings.SESSION_REFRESH_EACH_REQUEST:
        _refresh_session_cookie(response, payload)

    # تخزين المستخدم والصلاحيات في request.state للاستخدام في القوالب
    request.state.user = user
    request.state.permissions = permissions
    request.state.roles = roles

    return CurrentUser(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        school_id=str(user.school_id) if user.school_id else None,
        roles=roles,
        permissions=permissions,
        user=user,
    )


async def require_user(
    current: Annotated[CurrentUser | None, Depends(get_current_user)],
) -> CurrentUser:
    """Require an authenticated user or raise UnauthorizedException."""
    if current is None:
        raise UnauthorizedException()
    return current


async def require_school_context(
    current: Annotated[CurrentUser, Depends(require_user)],
) -> str:
    """Require that the user belongs to a school. Returns the school id."""
    if not current.school_id:
        raise ForbiddenException("المستخدم غير مرتبط بمدرسة")
    return current.school_id


# ------------------------------------------------------------------
# Permission dependency factory
# ------------------------------------------------------------------


def require_permission(*keys: str):
    """Dependency that enforces the user has ALL of the given permissions."""

    async def _checker(
        current: Annotated[CurrentUser, Depends(require_user)],
    ) -> CurrentUser:
        missing = [k for k in keys if k not in current.permissions]
        if missing:
            raise ForbiddenException(f"صلاحيات مطلوبة: {', '.join(missing)}")
        return current

    return _checker


def require_any_permission(*keys: str):
    """Dependency that enforces the user has at least one of the given permissions."""

    async def _checker(
        current: Annotated[CurrentUser, Depends(require_user)],
    ) -> CurrentUser:
        if not any(k in current.permissions for k in keys):
            raise ForbiddenException(f"صلاحية مطلوبة (إحدى): {', '.join(keys)}")
        return current

    return _checker


# ------------------------------------------------------------------
# Template helper function for can()
# ------------------------------------------------------------------

def can(request: Request, permission: str) -> bool:
    """التحقق من أن المستخدم لديه صلاحية معينة (للاستخدام في القوالب)"""
    if not hasattr(request, 'state'):
        return False
    
    # التحقق من وجود المستخدم في request.state
    if not hasattr(request.state, 'user') or request.state.user is None:
        return False
    
    # التحقق من الصلاحيات
    if hasattr(request.state, 'permissions'):
        return permission in request.state.permissions
    
    return False


# ------------------------------------------------------------------
# Template-friendly globals
# ------------------------------------------------------------------


async def template_context(request: Request) -> dict[str, Any]:
    """Build the standard template context with user + permissions.

    This is used by web routes that render Jinja2 templates. It makes
    ``current_user`` and ``can()`` available in every template without
    repeating boilerplate.
    """
    ctx: dict[str, Any] = {"request": request}
    user: CurrentUser | None = None
    
    try:
        # محاولة جلب المستخدم من قاعدة البيانات
        async for db in get_db():
            try:
                # ✅ تمرير Response فارغ (لن يتم استخدامه في التحديث)
                from fastapi import Response
                user = await get_current_user(request, Response(), db)
            finally:
                await db.close()
            break
    except Exception as e:
        user = None

    if user:
        ctx["current_user"] = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "school_id": user.school_id,
            "primary_role": user.primary_role,
            "role_label": user.role_label,
            "roles": user.roles,
        }
        ctx["permissions"] = user.permissions
        ctx["can"] = lambda k: k in user.permissions
        ctx["can_any"] = lambda *ks: any(k in user.permissions for k in ks)
    else:
        ctx["current_user"] = None
        ctx["permissions"] = set()
        ctx["can"] = lambda k: False
        ctx["can_any"] = lambda *ks: False

    return ctx
