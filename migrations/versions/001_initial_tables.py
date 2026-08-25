"""Initial tables for school management system

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """إنشاء جميع الجداول الأساسية."""
    
    # ============================================================
    # 1. جدول المدارس (schools)
    # ============================================================
    op.create_table(
        'schools',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('onboarding_complete', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('onboarding_step', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_schools_code', 'schools', ['code'], unique=True)
    op.create_index('ix_schools_id', 'schools', ['id'], unique=False)
    
    # ============================================================
    # 2. جدول المستخدمين (users)
    # ============================================================
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_login_at', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_school_id', 'users', ['school_id'], unique=False)
    
    # ============================================================
    # 3. جدول الأدوار (roles)
    # ============================================================
    op.create_table(
        'roles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=True),
        sa.Column('key', sa.String(50), nullable=False),
        sa.Column('name_ar', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)
    op.create_index('ix_roles_school_id', 'roles', ['school_id'], unique=False)
    
    # ============================================================
    # 4. جدول الصلاحيات (permissions)
    # ============================================================
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('label_ar', sa.String(200), nullable=False),
        sa.Column('label_en', sa.String(200), nullable=False),
        sa.Column('group', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_permissions_id', 'permissions', ['id'], unique=False)
    op.create_index('ix_permissions_key', 'permissions', ['key'], unique=True)
    
    # ============================================================
    # 5. جدول ربط الأدوار بالصلاحيات (role_permissions)
    # ============================================================
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('role_id', sa.String(36), nullable=False),
        sa.Column('permission_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_role_permissions_id', 'role_permissions', ['id'], unique=False)
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'], unique=False)
    
    # ============================================================
    # 6. جدول ربط المستخدمين بالأدوار (user_roles)
    # ============================================================
    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'], unique=False)
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    
    # ============================================================
    # 7. جدول السنوات الدراسية (academic_years)
    # ============================================================
    op.create_table(
        'academic_years',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_date', sa.String(50), nullable=False),
        sa.Column('end_date', sa.String(50), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_academic_years_id', 'academic_years', ['id'], unique=False)
    op.create_index('ix_academic_years_school_id', 'academic_years', ['school_id'], unique=False)
    
    # ============================================================
    # 8. جدول الصفوف (classes)
    # ============================================================
    op.create_table(
        'classes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('school_id', sa.String(36), nullable=False),
        sa.Column('academic_year_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('grade_level', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_classes_id', 'classes', ['id'], unique=False)
    op.create_index('ix_classes_school_id', 'classes', ['school_id'], unique=False)


def downgrade() -> None:
    """التراجع - حذف جميع الجداول."""
    op.drop_table('classes')
    op.drop_table('academic_years')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('schools')
