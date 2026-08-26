"""Authentication service with logging."""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.models.users import User
from app.models.users import Role
from app.models.schools import School
from app.models.users import UserRole
from app.schemas.auth import (
    RegisterSchoolRequest,
    RegisterUserRequest,
)

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """خدمة المصادقة مع تسجيل الأحداث"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _hash_password(self, password: str) -> str:
        """تشفير كلمة المرور"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """التحقق من كلمة المرور"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _create_token(self, user_id: int, email: str, roles: List[str]) -> str:
        """إنشاء توكن JWT"""
        payload = {
            "user_id": user_id,
            "email": email,
            "roles": roles,
            "exp": datetime.utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """فك تشفير التوكن"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("انتهت صلاحية الجلسة")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("توكن غير صالح")
    
    # ============================================
    # دوال البحث مع logging
    # ============================================
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """الحصول على مستخدم بواسطة البريد الإلكتروني"""
        logger.info(f"🔍 البحث عن مستخدم بالبريد: {email}")
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == func.lower(email))
        )
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"✅ تم العثور على المستخدم: {user.email} (ID: {user.id})")
        else:
            logger.warning(f"❌ لم يتم العثور على مستخدم بالبريد: {email}")
        return user
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """الحصول على مستخدم بواسطة المعرف"""
        logger.info(f"🔍 البحث عن مستخدم بالمعرف: {user_id}")
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"✅ تم العثور على المستخدم: {user.email}")
        else:
            logger.warning(f"❌ لم يتم العثور على مستخدم بالمعرف: {user_id}")
        return user
    
    async def _get_school_by_code(self, school_code: str) -> Optional[School]:
        """الحصول على مدرسة بواسطة الرمز"""
        logger.info(f"🔍 البحث عن مدرسة بالرمز: {school_code}")
        result = await self.db.execute(
            select(School).where(func.upper(School.code) == func.upper(school_code))
        )
        school = result.scalar_one_or_none()
        if school:
            logger.info(f"✅ تم العثور على المدرسة: {school.name} (ID: {school.id})")
        else:
            logger.warning(f"❌ لم يتم العثور على مدرسة بالرمز: {school_code}")
        return school
    
    # ✅ التصحيح 1: استخدام Role.key بدلاً من Role.name
    async def _get_role_by_key(self, role_key: str) -> Optional[Role]:
        """الحصول على دور بواسطة المفتاح (key)"""
        logger.info(f"🔍 البحث عن دور بالمفتاح: {role_key}")
        result = await self.db.execute(
            select(Role).where(func.lower(Role.key) == func.lower(role_key))
        )
        role = result.scalar_one_or_none()
        if role:
            logger.info(f"✅ تم العثور على الدور: {role.key} (ID: {role.id})")
        else:
            logger.warning(f"❌ لم يتم العثور على دور بالمفتاح: {role_key}")
        return role
    
    # ✅ التصحيح 2: استخدام Role.key
    async def _get_all_roles(self) -> List[str]:
        """الحصول على جميع مفاتيح الأدوار"""
        result = await self.db.execute(select(Role))
        roles = result.scalars().all()
        return [r.key for r in roles]
    
    # ✅ التصحيح 3: استخدام Role.key
    async def _get_user_roles(self, user: User) -> List[str]:
        """الحصول على مفاتيح أدوار المستخدم"""
        roles = []
        for user_role in user.user_roles:
            if user_role.role:
                roles.append(user_role.role.key)
        logger.info(f"📋 أدوار المستخدم {user.email}: {roles}")
        return roles
    
    # ============================================
    # دوال التسجيل مع logging
    # ============================================
    
    async def register_user(self, request: RegisterUserRequest) -> Dict[str, Any]:
        """تسجيل مستخدم جديد مع تسجيل مفصل"""
        logger.info("=" * 60)
        logger.info(f"📝 بدء تسجيل مستخدم جديد")
        logger.info(f"   - البريد: {request.email}")
        logger.info(f"   - الاسم: {request.full_name}")
        logger.info(f"   - الدور: {request.role_name}")
        logger.info(f"   - رمز المدرسة: {request.school_code}")
        
        try:
            # 1. التحقق من عدم وجود البريد
            existing_user = await self._get_user_by_email(request.email)
            if existing_user:
                logger.error(f"❌ البريد الإلكتروني مستخدم بالفعل: {request.email}")
                raise ValidationException("البريد الإلكتروني مستخدم بالفعل")
            
            # 2. البحث عن المدرسة
            school = await self._get_school_by_code(request.school_code)
            if not school:
                logger.error(f"❌ رمز المدرسة غير صحيح: {request.school_code}")
                raise ValidationException("رمز المدرسة غير صحيح")
            
            # 3. البحث عن الدور باستخدام key
            role = await self._get_role_by_key(request.role_name)
            
            # 4. إذا لم يتم العثور على الدور، عرض جميع الأدوار المتاحة
            if not role:
                available_roles = await self._get_all_roles()
                logger.error(f"❌ الدور غير موجود: {request.role_name}")
                logger.info(f"📋 الأدوار المتاحة: {available_roles}")
                raise ValidationException(
                    f"الدور '{request.role_name}' غير موجود. الأدوار المتاحة: {', '.join(available_roles)}"
                )
            
            # 5. إنشاء المستخدم
            logger.info("✅ جميع التحققات اجتازت بنجاح، جاري إنشاء المستخدم...")
            
            user = User(
                email=request.email.lower(),
                password_hash=self._hash_password(request.password),  # ✅ استخدام password_hash
                full_name=request.full_name,
                phone=request.phone,
                school_id=school.id,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()
            logger.info(f"✅ تم إنشاء المستخدم: {user.email} (ID: {user.id})")
            
            # 6. ربط المستخدم بالدور
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
            )
            self.db.add(user_role)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"✅ تم ربط المستخدم بالدور: {role.key}")
            
            # 7. تحويل إلى استجابة
            roles = await self._get_user_roles(user)
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "school_id": str(user.school_id) if user.school_id else None,
                "roles": roles,
            }
            
            logger.info("✅ ✅ ✅ تم تسجيل المستخدم بنجاح!")
            logger.info("=" * 60)
            
            return {"user": user_data}
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل المستخدم: {str(e)}")
            logger.error("=" * 60)
            raise
    
    async def register_school(self, request: RegisterSchoolRequest) -> Dict[str, Any]:
        """تسجيل مدرسة جديدة مع تسجيل مفصل"""
        logger.info("=" * 60)
        logger.info(f"🏫 بدء تسجيل مدرسة جديدة")
        logger.info(f"   - اسم المدرسة: {request.school_name}")
        logger.info(f"   - رمز المدرسة: {request.school_code}")
        logger.info(f"   - اسم المدير: {request.director_name}")
        logger.info(f"   - بريد المدير: {request.director_email}")
        
        try:
            # 1. التحقق من عدم وجود البريد
            existing_user = await self._get_user_by_email(request.director_email)
            if existing_user:
                logger.error(f"❌ البريد الإلكتروني مستخدم بالفعل: {request.director_email}")
                raise ValidationException("البريد الإلكتروني مستخدم بالفعل")
            
            # 2. التحقق من عدم وجود رمز المدرسة
            existing_school = await self._get_school_by_code(request.school_code)
            if existing_school:
                logger.error(f"❌ رمز المدرسة مستخدم بالفعل: {request.school_code}")
                raise ValidationException("رمز المدرسة مستخدم بالفعل")
            
            # 3. إنشاء المدرسة
            school = School(
                name=request.school_name,
                code=request.school_code.upper(),
                is_active=True,
            )
            self.db.add(school)
            await self.db.flush()
            logger.info(f"✅ تم إنشاء المدرسة: {school.name} (ID: {school.id})")
            
            # 4. الحصول على دور المدير باستخدام key
            role = await self._get_role_by_key("director")
            if not role:
                available_roles = await self._get_all_roles()
                logger.error(f"❌ دور المدير غير موجود")
                logger.info(f"📋 الأدوار المتاحة: {available_roles}")
                raise ValidationException(f"دور المدير غير موجود. الأدوار المتاحة: {', '.join(available_roles)}")
            
            # 5. إنشاء المستخدم (المدير)
            user = User(
                email=request.director_email.lower(),
                password_hash=self._hash_password(request.director_password),  # ✅ استخدام password_hash
                full_name=request.director_name,
                phone=request.director_phone,
                school_id=school.id,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()
            logger.info(f"✅ تم إنشاء المدير: {user.email} (ID: {user.id})")
            
            # 6. ربط المستخدم بدور المدير
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
            )
            self.db.add(user_role)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"✅ تم ربط المدير بالدور: {role.key}")
            
            # 7. تحويل إلى استجابة
            roles = await self._get_user_roles(user)
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "school_id": str(user.school_id) if user.school_id else None,
                "roles": roles,
            }
            
            logger.info("✅ ✅ ✅ تم تسجيل المدرسة والمدير بنجاح!")
            logger.info("=" * 60)
            
            return {
                "school_id": school.id,
                "school_name": school.name,
                "school_code": school.code,
                "director": user_data,
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل المدرسة: {str(e)}")
            logger.error("=" * 60)
            raise
    
    # ============================================
    # دوال تسجيل الدخول مع logging
    # ============================================
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """تسجيل الدخول مع تسجيل مفصل"""
        logger.info("=" * 60)
        logger.info(f"🔐 محاولة تسجيل الدخول")
        logger.info(f"   - البريد: {email}")
        
        try:
            # 1. البحث عن المستخدم
            user = await self._get_user_by_email(email)
            
            if not user:
                logger.warning(f"❌ فشل تسجيل الدخول: المستخدم غير موجود ({email})")
                logger.info("=" * 60)
                raise UnauthorizedException("البريد الإلكتروني أو كلمة المرور غير صحيحة")
            
            logger.info(f"✅ تم العثور على المستخدم: {user.email}")
            
            # 2. التحقق من كلمة المرور
            logger.info("🔍 التحقق من كلمة المرور...")
            password_valid = self._verify_password(password, user.password_hash)  # ✅ استخدام password_hash
            
            if not password_valid:
                logger.warning(f"❌ فشل تسجيل الدخول: كلمة مرور غير صحيحة ({email})")
                logger.info("=" * 60)
                raise UnauthorizedException("البريد الإلكتروني أو كلمة المرور غير صحيحة")
            
            logger.info("✅ كلمة المرور صحيحة")
            
            # 3. التحقق من أن المستخدم نشط
            if not user.is_active:
                logger.warning(f"❌ فشل تسجيل الدخول: الحساب غير نشط ({email})")
                logger.info("=" * 60)
                raise UnauthorizedException("الحساب غير نشط. يرجى التواصل مع المدير")
            
            logger.info("✅ الحساب نشط")
            
            # 4. الحصول على الأدوار
            roles = await self._get_user_roles(user)
            if not roles:
                logger.warning(f"❌ فشل تسجيل الدخول: لا توجد أدوار للمستخدم ({email})")
                logger.info("=" * 60)
                raise UnauthorizedException("ليس لديك صلاحيات للدخول")
            
            logger.info(f"✅ الأدوار المتاحة: {roles}")
            
            # 5. إنشاء توكن
            token = self._create_token(user.id, user.email, roles)
            logger.info(f"✅ تم إنشاء التوكن للمستخدم: {user.email}")
            
            # 6. تحويل إلى استجابة
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "is_active": user.is_active,
                "school_id": str(user.school_id) if user.school_id else None,
                "roles": roles,
            }
            
            logger.info(f"✅ ✅ ✅ تسجيل الدخول ناجح: {user.email}")
            logger.info("=" * 60)
            
            return {
                "token": token,
                "user": user_data,
                "expires_at": datetime.utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE),
            }
            
        except UnauthorizedException:
            raise
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في تسجيل الدخول: {str(e)}")
            logger.info("=" * 60)
            raise
    
    # ============================================
    # دوال Debug
    # ============================================
    
    async def debug_get_all_users(self) -> List[Dict[str, Any]]:
        """الحصول على جميع المستخدمين للتحقق"""
        result = await self.db.execute(select(User))
        users = result.scalars().all()
        
        logger.info("=" * 60)
        logger.info("📋 جميع المستخدمين في قاعدة البيانات:")
        
        users_data = []
        for user in users:
            roles = await self._get_user_roles(user)
            user_info = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "school_id": user.school_id,
                "roles": roles,
            }
            users_data.append(user_info)
            logger.info(f"  - ID: {user.id}, Email: {user.email}, Active: {user.is_active}, Roles: {roles}")
        
        logger.info("=" * 60)
        return users_data
    
    # ✅ التصحيح 4: استخدام Role.key بدلاً من Role.name
    async def debug_get_all_roles(self) -> List[Dict[str, Any]]:
        """الحصول على جميع الأدوار للتحقق"""
        result = await self.db.execute(select(Role))
        roles = result.scalars().all()
        
        logger.info("=" * 60)
        logger.info("📋 جميع الأدوار في قاعدة البيانات:")
        
        roles_data = []
        for role in roles:
            role_info = {
                "id": role.id,
                "key": role.key,  # ✅ استخدام key
                "name_ar": role.name_ar,
                "name_en": role.name_en,
                "is_system": role.is_system,
            }
            roles_data.append(role_info)
            logger.info(f"  - ID: {role.id}, Key: '{role.key}', Name: '{role.name_ar}'")
        
        logger.info("=" * 60)
        return roles_data
