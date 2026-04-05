"""Pydantic models for notification."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    """Shared fields."""
    status: str = Field(default="active", max_length=50)


class NotificationCreate(NotificationBase):
    """Payload for creating a notification."""


class NotificationResponse(NotificationBase):
    """Full representation returned by the API."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
