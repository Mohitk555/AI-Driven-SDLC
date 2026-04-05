"""Pydantic models for policy."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyBase(BaseModel):
    """Shared fields."""
    status: str = Field(default="active", max_length=50)


class PolicyCreate(PolicyBase):
    """Payload for creating a policy."""


class PolicyResponse(PolicyBase):
    """Full representation returned by the API."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
