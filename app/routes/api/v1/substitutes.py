"""Substitute assignment API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.core.exceptions import ForbiddenException, ValidationException
from app.services.substitute_service import SubstituteService


router = APIRouter(prefix="/substitutes", tags=["substitutes"])


@router.get("/alternatives")
async def alternatives(
    schedule_entry_id: str,
    date: str,
    user: CurrentUser = Depends(require_permission("substitutes.view")),
    db: AsyncSession = Depends(get_db),
):
    svc = SubstituteService(db)
    try:
        return await svc.list_alternatives(
            school_id=user.school_id,
            schedule_entry_id=schedule_entry_id,
            date=date,
        )
    except ValidationException as e:
        raise HTTPException(404, detail=str(e))


@router.post("/request")
async def request_substitute(
    schedule_entry_id: str,
    absent_teacher_id: str,
    substitute_teacher_id: str,
    date: str,
    reason: str = "",
    user: CurrentUser = Depends(require_permission("substitutes.create")),
    db: AsyncSession = Depends(get_db),
):
    if "substitutes.create" not in user.permissions:
        raise ForbiddenException("لا تملك صلاحية تكليف معلم بديل")
    svc = SubstituteService(db)
    try:
        sa = await svc.request(
            school_id=user.school_id,
            actor_id=user.id,
            actor_role=user.primary_role,
            user_permissions=user.permissions,
            schedule_entry_id=schedule_entry_id,
            absent_teacher_id=absent_teacher_id,
            substitute_teacher_id=substitute_teacher_id,
            date=date,
            reason=reason,
        )
    except ValidationException as e:
        raise HTTPException(400, detail=str(e))
    return {"id": sa.id, "status": sa.status}


@router.post("/{assignment_id}/respond")
async def respond(
    assignment_id: str,
    accept: bool,
    reason: str = "",
    user: CurrentUser = Depends(require_permission("substitutes.respond")),
    db: AsyncSession = Depends(get_db),
):
    if "substitutes.respond" not in user.permissions:
        raise ForbiddenException("لا تملك صلاحية الرد على التكليف")
    svc = SubstituteService(db)
    try:
        sa = await svc.respond(
            school_id=user.school_id,
            actor_id=user.id,
            actor_role=user.primary_role,
            user_permissions=user.permissions,
            assignment_id=assignment_id,
            accept=accept,
            reason=reason,
        )
    except Exception as e:
        raise HTTPException(400, detail=str(e))
    return {"id": sa.id, "status": sa.status}
