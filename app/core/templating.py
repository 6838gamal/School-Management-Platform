from fastapi.templating import Jinja2Templates

# إنشاء متغير عام للتemplates
templates = None

def set_templates(templates_instance: Jinja2Templates):
    """تعيين مثيل الـ templates للاستخدام في جميع أنحاء التطبيق"""
    global templates
    templates = templates_instance
    print("✅ تم تعيين templates بنجاح")
