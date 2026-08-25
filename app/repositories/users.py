"""User, Role, Permission repositories."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.users import User, Role, Permission, UserRole, RolePermission
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email with roles loaded."""
        try:
            query = (
                select(User)
                .where(User.email == email)
                .options(
                    selectinload(User.user_roles)
                    .selectinload(UserRole.role)
                    .selectinload(Role.role_permissions)
                    .selectinload(RolePermission.permission)
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            # إذا فشل التحميل مع selectinload، حاول بدونها
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

    async def get_with_roles(self, id: str) -> User | None:
        """Get user with all roles and permissions loaded."""
        try:
            query = (
                select(User)
                .where(User.id == id)
                .options(
                    selectinload(User.user_roles)
                    .selectinload(UserRole.role)
                    .selectinload(Role.role_permissions)
                    .selectinload(RolePermission.permission)
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            query = select(User).where(User.id == id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        """List users by school with pagination."""
        return await self.list(filters={"school_id": school_id}, page=page, page_size=page_size)


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def list_by_school(self, school_id: str) -> list[Role]:
        """List roles by school with permissions loaded."""
        try:
            query = (
                select(Role)
                .where(Role.school_id == school_id)
                .options(
                    selectinload(Role.role_permissions)
                    .selectinload(RolePermission.permission)
                )
            )
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            query = select(Role).where(Role.school_id == school_id)
            result = await self.db.execute(query)
            return list(result.scalars().all())

    async def get_by_key(self, school_id: str, key: str) -> Role | None:
        """Get role by school_id and key."""
        query = select(Role).where(Role.school_id == school_id, Role.key == key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def set_permissions(self, role: Role, permission_ids: list[str]) -> None:
        """Set permissions for a role (replace all existing)."""
        # Remove existing
        query = select(RolePermission).where(RolePermission.role_id == role.id)
        result = await self.db.execute(query)
        for rp in result.scalars().all():
            await self.db.delete(rp)
        
        # Add new
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role.id, permission_id=pid))
        await self.db.flush()


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def get_by_key(self, key: str) -> Permission | None:
        """Get permission by key."""
        query = select(Permission).where(Permission.key == key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_dict(self) -> dict[str, Permission]:
        """Get all permissions as dict keyed by permission key."""
        result = await self.db.execute(select(Permission))
        return {p.key: p for p in result.scalars().all()}


class UserRoleRepository(BaseRepository[UserRole]):
    model = UserRole

    async def assign(self, user_id: str, role_id: str) -> UserRole:
        """Assign a role to a user if not already assigned."""
        query = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.db.execute(query)
        obj = result.scalar_one_or_none()
        if obj:
            return obj
        obj = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(obj)
        await self.db.flush()
        return obj
