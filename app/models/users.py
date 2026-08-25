"""
User, Role, Permission and join models — the RBAC core.

Users belong to a school. Roles are per-school (each school can customise
its roles) but seeded from a default template. Permissions are global
keys defined in ``app.core.permissions``.
"""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Role(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    school_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Permission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    label_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    label_en: Mapped[str] = mapped_column(String(200))
    group: Mapped[str] = mapped_column(String(50), nullable=False)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class RolePermission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), index=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"), index=True
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions", lazy="selectin")


class User(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "users"

    school_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def get_role_keys(self) -> list[str]:
        """الحصول على مفاتيح الأدوار للمستخدم"""
        return [ur.role.key for ur in self.user_roles]

    def get_role_names(self) -> list[str]:
        """الحصول على أسماء الأدوار للمستخدم (بالعربية)"""
        return [ur.role.name_ar for ur in self.user_roles]

    def has_role(self, role_key: str) -> bool:
        """التحقق من أن المستخدم لديه دور معين"""
        return role_key in self.get_role_keys()

    def has_permission(self, permission_key: str) -> bool:
        """التحقق من أن المستخدم لديه صلاحية معينة"""
        for ur in self.user_roles:
            for rp in ur.role.role_permissions:
                if rp.permission.key == permission_key:
                    return True
        return False


class UserRole(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles", lazy="selectin")


__all__ = [
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission"
]
