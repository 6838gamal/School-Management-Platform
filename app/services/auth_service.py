"""Authentication service with logging."""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import bcrypt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.security import encode_session, decode_session
from app.models.users import User
from app.models.users import Role
from app.models.schools import School
from app.models.users import UserRole
from app.schemas.auth import (
    RegisterSchoolRequest,
    RegisterUserRequest,
)

logger = logging.getLogger(__name__)


class AuthService:
    """خدمة المصادقة مع تسجيل الأحداث"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _hash_password(self, password: str) -> str:
        """
        تشفير كلمة المرور باستخدام bcrypt
        
        ملاحظة: bcrypt يدعم فقط 72 حرفاً كحد أقصى
        """
        try:
            # التأكد من أن كلمة المرور لا تتجاوز 72 حرفاً
            if len(password) > 72:
                password = password[:72]
                logger.warning(f"⚠️ تم تقصير كلمة المرور إلى 72 حرفاً")
            
            # تشفير كلمة المرور
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            logger.info(f"✅ تم تشفير كلمة المرور بنجاح")
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ فشل تشفير كلمة المرور: {str(e)}")
            raise ValidationException(f"فشل تشفير كلمة المرور: {str(e)}")
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """التحقق من كلمة المرور باستخدام bcrypt"""
        try:
            # التأكد من أن كلمة المرور لا تتجاوز 72 حرفاً
            if len(plain_password) > 72:
                plain_password = plain_password[:72]
            
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"❌ فشل التحقق من كلمة المرور: {str(e)}")
            return False
    
    def _create_token(self, user_id: str, email: str, roles: List[str]) -> str:
        """
        إنشاء توكن جلسة باستخدام itsdangerous
        
        ملاحظة: استخدام encode_session من security.py لتوحيد التشفير
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "roles": roles,
        }
        return encode_session(payload, max_age=settings.SESSION_MAX_AGE)
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """
        فك تشفير التوكن باستخدام itsdangerous
        
        ملاحظة: استخدام decode_session من security.py لتوحيد التشفير
        """
        payload = decode_session(token, max_age=settings.SESSION_MAX_AGE)
        if not payload:
            raise UnauthorizedException("توكن غير صالح أو منتهي الصلاحية")
        return payload
    
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
    
    async def _get_role_by_key(self, role_key: str, school_id: Optional[str] = None) -> Optional[Role]:
        """
        الحصول على دور بواسطة المفتاح (key) والمدرسة
        
        Args:
            role_key: مفتاح الدور (مثل director, deputy, ...)
            school_id: معرف المدرسة (اختياري - إذا لم يتم تمريره، سيتم البحث عن أي دور)
        """
        logger.info(f"🔍 البحث عن دور بالمفتاح: {role_key}")
        
        query = select(Role).where(func.lower(Role.key) == func.lower(role_key))
        
        # إذا تم تحديد school_id، أضفه في البحث
        if school_id:
            query = query.where(Role.school_id == school_id)
            logger.info(f"   - في المدرسة: {school_id}")
        
        result = await self.db.execute(query)
        role = result.scalar_one_or_none()
        
        if role:
            logger.info(f"✅ تم العثور على الدور: {role.key} (ID: {role.id})")
        else:
            logger.warning(f"❌ لم يتم العثور على دور بالمفتاح: {role_key}")
        
        return role
    
    async def _get_roles_by_key(self, role_key: str) -> List[Role]:
        """الحصول على جميع الأدوار بمفتاح معين (للمدارس المختلفة)"""
        logger.info(f"🔍 البحث عن جميع الأدوار بالمفتاح: {role_key}")
        result = await self.db.execute(
            select(Role).where(func.lower(Role.key) == func.lower(role_key))
        )
        roles = result.scalars().all()
        logger.info(f"✅ تم العثور على {len(roles)} دور")
        return roles
    
    async def _get_all_roles(self, school_id: Optional[str] = None) -> List[str]:
        """الحصول على جميع مفاتيح الأدوار (لمدرسة معينة أو كل الأدوار)"""
        query = select(Role)
        if school_id:
            query = query.where(Role.school_id == school_id)
        
        result = await self.db.execute(query)
        roles = result.scalars().all()
        return [r.key for r in roles]
    
    async def _get_or_create_role(self, role_key: str, school_id: str, name_ar: str, name_en: str, description: str = None) -> Role:
        """الحصول على دور أو إنشاؤه إذا لم يكن موجوداً"""
        role = await self._get_role_by_key(role_key, school_id)
        
        if not role:
            role = Role(
                school_id=school_id,
                key=role_key,
                name_ar=name_ar,
                name_en=name_en,
                description=description or f"دور {name_ar} في المدرسة",
                is_system=True
            )
            self.db.add(role)
            await self.db.flush()
            logger.info(f"✅ تم إنشاء دور جديد: {role_key} للمدرسة {school_id}")
        else:
            logger.info(f"⏭️ الدور موجود بالفعل: {role_key} للمدرسة {school_id}")
        
        return role
    
    # ============================================
    # ✅ دوال جلب الأدوار (محدثة - استعلام مباشر)
    # ============================================
    
    async def _get_user_roles(self, user: User) -> List[str]:
        """
        الحصول على مفاتيح أدوار المستخدم باستعلام مباشر من قاعدة البيانات
        
        ✅ تم التحديث لاستخدام استعلام مباشر بدلاً من الاعتماد على العلاقة
        """
        try:
            from sqlalchemy import select
            from app.models.users import UserRole, Role
            
            result = await self.db.execute(
                select(Role.key)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )
            roles = result.scalars().all()
            
            logger.info(f"📋 أدوار المستخدم {user.email}: {roles}")
            return list(roles)
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أدوار المستخدم {user.email}: {str(e)}")
            return []
    
    async def _get_user_roles_with_details(self, user: User) -> List[Dict[str, Any]]:
        """
        الحصول على تفاصيل أدوار المستخدم (للاستخدام في Debug)
        """
        try:
            from sqlalchemy import select
            from app.models.users import UserRole, Role
            
            result = await self.db.execute(
                select(Role)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )
            roles = result.scalars().all()
            
            return [
                {
                    "id": r.id,
                    "key": r.key,
                    "name_ar": r.name_ar,
                    "name_en": r.name_en,
                    "school_id": r.school_id,
                    "is_system": r.is_system,
                }
                for r in roles
            ]
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تفاصيل أدوار المستخدم: {str(e)}")
            return []
    
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
            
            # 3. البحث عن الدور مع school_id
            role = await self._get_role_by_key(request.role_name, school.id)
            
            # 4. إذا لم يتم العثور على الدور، قم بإنشائه
            if not role:
                logger.info(f"📝 الدور '{request.role_name}' غير موجود، جاري إنشائه...")
                
                # أسماء الأدوار بالعربية
                role_names_ar = {
                    "deputy": "وكيل",
                    "activities": "مسؤول أنشطة",
                    "teacher": "معلم"
                }
                
                role_names_en = {
                    "deputy": "Deputy",
                    "activities": "Activities Officer",
                    "teacher": "Teacher"
                }
                
                name_ar = role_names_ar.get(request.role_name, request.role_name)
                name_en = role_names_en.get(request.role_name, request.role_name)
                
                role = Role(
                    school_id=school.id,
                    key=request.role_name,
                    name_ar=name_ar,
                    name_en=name_en,
                    description=f"{name_ar} في المدرسة",
                    is_system=True
                )
                self.db.add(role)
                await self.db.flush()
                logger.info(f"✅ تم إنشاء الدور: {role.key} (ID: {role.id})")
            
            # 5. إنشاء المستخدم
            logger.info("✅ جميع التحققات اجتازت بنجاح، جاري إنشاء المستخدم...")
            
            user = User(
                email=request.email.lower(),
                password_hash=self._hash_password(request.password),
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
            
            # 7. تحويل إلى استجابة - استخدام الدالة المحدثة
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
            
            logger.info(f"✅ ✅ ✅ تم تسجيل المستخدم بنجاح! الأدوار: {roles}")
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
            
            # 4. إنشاء دور المدير للمدرسة مباشرة
            logger.info("📝 جاري إنشاء دور المدير للمدرسة...")
            role = Role(
                school_id=school.id,
                key="director",
                name_ar="مدير",
                name_en="Director",
                description="مدير المدرسة - صلاحيات كاملة",
                is_system=True
            )
            self.db.add(role)
            await self.db.flush()
            logger.info(f"✅ تم إنشاء دور المدير: {role.key} (ID: {role.id})")
            
            # 5. إنشاء المستخدم (المدير)
            user = User(
                email=request.director_email.lower(),
                password_hash=self._hash_password(request.director_password),
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
            
            # 7. تحويل إلى استجابة - استخدام الدالة المحدثة
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
            
            logger.info(f"✅ ✅ ✅ تم تسجيل المدرسة والمدير بنجاح! الأدوار: {roles}")
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
            password_valid = self._verify_password(password, user.password_hash)
            
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
            
            # 4. الحصول على الأدوار - استخدام الدالة المحدثة
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
            
            logger.info(f"✅ ✅ ✅ تسجيل الدخول ناجح: {user.email} - الأدوار: {roles}")
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
    
    async def debug_get_all_roles(self, school_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """الحصول على جميع الأدوار للتحقق (لمدرسة معينة أو كل الأدوار)"""
        query = select(Role)
        if school_id:
            query = query.where(Role.school_id == school_id)
        
        result = await self.db.execute(query)
        roles = result.scalars().all()
        
        logger.info("=" * 60)
        logger.info("📋 جميع الأدوار في قاعدة البيانات:")
        
        roles_data = []
        for role in roles:
            role_info = {
                "id": role.id,
                "key": role.key,
                "name_ar": role.name_ar,
                "name_en": role.name_en,
                "school_id": role.school_id,
                "is_system": role.is_system,
            }
            roles_data.append(role_info)
            logger.info(f"  - ID: {role.id}, Key: '{role.key}', Name: '{role.name_ar}', School: {role.school_id}")
        
        logger.info("=" * 60)
        return roles_data
    
    async def debug_get_user_roles_direct(self, email: str) -> Dict[str, Any]:
        """التحقق المباشر من أدوار مستخدم معين (Debug)"""
        user = await self._get_user_by_email(email)
        if not user:
            return {"error": f"المستخدم غير موجود: {email}"}
        
        # استعلام مباشر
        from sqlalchemy import select
        from app.models.users import UserRole, Role
        
        result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        roles = result.scalars().all()
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "school_id": user.school_id,
                "is_active": user.is_active,
            },
            "roles": [
                {
                    "id": r.id,
                    "key": r.key,
                    "name_ar": r.name_ar,
                    "name_en": r.name_en,
                }
                for r in roles
            ],
            "roles_count": len(roles),
            "has_roles": len(roles) > 0,
        }
