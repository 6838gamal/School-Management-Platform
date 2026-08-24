"""Teachers API v1."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.schemas.teachers import AssignmentCreate, TeacherCreate, TeacherUpdate
from app.services.teacher_service import TeacherService

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("")
async def list_teachers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = "",
    user: CurrentUser = Depends(require_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    return await service.list_teachers(user.school_id, page, page_size, search or None)


@router.post("")
async def create_teacher(
    req: TeacherCreate,
    user: CurrentUser = Depends(require_permission("teachers.create")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    return await service.create_teacher(user.school_id, req)


@router.get("/{teacher_id}")
async def get_teacher(
    teacher_id: str,
    user: CurrentUser = Depends(require_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    return await service.get_teacher_detail(teacher_id)


@router.put("/{teacher_id}")
async def update_teacher(
    teacher_id: str,
    req: TeacherUpdate,
    user: CurrentUser = Depends(require_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    return await service.update_teacher(teacher_id, req)


@router.post("/assign")
async def assign_teacher(
    req: AssignmentCreate,
    user: CurrentUser = Depends(require_permission("teachers.assign")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    return await service.assign_teacher(req)
