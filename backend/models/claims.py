"""Pydantic models for claims."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClaimsBase(BaseModel):
    """Shared fields."""
    status: str = Field(default="active", max_length=50)


class ClaimsCreate(ClaimsBase):
    """Payload for creating a claims."""


class ClaimsResponse(ClaimsBase):
    """Full representation returned by the API."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
