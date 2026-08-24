"""
Application entry point.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.exceptions import register_exception_handlers, set_templates
from app.routes.api.v1.auth import router as api_auth_router
from app.routes.api.v1.modules import (
    academics_router as api_academics,
    activities_router as api_activities,
    attendance_router as api_attendance,
    behavior_router as api_behavior,
    grades_router as api_grades,
    homework_router as api_homework,
    notifications_router as api_notifications,
    reports_router as api_reports,
    schedules_router as api_schedules,
)
from app.routes.api.v1.students import router as api_students_router
from app.routes.api.v1.teachers import router as api_teachers_router
from app.routes.web.academics import router as web_academics
from app.routes.web.auth import router as web_auth
from app.routes.web.dashboard import router as web_dashboard
from app.routes.web.modules import (
    activities_router as web_activities,
    attendance_router as web_attendance,
    behavior_router as web_behavior,
    grades_router as web_grades,
    homework_router as web_homework,
    notifications_router as web_notifications,
    reports_router as web_reports,
    schedules_router as web_schedules,
)
from app.routes.web.students import router as web_students
from app.routes.web.teachers import router as web_teachers

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_templates(templates)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

register_exception_handlers(app)

# ---- Web routes ----
app.include_router(web_auth)
app.include_router(web_dashboard)
app.include_router(web_students)
app.include_router(web_teachers)
app.include_router(web_academics)
app.include_router(web_attendance)
app.include_router(web_grades)
app.include_router(web_schedules)
app.include_router(web_homework)
app.include_router(web_activities)
app.include_router(web_behavior)
app.include_router(web_notifications)
app.include_router(web_reports)

# ---- API v1 routes ----
api_prefix = "/api/v1"
app.include_router(api_auth_router, prefix=api_prefix)
app.include_router(api_students_router, prefix=api_prefix)
app.include_router(api_teachers_router, prefix=api_prefix)
app.include_router(api_academics, prefix=api_prefix)
app.include_router(api_attendance, prefix=api_prefix)
app.include_router(api_grades, prefix=api_prefix)
app.include_router(api_schedules, prefix=api_prefix)
app.include_router(api_homework, prefix=api_prefix)
app.include_router(api_activities, prefix=api_prefix)
app.include_router(api_behavior, prefix=api_prefix)
app.include_router(api_notifications, prefix=api_prefix)
app.include_router(api_reports, prefix=api_prefix)


@app.get("/")
async def root(request: Request):
    return RedirectResponse("/login", status_code=302)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
