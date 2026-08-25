"""Seed data for initial database setup."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.users import User, Role, Permission, UserRole, RolePermission
from app.models.schools import School
from app.core.security import hash_password
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, ROLE_LABELS


async def seed_database(db: AsyncSession):
    """
    إضافة بيانات تجريبية إلى قاعدة البيانات.
    
    يتم تشغيل هذه الدالة عند بدء تشغيل التطبيق لأول مرة.
    تتجنب إضافة بيانات مكررة عن طريق التحقق من وجود البيانات مسبقاً.
    """
    
    # التحقق من وجود مستخدمين مسبقاً - إذا وجدوا نخرج من الدالة
    stmt = select(User)
    result = await db.execute(stmt)
    existing_users = result.scalars().all()
    if existing_users:
        print("ℹ️ البيانات موجودة بالفعل، تخطي الإضافة")
        return
    
    print("🌱 جاري إضافة البيانات التجريبية...")
    
    # ============================================================
    # 1. إنشاء مدرسة
    # ============================================================
    school = School(
        name="مدرسة النموذج",
        code="SCHOOL001",
        onboarding_complete=True,
        is_active=True
    )
    db.add(school)
    await db.flush()
    print("✅ تم إنشاء المدرسة")
    
    # ============================================================
    # 2. إنشاء الصلاحيات من catalog
    # ============================================================
    for perm_def in PERMISSIONS:
        # التحقق من عدم وجود الصلاحية مسبقاً
        stmt = select(Permission).where(Permission.key == perm_def.key)
        result = await db.execute(stmt)
        existing_perm = result.scalar_one_or_none()
        if not existing_perm:
            perm = Permission(
                key=perm_def.key,
                label_ar=perm_def.label_ar,
                label_en=perm_def.label_en,
                group=perm_def.group
            )
            db.add(perm)
    await db.flush()
    print("✅ تم إنشاء الصلاحيات")
    
    # ============================================================
    # 3. جلب جميع الصلاحيات في قاموس للاستخدام السريع
    # ============================================================
    stmt = select(Permission)
    result = await db.execute(stmt)
    all_perms = result.scalars().all()
    perm_dict = {p.key: p for p in all_perms}
    
    # ============================================================
    # 4. إنشاء الأدوار مع صلاحياتها
    # ============================================================
    for role_key, perm_keys in ROLE_PERMISSIONS.items():
        # التحقق من عدم وجود الدور مسبقاً
        stmt = select(Role).where(
            Role.school_id == school.id,
            Role.key == role_key
        )
        result = await db.execute(stmt)
        existing_role = result.scalar_one_or_none()
        
        if not existing_role:
            # إنشاء الدور
            role = Role(
                school_id=school.id,
                key=role_key,
                name_ar=ROLE_LABELS.get(role_key, {}).get("ar", role_key),
                name_en=ROLE_LABELS.get(role_key, {}).get("en", role_key),
                description=f"دور {ROLE_LABELS.get(role_key, {}).get('ar', role_key)} في المدرسة",
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
            
            print(f"✅ تم إنشاء دور: {ROLE_LABELS.get(role_key, {}).get('ar', role_key)}")
    
    await db.flush()
    print("✅ تم إنشاء الأدوار والصلاحيات")
    
    # ============================================================
    # 5. إنشاء المستخدمين التجريبيين
    # ============================================================
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
        # التحقق من عدم وجود المستخدم مسبقاً
        stmt = select(User).where(User.email == user_data["email"])
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            # إنشاء المستخدم
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                school_id=school.id,
                is_active=True,
                phone=None,
                avatar_url=None
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
            
            print(f"✅ تم إنشاء المستخدم: {user_data['email']} (دور: {ROLE_LABELS.get(user_data['role'], {}).get('ar', user_data['role'])})")
    
    await db.commit()
    
    # ============================================================
    # 6. عرض ملخص البيانات
    # ============================================================
    print("\n" + "="*50)
    print("🎉 تم إعداد البيانات التجريبية بنجاح!")
    print("="*50)
    
    print("\n📝 بيانات تسجيل الدخول:")
    print("-" * 40)
    print("   👨‍💼 admin@school.edu / admin123 (مدير)")
    print("   👨‍🏫 deputy@school.edu / deputy123 (وكيل)")
    print("   🎯 activities@school.edu / activities123 (مسؤول أنشطة)")
    print("   📚 teacher@school.edu / teacher123 (معلم)")
    print("-" * 40)
    
    # عرض إحصائيات
    stmt = select(User)
    result = await db.execute(stmt)
    users_count = len(result.scalars().all())
    
    stmt = select(Role)
    result = await db.execute(stmt)
    roles_count = len(result.scalars().all())
    
    stmt = select(Permission)
    result = await db.execute(stmt)
    perms_count = len(result.scalars().all())
    
    print(f"\n📊 إحصائيات:")
    print(f"   🏫 مدرسة: 1")
    print(f"   👤 مستخدمين: {users_count}")
    print(f"   🎭 أدوار: {roles_count}")
    print(f"   🔑 صلاحيات: {perms_count}")
    print("="*50 + "\n")


async def reset_database(db: AsyncSession):
    """
    حذف جميع البيانات وإعادة تهيئتها.
    استخدم بحذر! هذا سيحذف جميع البيانات الموجودة.
    """
    print("⚠️ جاري حذف جميع البيانات...")
    
    # حذف بترتيب عكسي حسب العلاقات
    await db.execute(select(RolePermission).delete())
    await db.execute(select(UserRole).delete())
    await db.execute(select(User).delete())
    await db.execute(select(Role).delete())
    await db.execute(select(Permission).delete())
    await db.execute(select(School).delete())
    
    await db.commit()
    print("✅ تم حذف جميع البيانات")
    
    # إعادة الإضافة
    await seed_database(db)
