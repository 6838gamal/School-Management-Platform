"""Authentication and authorization service."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, ROLE_LABELS
from app.core.security import decode_session, encode_session, hash_password, verify_password
from app.models.academics import AcademicYear
from app.models.schools import School
from app.models.users import Permission, Role, RolePermission, User, UserRole
from app.repositories.academics import AcademicYearRepository, SchoolRepository
from app.repositories.users import PermissionRepository, RoleRepository, UserRoleRepository, UserRepository
from app.schemas.auth import RegisterSchoolRequest


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.permissions = PermissionRepository(db)
        self.user_roles = UserRoleRepository(db)
        self.schools = SchoolRepository(db)
        self.years = AcademicYearRepository(db)

    async def register_school(self, req: RegisterSchoolRequest) -> dict:
        # Check school code uniqueness
        existing = await self.schools.get_by_code(req.school_code)
        if existing:
            raise ConflictException("رمز المدرسة مستخدم بالفعل")
        existing_user = await self.users.get_by_email(req.director_email)
        if existing_user:
            raise ConflictException("البريد الإلكتروني مستخدم بالفعل")

        # Create school
        school = await self.schools.create(
            name=req.school_name,
            code=req.school_code,
            onboarding_complete=False,
            onboarding_step="school_info",
            is_active=True,
        )

        # Seed permissions + roles
        await self._seed_permissions()
        await self._seed_roles(school.id)

        # Create director user
        director = await self.users.create(
            email=req.director_email,
            password_hash=hash_password(req.director_password),
            full_name=req.director_name,
            school_id=school.id,
            is_active=True,
        )

        # Assign director role
        director_role = await self.roles.get_by_key(school.id, "director")
        if director_role:
            await self.user_roles.assign(director.id, director_role.id)

        # Create a default academic year
        year = await self.years.create(
            school_id=school.id,
            name=datetime.now(timezone.utc).strftime("%Y"),
            start_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            end_date=(datetime.now(timezone.utc).replace(month=12, day=30)).strftime("%Y-%m-%d"),
            is_current=True,
            is_active=True,
        )

        return {"school_id": school.id, "user_id": director.id, "year_id": year.id}

    async def login(self, email: str, password: str) -> dict:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("بيانات الدخول غير صحيحة")
        if not user.is_active:
            raise UnauthorizedException("الحساب معطل")
        # Load roles
        user = await self.users.get_with_roles(user.id)
        roles = [ur.role.key for ur in user.user_roles]
        perms: set[str] = set()
        for ur in user.user_roles:
            for rp in ur.role.role_permissions:
                perms.add(rp.permission.key)
        user.last_login_at = datetime.now(timezone.utc).isoformat()
        await self.db.flush()
        token = encode_session({"uid": user.id})
        return {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "school_id": user.school_id,
                "roles": roles,
                "permissions": list(perms),
            },
        }

    async def _seed_permissions(self) -> None:
        existing = await self.permissions.get_all_dict()
        for p in PERMISSIONS:
            if p.key not in existing:
                await self.permissions.create(
                    key=p.key, label_ar=p.label_ar, label_en=p.label_en, group=p.group,
                )

    async def _seed_roles(self, school_id: str) -> None:
        perm_dict = await self.permissions.get_all_dict()
        for role_key, perm_keys in ROLE_PERMISSIONS.items():
            role = await self.roles.get_by_key(school_id, role_key)
            if not role:
                labels = ROLE_LABELS[role_key]
                role = await self.roles.create(
                    school_id=school_id,
                    key=role_key,
                    name_ar=labels["ar"],
                    name_en=labels["en"],
                    is_system=True,
                )
            # Set permissions
            perm_ids = [perm_dict[k].id for k in perm_keys if k in perm_dict]
            await self.roles.set_permissions(role, perm_ids)
