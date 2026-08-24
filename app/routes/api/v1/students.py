"""Students API v1."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.schemas.common import MessageResponse
from app.schemas.students import StudentCreate, StudentUpdate, TransferRequest
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = "",
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    return await service.list_students(user.school_id, page, page_size, search or None)


@router.post("")
async def create_student(
    req: StudentCreate,
    user: CurrentUser = Depends(require_permission("students.create")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    return await service.create_student(user.school_id, req)


@router.get("/{student_id}")
async def get_student(
    student_id: str,
    user: CurrentUser = Depends(require_permission("students.view")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    return await service.get_student_detail(student_id)


@router.put("/{student_id}")
async def update_student(
    student_id: str,
    req: StudentUpdate,
    user: CurrentUser = Depends(require_permission("students.update")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    return await service.update_student(student_id, req)


@router.post("/transfer")
async def transfer_student(
    req: TransferRequest,
    user: CurrentUser = Depends(require_permission("students.transfer")),
    db: AsyncSession = Depends(get_db),
):
    service = StudentService(db)
    return await service.transfer_student(user.school_id, req)
