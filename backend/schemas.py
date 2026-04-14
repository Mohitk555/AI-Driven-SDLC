"""Pydantic v2 schemas for request/response validation."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.models import ClaimStatus, ClaimType, UserRole

T = TypeVar("T")


# ── Auth / Token ──────────────────────────────────────────────────────────────


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data decoded from a JWT token."""
    user_id: int | None = None
    email: str | None = None
    role: UserRole | None = None


# ── User ──────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


# ── Claim ─────────────────────────────────────────────────────────────────────


class ClaimCreate(BaseModel):
    """Schema for filing a new claim."""
    policy_number: str = Field(..., min_length=1, max_length=50)
    claim_type: ClaimType
    description: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)


class ClaimUpdate(BaseModel):
    """Schema for admin updating a claim."""
    status: ClaimStatus | None = None
    admin_notes: str | None = None
    assigned_to: int | None = None


class ClaimResponse(BaseModel):
    """Schema for claim in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_number: str
    claim_type: ClaimType
    description: str
    amount: float
    status: ClaimStatus
    filed_by: int
    filed_by_name: str
    assigned_to: int | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime
    document_count: int


class ClaimDetailResponse(ClaimResponse):
    """Claim response with embedded documents."""
    documents: list["DocumentResponse"] = []


# ── Status History ────────────────────────────────────────────────────────────


class ClaimStatusHistoryResponse(BaseModel):
    """Schema for a single status-change record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_id: int
    old_status: str | None
    new_status: str
    changed_by: int
    changed_by_name: str
    notes: str | None
    changed_at: datetime


# ── Document ──────────────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """Schema for document in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    uploaded_by: int
    uploaded_at: datetime


# ── Pagination ────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int


# Resolve forward references
ClaimDetailResponse.model_rebuild()
