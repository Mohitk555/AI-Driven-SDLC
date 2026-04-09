"""Pydantic v2 schemas for admin policy list and lifecycle actions."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class AdminPolicyItem(BaseModel):
    """Single row in the admin policy list table."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    id: int
    policy_number: str
    customer_name: str
    vehicle_summary: str
    coverage_type: str
    premium_amount: float
    status: str
    effective_date: date
    expiration_date: date


class AdminPolicyListResponse(BaseModel):
    """Paginated admin policy list."""

    items: list[AdminPolicyItem]
    total: int
    page: int
    page_size: int


class CancelPolicyRequest(BaseModel):
    """Request body for cancelling a policy."""

    reason: str = Field(..., min_length=1, max_length=1000)


class ReinstatePolicyRequest(BaseModel):
    """Request body for reinstating a policy."""

    reason: str = Field(..., min_length=1, max_length=1000)


class PolicyActionResponse(BaseModel):
    """Response after a lifecycle action (cancel/renew/reinstate)."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    id: int
    policy_number: str
    status: str
    effective_date: date
    expiration_date: date
    cancellation_reason: str | None = None
    cancellation_date: datetime | None = None
    reinstatement_reason: str | None = None
    reinstatement_date: datetime | None = None
    renewed_from_policy_id: int | None = None
    updated_at: datetime
