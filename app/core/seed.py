"""Seed data for initial database setup."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.users import User, Role, Permission, UserRole
from app.models.schools import School
from app.core.security import hash_password
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, ROLE_LABELS


async def seed_database(db: AsyncSession):
    """إضافة بيانات تجريبية إلى قاعدة البيانات"""
    
    # 1. إنشاء مدرسة
    stmt = select(School).where(School.code == "SCHOOL001")
    result = await db.execute(stmt)
    school = result.scalar_one_or_none()
    
    if not school:
        school = School(
            name="مدرسة النموذج",
            code="SCHOOL001",
            onboarding_complete=True,
            is_active=True
        )
        db.add(school)
        await db.flush()
        print("✅ تم إنشاء المدرسة")
    
    # 2. إنشاء الصلاحيات
    for perm_def in PERMISSIONS:
        stmt = select(Permission).where(Permission.key == perm_def.key)
        result = await db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(
                key=perm_def.key,
                label_ar=perm_def.label_ar,
                label_en=perm_def.label_en,
                group=perm_def.group
            )
            db.add(perm)
    await db.flush()
    print("✅ تم إنشاء الصلاحيات")
    
    # 3. الحصول على جميع الصلاحيات
    stmt = select(Permission)
    result = await db.execute(stmt)
    all_perms = result.scalars().all()
    perm_dict = {p.key: p for p in all_perms}
    
    # 4. إنشاء الأدوار مع صلاحياتها
    for role_key, perm_keys in ROLE_PERMISSIONS.items():
        stmt = select(Role).where(
            Role.school_id == school.id,
            Role.key == role_key
        )
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            labels = ROLE_LABELS.get(role_key, {"ar": role_key, "en": role_key})
            role = Role(
                school_id=school.id,
                key=role_key,
                name_ar=labels["ar"],
                name_en=labels["en"],
                is_system=True
            )
            db.add(role)
            await db.flush()
            
            # إضافة الصلاحيات للدور
            for perm_key in perm_keys:
                if perm_key in perm_dict:
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=perm_dict[perm_key].id
                    )
                    db.add(role_permission)
    
    await db.flush()
    print("✅ تم إنشاء الأدوار والصلاحيات")
    
    # 5. إنشاء المستخدمين التجريبيين
    users_data = [
        {
            "email": "admin@school.edu",
            "password": "admin123",
            "full_name": "أحمد المدير",
            "role": "director"
        },
        {
            "email": "deputy@school.edu",
            "password": "deputy123",
            "full_name": "خالد الوكيل",
            "role": "deputy"
        },
        {
            "email": "activities@school.edu",
            "password": "activities123",
            "full_name": "سارة الأنشطة",
            "role": "activities_manager"
        },
        {
            "email": "teacher@school.edu",
            "password": "teacher123",
            "full_name": "محمد المعلم",
            "role": "teacher"
        }
    ]
    
    for user_data in users_data:
        stmt = select(User).where(User.email == user_data["email"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # إنشاء المستخدم
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                school_id=school.id,
                is_active=True
            )
            db.add(user)
            await db.flush()
            
            # تعيين الدور للمستخدم
            stmt = select(Role).where(
                Role.school_id == school.id,
                Role.key == user_data["role"]
            )
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            
            if role:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role.id
                )
                db.add(user_role)
            
            print(f"✅ تم إنشاء المستخدم: {user_data['email']} / {user_data['password']}")
    
    await db.commit()
    print("\n🎉 تم إعداد البيانات التجريبية بنجاح!")
    print("\n📝 بيانات تسجيل الدخول:")
    print("   👨‍💼 admin@school.edu / admin123 (مدير)")
    print("   👨‍🏫 deputy@school.edu / deputy123 (وكيل)")
    print("   🎯 activities@school.edu / activities123 (مسؤول أنشطة)")
    print("   📚 teacher@school.edu / teacher123 (معلم)")
