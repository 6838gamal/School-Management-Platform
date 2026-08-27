from fastapi.templating import Jinja2Templates

# إنشاء متغير عام للتemplates
_templates = None

def get_templates():
    """الحصول على مثيل الـ templates"""
    return _templates

def set_templates(templates_instance: Jinja2Templates):
    """تعيين مثيل الـ templates للاستخدام في جميع أنحاء التطبيق"""
    global _templates
    _templates = templates_instance
    print(f"✅ تم تعيين templates بنجاح: {_templates is not None}")

# للتوافق مع الكود القديم
templates = None

def get_template_response(template_name: str, context: dict):
    """دالة مساعدة للحصول على TemplateResponse مع التحقق من وجود templates"""
    if _templates is None:
        raise RuntimeError("Templates not initialized. Call set_templates() first.")
    return _templates.TemplateResponse(template_name, context)
