"""Notification schemas."""
from app.schemas.common import ORMBase


class NotificationCreate(BaseModel):
    title: str
    body: str | None = None
    type: str = "info"
    audience: str = "user"  # user/role/school/teachers
    audience_role: str | None = None
    user_ids: list[str] = []


class NotificationOut(ORMBase):
    id: str
    school_id: str
    title: str
    body: str | None = None
    type: str
    audience: str
    audience_role: str | None = None
    created_by: str | None = None
    created_at: str


class NotificationRecipientOut(ORMBase):
    id: str
    notification_id: str
    user_id: str
    is_read: bool
    read_at: str | None = None
    notification: NotificationOut | None = None
