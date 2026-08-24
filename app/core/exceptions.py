"""Custom exception hierarchy and FastAPI exception handlers."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


class AppException(Exception):
    """Base application exception carrying an HTTP status and message."""

    status_code: int = 400
    default_message: str = "حدث خطأ"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    status_code = 404
    default_message = "العنصر غير موجود"


class ForbiddenException(AppException):
    status_code = 403
    default_message = "ليس لديك صلاحية للوصول"


class UnauthorizedException(AppException):
    status_code = 401
    default_message = "يجب تسجيل الدخول"


class ConflictException(AppException):
    status_code = 409
    default_message = "البيانات متضاربة"


class ValidationException(AppException):
    status_code = 422
    default_message = "بيانات غير صحيحة"


templates: Jinja2Templates | None = None


def set_templates(t: Jinja2Templates) -> None:
    global templates
    templates = t


def _is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api/")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ForbiddenException)
    async def _forbidden(request: Request, exc: ForbiddenException):
        if _is_api_request(request):
            return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
        if templates:
            return templates.TemplateResponse(
                "errors/403.html",
                {"request": request, "message": exc.message},
                status_code=403,
            )
        return JSONResponse({"detail": exc.message}, status_code=403)

    @app.exception_handler(UnauthorizedException)
    async def _unauthorized(request: Request, exc: UnauthorizedException):
        if _is_api_request(request):
            return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
        return RedirectResponse("/login?next=" + request.url.path, status_code=302)

    @app.exception_handler(NotFoundException)
    async def _not_found(request: Request, exc: NotFoundException):
        if _is_api_request(request):
            return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
        if templates:
            return templates.TemplateResponse(
                "errors/404.html",
                {"request": request, "message": exc.message},
                status_code=404,
            )
        return JSONResponse({"detail": exc.message}, status_code=404)

    @app.exception_handler(ConflictException)
    async def _conflict(request: Request, exc: ConflictException):
        if _is_api_request(request):
            return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
        if templates:
            return templates.TemplateResponse(
                "errors/error.html",
                {"request": request, "message": exc.message},
                status_code=409,
            )
        return JSONResponse({"detail": exc.message}, status_code=409)

    @app.exception_handler(AppException)
    async def _app_exc(request: Request, exc: AppException):
        if _is_api_request(request):
            return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
        if templates:
            return templates.TemplateResponse(
                "errors/error.html",
                {"request": request, "message": exc.message},
                status_code=exc.status_code,
            )
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
