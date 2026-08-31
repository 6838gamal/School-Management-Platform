"""Session lifecycle API — state machine endpoints + substitute list/respond (JSON)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_permission
from app.core.exceptions import ForbiddenException, ValidationException
from app.services.session_lifecycle_service import SessionLifecycleService, INDICATOR_COLORS


router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


@router.get("/entry/{schedule_entry_id}")
async def get_entry_state(
    schedule_entry_id: str,
    date: str,
    user: CurrentUser = Depends(require_permission("session_lifecycle.view")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.session_lifecycle import SessionLifecycle
    row = (
        await db.execute(
            select(SessionLifecycle).where(
                SessionLifecycle.schedule_entry_id == schedule_entry_id,
                SessionLifecycle.date == date,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return {"status": "scheduled", **dict(INDICATOR_COLORS["scheduled"])}
    color, label = INDICATOR_COLORS.get(row.status, ("⚪", row.status))
    return {"id": row.id, "status": row.status, "indicator": color, "status_label": label}


@router.post("/transition")
async def transition(
    schedule_entry_id: str,
    date: str,
    to_status: str,
    notes: Optional[str] = None,
    substitute_teacher_id: Optional[str] = None,
    user: CurrentUser = Depends(require_permission("session_lifecycle.transition")),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionLifecycleService(db)
    try:
        row = await svc.transition(
            school_id=user.school_id,
            actor_id=user.id,
            actor_role=user.primary_role,
            user_permissions=user.permissions,
            schedule_entry_id=schedule_entry_id,
            date=date,
            to_status=to_status,
            notes=notes,
            substitute_teacher_id=substitute_teacher_id,
        )
    except ValidationException as e:
        raise HTTPException(409, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(403, detail=str(e))
    color, label = INDICATOR_COLORS.get(row.status, ("⚪", row.status))
    return {"status": row.status, "indicator": color, "status_label": label, "id": row.id}
