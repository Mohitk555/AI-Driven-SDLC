"""Pydantic models for document."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Shared fields."""
    status: str = Field(default="active", max_length=50)


class DocumentCreate(DocumentBase):
    """Payload for creating a document."""


class DocumentResponse(DocumentBase):
    """Full representation returned by the API."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
