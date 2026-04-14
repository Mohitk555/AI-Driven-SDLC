"""Pydantic v2 schemas for the claims analytics dashboard."""

from pydantic import BaseModel, ConfigDict


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class ClaimsDashboardResponse(BaseModel):
    """Aggregated claims statistics for the admin dashboard."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    total_claims: int
    count_by_status: dict[str, int]
    total_amount: float
    average_amount: float | None
    approved_count: int
    rejected_count: int
    approval_rate: float | None
    rejection_rate: float | None
    average_processing_days: float | None
