"""Pydantic v2 schemas for configurable risk rules (admin CRUD)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


# ── Shared sub-model ────────────────────────────────────────────────────────


class BracketItem(BaseModel):
    """A single condition/adjustment pair within a risk rule."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    condition: str = Field(..., min_length=1, max_length=100)
    adjustment: float


# ── Request schemas ─────────────────────────────────────────────────────────


class RiskRuleCreateRequest(BaseModel):
    """Body for creating a new risk rule."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    factor_name: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    brackets: list[BracketItem] = Field(..., min_length=1)


class RiskRuleUpdateRequest(BaseModel):
    """Body for updating an existing risk rule (partial)."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    label: str | None = Field(None, min_length=1, max_length=100)
    brackets: list[BracketItem] | None = Field(None, min_length=1)


# ── Response schemas ────────────────────────────────────────────────────────


class RiskRuleResponse(BaseModel):
    """Full representation of a risk rule returned to the client."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    id: int
    factor_name: str
    label: str
    is_enabled: bool
    brackets: list[BracketItem]
    created_at: datetime
    updated_at: datetime


class RiskRuleListResponse(BaseModel):
    """Wrapper for a list of risk rules."""

    items: list[RiskRuleResponse]
