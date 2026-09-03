"""0026__Add_attendance_status_and_attendance_updated_at_to_students_table

Revision ID: add_attendance_fields
Revises: previous_revision
Create Date: 2026-09-03 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = '0026'
down_revision = '0025'  # استبدل بالـ revision السابق
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في الجدول"""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول"""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """✅ تطبيق التغييرات على قاعدة البيانات"""
    
    # ============================================================
    # 1️⃣ إضافة أعمدة attendance_status و attendance_updated_at
    # ============================================================
    
    # ✅ التحقق من وجود جدول students
    if not _table_exists('students'):
        print("⚠️ جدول 'students' غير موجود، يتم إنشاؤه...")
        # سيتم إنشاء الجدول بواسطة migrations سابقة
        return
    
    # ✅ إضافة عمود attendance_status
    if not _column_exists('students', 'attendance_status'):
        op.add_column(
            'students',
            sa.Column(
                'attendance_status',
                sa.String(20),
                nullable=True,
                comment='حالة الحضور: present, absent, late, permitted, excused'
            )
        )
        print("✅ تم إضافة عمود 'attendance_status'")
    else:
        print("ℹ️ عمود 'attendance_status' موجود بالفعل")
    
    # ✅ إضافة عمود attendance_updated_at
    if not _column_exists('students', 'attendance_updated_at'):
        op.add_column(
            'students',
            sa.Column(
                'attendance_updated_at',
                sa.DateTime(),
                nullable=True,
                comment='تاريخ آخر تحديث لحالة الحضور'
            )
        )
        print("✅ تم إضافة عمود 'attendance_updated_at'")
    else:
        print("ℹ️ عمود 'attendance_updated_at' موجود بالفعل")
    
    # ============================================================
    # 2️⃣ تحديث القيم الافتراضية للطلاب الحاليين
    # ============================================================
    
    # ✅ تحديث الطلاب الذين ليس لديهم حالة حضور
    op.execute(
        text("""
            UPDATE students 
            SET attendance_status = 'present' 
            WHERE attendance_status IS NULL
        """)
    )
    print("✅ تم تحديث حالة الحضور للطلاب الحاليين إلى 'present'")
    
    # ============================================================
    # 3️⃣ إضافة عمود grade_id إلى student_enrollments (إذا لم يكن موجوداً)
    # ============================================================
    
    if _table_exists('student_enrollments'):
        if not _column_exists('student_enrollments', 'grade_id'):
            op.add_column(
                'student_enrollments',
                sa.Column(
                    'grade_id',
                    sa.String(36),
                    nullable=True,
                    comment='معرف الصف'
                )
            )
            print("✅ تم إضافة عمود 'grade_id' إلى 'student_enrollments'")
        else:
            print("ℹ️ عمود 'grade_id' موجود بالفعل في 'student_enrollments'")
    
    # ============================================================
    # 4️⃣ حذف عمود class_id من student_enrollments (إذا كان موجوداً)
    # ============================================================
    
    if _table_exists('student_enrollments'):
        if _column_exists('student_enrollments', 'class_id'):
            op.drop_column('student_enrollments', 'class_id')
            print("✅ تم حذف عمود 'class_id' من 'student_enrollments'")
        else:
            print("ℹ️ عمود 'class_id' غير موجود في 'student_enrollments'")
    
    # ============================================================
    # 5️⃣ إنشاء فهارس (Indexes) لتحسين الأداء
    # ============================================================
    
    # ✅ فهرس على attendance_status
    if not _column_exists('students', 'attendance_status'):
        # إذا لم يتم إضافة العمود، لن نحتاج إلى فهرس
        pass
    else:
        # التحقق من وجود الفهرس
        conn = op.get_bind()
        inspector = inspect(conn)
        indexes = [idx['name'] for idx in inspector.get_indexes('students')]
        
        if 'idx_students_attendance_status' not in indexes:
            op.create_index(
                'idx_students_attendance_status',
                'students',
                ['attendance_status']
            )
            print("✅ تم إنشاء فهرس 'idx_students_attendance_status'")
        else:
            print("ℹ️ فهرس 'idx_students_attendance_status' موجود بالفعل")
        
        # ✅ فهرس مركب على attendance_status + is_active
        if 'idx_students_attendance_active' not in indexes:
            op.create_index(
                'idx_students_attendance_active',
                'students',
                ['attendance_status', 'is_active']
            )
            print("✅ تم إنشاء فهرس 'idx_students_attendance_active'")
        else:
            print("ℹ️ فهرس 'idx_students_attendance_active' موجود بالفعل")


def downgrade() -> None:
    """⬇️ التراجع عن التغييرات"""
    
    # ============================================================
    # 1️⃣ حذف فهارس attendance_status
    # ============================================================
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if _table_exists('students'):
        indexes = [idx['name'] for idx in inspector.get_indexes('students')]
        
        if 'idx_students_attendance_active' in indexes:
            op.drop_index('idx_students_attendance_active', table_name='students')
            print("✅ تم حذف فهرس 'idx_students_attendance_active'")
        
        if 'idx_students_attendance_status' in indexes:
            op.drop_index('idx_students_attendance_status', table_name='students')
            print("✅ تم حذف فهرس 'idx_students_attendance_status'")
    
    # ============================================================
    # 2️⃣ حذف أعمدة attendance_status و attendance_updated_at
    # ============================================================
    
    if _table_exists('students'):
        if _column_exists('students', 'attendance_updated_at'):
            op.drop_column('students', 'attendance_updated_at')
            print("✅ تم حذف عمود 'attendance_updated_at'")
        
        if _column_exists('students', 'attendance_status'):
            op.drop_column('students', 'attendance_status')
            print("✅ تم حذف عمود 'attendance_status'")
    
    # ============================================================
    # 3️⃣ استعادة عمود class_id (إذا كان موجوداً)
    # ============================================================
    
    if _table_exists('student_enrollments'):
        if not _column_exists('student_enrollments', 'class_id'):
            op.add_column(
                'student_enrollments',
                sa.Column(
                    'class_id',
                    sa.String(36),
                    nullable=True,
                    comment='معرف الفصل الدراسي'
                )
            )
            print("✅ تم استعادة عمود 'class_id' إلى 'student_enrollments'")
    
    # ============================================================
    # 4️⃣ حذف عمود grade_id من student_enrollments
    # ============================================================
    
    if _table_exists('student_enrollments'):
        if _column_exists('student_enrollments', 'grade_id'):
            op.drop_column('student_enrollments', 'grade_id')
            print("✅ تم حذف عمود 'grade_id' من 'student_enrollments'")


# ============================================================
# 🔧 دالة مساعدة للتحقق من حالة الترحيل
# ============================================================

def check_migration_status() -> dict:
    """
    التحقق من حالة الترحيل - يمكن استخدامها في سطر الأوامر
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    result = {
        'table_exists': False,
        'attendance_status_exists': False,
        'attendance_updated_at_exists': False,
        'grade_id_exists': False,
        'class_id_exists': False,
    }
    
    if _table_exists('students'):
        result['table_exists'] = True
        result['attendance_status_exists'] = _column_exists('students', 'attendance_status')
        result['attendance_updated_at_exists'] = _column_exists('students', 'attendance_updated_at')
    
    if _table_exists('student_enrollments'):
        result['grade_id_exists'] = _column_exists('student_enrollments', 'grade_id')
        result['class_id_exists'] = _column_exists('student_enrollments', 'class_id')
    
    return result
