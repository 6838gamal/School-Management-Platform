"""Web routes package."""
# Makes web a Python package
from app.routes.web.teachers import router as teachers_router

__all__ = ['teachers_router']
