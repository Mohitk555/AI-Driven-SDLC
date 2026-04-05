"""Pydantic models for user."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Shared fields."""
    status: str = Field(default="active", max_length=50)


class UserCreate(UserBase):
    """Payload for creating a user."""


class UserResponse(UserBase):
    """Full representation returned by the API."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
