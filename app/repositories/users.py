"""User, Role, Permission repositories."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.users import Permission, Role, RolePermission, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User)  # ✅ استخدم User مباشرة
            .where(User.email == email)
            .options(selectinload(User.user_roles))
        )
        return result.scalar_one_or_none()

    async def get_with_roles(self, id: str) -> User | None:
        result = await self.db.execute(
            select(User)  # ✅ استخدم User مباشرة
            .where(User.id == id)
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        return await self.list(filters={"school_id": school_id}, page=page, page_size=page_size)


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def list_by_school(self, school_id: str) -> list[Role]:
        result = await self.db.execute(
            select(Role)  # ✅ استخدم Role مباشرة
            .where(Role.school_id == school_id)
            .options(
                selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        return list(result.scalars().all())

    async def get_by_key(self, school_id: str, key: str) -> Role | None:
        result = await self.db.execute(
            select(Role).where(Role.school_id == school_id, Role.key == key)
        )
        return result.scalar_one_or_none()

    async def set_permissions(self, role: Role, permission_ids: list[str]) -> None:
        # Remove existing
        existing = await self.db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        for rp in existing.scalars().all():
            await self.db.delete(rp)
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role.id, permission_id=pid))
        await self.db.flush()


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def get_by_key(self, key: str) -> Permission | None:
        result = await self.db.execute(select(Permission).where(Permission.key == key))
        return result.scalar_one_or_none()

    async def get_all_dict(self) -> dict[str, Permission]:
        result = await self.db.execute(select(Permission))
        return {p.key: p for p in result.scalars().all()}


class UserRoleRepository(BaseRepository[UserRole]):
    model = UserRole

    async def assign(self, user_id: str, role_id: str) -> UserRole:
        existing = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            return obj
        obj = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(obj)
        await self.db.flush()
        return obj
