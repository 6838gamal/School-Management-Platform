from fastapi.templating import Jinja2Templates

templates = None

def set_templates(templates_instance: Jinja2Templates):
    global templates
    templates = templates_instance
