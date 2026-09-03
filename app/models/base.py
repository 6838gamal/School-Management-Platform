"""Base model - القاعدة النموذجية لجميع النماذج"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from datetime import datetime
import uuid

# ============================================================
# ============ Base ============
# ============================================================

# استخدام Base الموجود في قاعدة البيانات
# إذا كان Base موجوداً في core/database.py
try:
    from app.core.database import Base
except ImportError:
    # إذا لم يكن موجوداً، نقوم بإنشائه
    Base = declarative_base()


# ============================================================
# ============ BaseModel ============
# ============================================================

class BaseModel:
    """
    القاعدة النموذجية لجميع النماذج
    
    تحتوي على الحقول المشتركة:
    - id: المعرف الفريد (UUID)
    - created_at: تاريخ الإنشاء
    - updated_at: تاريخ التحديث
    - is_active: هل النموذج نشط
    - is_deleted: هل تم حذفه (حذف منطقي)
    - created_by: من أنشأ
    - updated_by: من عدل
    """
    
    # ============ الحقول الأساسية ============
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # ============ الطوابع الزمنية ============
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # ============ حالة النموذج ============
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # ============ من قام بالإنشاء والتعديل ============
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    
    # ============ دوال مساعدة ============
    
    def to_dict(self) -> dict:
        """
        تحويل النموذج إلى قاموس
        
        Returns:
            dict: قاموس يحتوي على جميع الحقول
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def to_dict_with_relations(self, relations: list = None) -> dict:
        """
        تحويل النموذج إلى قاموس مع العلاقات
        
        Args:
            relations: قائمة بأسماء العلاقات المراد تضمينها
        
        Returns:
            dict: قاموس يحتوي على الحقول والعلاقات
        """
        data = self.to_dict()
        
        if relations:
            for relation in relations:
                if hasattr(self, relation):
                    rel = getattr(self, relation)
                    if rel:
                        if isinstance(rel, list):
                            data[relation] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in rel]
                        else:
                            data[relation] = rel.to_dict() if hasattr(rel, 'to_dict') else rel
        
        return data
    
    def update(self, **kwargs) -> None:
        """
        تحديث النموذج بالبيانات المقدمة
        
        Args:
            **kwargs: الحقول والقيم المراد تحديثها
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ['id', 'created_at', 'created_by']:
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def soft_delete(self, deleted_by: str = None) -> None:
        """
        حذف منطقي للنموذج
        
        Args:
            deleted_by: معرف من قام بالحذف
        """
        self.is_active = False
        self.is_deleted = True
        self.updated_at = datetime.now()
        if deleted_by:
            self.updated_by = deleted_by
    
    def restore(self) -> None:
        """استعادة النموذج بعد الحذف المنطقي"""
        self.is_active = True
        self.is_deleted = False
        self.updated_at = datetime.now()
    
    @property
    def is_active_label(self) -> str:
        """تسمية حالة النشاط"""
        return "✅ نشط" if self.is_active else "❌ غير نشط"
    
    @property
    def created_at_formatted(self) -> str:
        """تاريخ الإنشاء منسق"""
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def updated_at_formatted(self) -> str:
        """تاريخ التحديث منسق"""
        return self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"
    
    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id})"


# ============================================================
# ============ Mixins ============
# ============================================================

class TimestampMixin:
    """Mixin للطوابع الزمنية"""
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class SoftDeleteMixin:
    """Mixin للحذف المنطقي"""
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)


class AuditMixin:
    """Mixin لتتبع من قام بالتعديل"""
    
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)


# ============================================================
# ============ دوال مساعدة ============
# ============================================================

def generate_uuid() -> str:
    """توليد معرف UUID جديد"""
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """الحصول على الوقت الحالي"""
    return datetime.now()


# ============================================================
# ============ مثال على الاستخدام ============
# ============================================================

"""
مثال على كيفية استخدام BaseModel في نموذج:

from app.models.base import Base, BaseModel

class Holiday(Base, BaseModel):
    __tablename__ = "holidays"
    
    # الحقول الخاصة بالنموذج
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    
    # الحقول الموروثة من BaseModel:
    # id, created_at, updated_at, is_active, is_deleted, created_by, updated_by
"""
