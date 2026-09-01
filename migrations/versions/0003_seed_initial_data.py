"""Seed initial data (roles and permissions)

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | None = None
depends_on:  str | None = None


def upgrade() -> None:
    """إضافة البيانات الأولية (الأدوار والصلاحيات)"""
    
    # الحصول على اتصال
    connection = op.get_bind()
    
    # ============================================================
    # 1. إضافة الصلاحيات
    # ============================================================
    permissions = [
        # Schools
        ('schools.view', 'عرض المدرسة', 'View school', 'schools'),
        ('schools.update', 'تعديل بيانات المدرسة', 'Update school', 'schools'),
        # Academic structure
        ('academics.view', 'عرض الهيكل الأكاديمي', 'View academic structure', 'academics'),
        ('academics.create', 'إنشاء عناصر أكاديمية', 'Create academic items', 'academics'),
        ('academics.update', 'تعديل عناصر أكاديمية', 'Update academic items', 'academics'),
        ('academics.delete', 'حذف عناصر أكاديمية', 'Delete academic items', 'academics'),
        # Users
        ('users.view', 'عرض المستخدمين', 'View users', 'users'),
        ('users.create', 'إنشاء مستخدم', 'Create user', 'users'),
        ('users.update', 'تعديل مستخدم', 'Update user', 'users'),
        ('users.delete', 'حذف مستخدم', 'Delete user', 'users'),
        ('users.assign_role', 'تعيين دور لمستخدم', 'Assign role to user', 'users'),
        # Students
        ('students.view', 'عرض الطلاب', 'View students', 'students'),
        ('students.create', 'إضافة طالب', 'Create student', 'students'),
        ('students.update', 'تعديل طالب', 'Update student', 'students'),
        ('students.delete', 'حذف طالب', 'Delete student', 'students'),
        # Teachers
        ('teachers.view', 'عرض المعلمين', 'View teachers', 'teachers'),
        ('teachers.create', 'إضافة معلم', 'Create teacher', 'teachers'),
        ('teachers.update', 'تعديل معلم', 'Update teacher', 'teachers'),
        ('teachers.assign', 'تكليف معلم', 'Assign teacher', 'teachers'),
        # Activities
        ('activities.view', 'عرض الأنشطة', 'View activities', 'activities'),
        ('activities.create', 'إنشاء نشاط', 'Create activity', 'activities'),
        ('activities.update', 'تعديل نشاط', 'Update activity', 'activities'),
        ('activities.delete', 'حذف نشاط', 'Delete activity', 'activities'),
        # Reports
        ('reports.view', 'عرض التقارير', 'View reports', 'reports'),
        ('reports.generate', 'إنشاء تقرير', 'Generate report', 'reports'),
        # Settings
        ('settings.view', 'عرض الإعدادات', 'View settings', 'settings'),
        ('settings.update', 'تعديل الإعدادات', 'Update settings', 'settings'),
    ]
    
    for key, label_ar, label_en, group in permissions:
        connection.execute(
            text("""
                INSERT INTO permissions (id, key, label_ar, label_en, group, created_at)
                VALUES (
                    UUID(),
                    :key,
                    :label_ar,
                    :label_en,
                    :group,
                    NOW()
                )
                ON DUPLICATE KEY UPDATE 
                    label_ar = :label_ar,
                    label_en = :label_en,
                    group = :group
            """),
            {
                "key": key,
                "label_ar": label_ar,
                "label_en": label_en,
                "group": group
            }
        )


def downgrade() -> None:
    """حذف البيانات الأولية"""
    connection = op.get_bind()
    
    # حذف الصلاحيات
    connection.execute(text("DELETE FROM permissions"))
