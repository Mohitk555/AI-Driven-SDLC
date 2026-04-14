"""Pydantic v2 schemas for auto-insurance quotes and policies."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from backend.models import CoverageType, PolicyStatus, QuoteStatus
from backend.schemas import PaginatedResponse  # noqa: F401 — re-exported for routers


def _camel_config(**extra: object) -> ConfigDict:
    """Shared config: camelCase aliases + populate_by_name."""
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        **extra,  # type: ignore[arg-type]
    )


# ── Nested Inputs ────────────────────────────────────────────────────────────


class AddressInput(BaseModel):
    model_config = _camel_config()

    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)


class DrivingHistoryInput(BaseModel):
    model_config = _camel_config()

    accident_count: int = Field(0, ge=0)
    violation_count: int = Field(0, ge=0)
    years_licensed: int = Field(0, ge=0)


class DriverInput(BaseModel):
    model_config = _camel_config()

    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    license_number: str = Field(..., min_length=1, max_length=50)
    address: AddressInput
    driving_history: DrivingHistoryInput

    @field_validator("date_of_birth")
    @classmethod
    def _driver_age_minimum(cls, v: date) -> date:
        from datetime import date as _date

        today = _date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 16:
            raise ValueError("Driver must be at least 16 years old.")
        return v


class VehicleInput(BaseModel):
    model_config = _camel_config()

    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int
    vin: str = Field(..., min_length=17, max_length=17)
    mileage: int = Field(..., ge=0)

    @field_validator("year")
    @classmethod
    def _year_not_future(cls, v: int) -> int:
        from datetime import date as _date

        if v > _date.today().year + 1:
            raise ValueError("Vehicle year cannot be in the future.")
        if v < 1900:
            raise ValueError("Vehicle year is unrealistic.")
        return v


# ── Quote Schemas ────────────────────────────────────────────────────────────


class QuoteCreateRequest(BaseModel):
    model_config = _camel_config()

    vehicle: VehicleInput
    driver: DriverInput
    coverage_type: CoverageType


class PremiumBreakdownItem(BaseModel):
    model_config = _camel_config()

    factor: str
    value: str
    impact: float


class QuoteResponse(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    premium_amount: float
    coverage_type: CoverageType
    status: QuoteStatus
    premium_breakdown: list[PremiumBreakdownItem]
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    vehicle_vin: str
    vehicle_mileage: int
    driver_first_name: str
    driver_last_name: str
    driver_date_of_birth: date
    driver_license_number: str
    expires_at: datetime
    created_at: datetime


class QuoteSummaryResponse(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    coverage_type: CoverageType
    premium_amount: float
    status: QuoteStatus
    vehicle_summary: str
    created_at: datetime


# ── Policy Schemas ───────────────────────────────────────────────────────────


class PolicyCreateRequest(BaseModel):
    model_config = _camel_config()

    quote_id: int


class PolicyResponse(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    policy_number: str
    quote_id: int
    status: PolicyStatus
    coverage_type: CoverageType
    premium_amount: float
    effective_date: date
    expiration_date: date
    renewed_from_policy_id: Optional[int] = None
    renewed_to_policy_id: Optional[int] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_vin: Optional[str] = None
    driver_first_name: Optional[str] = None
    driver_last_name: Optional[str] = None
    created_at: datetime


class PolicySummaryResponse(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    policy_number: str
    coverage_type: CoverageType
    premium_amount: float
    status: PolicyStatus
    vehicle_summary: str
    effective_date: date
    expiration_date: date


# ── Renewal Schemas ─────────────────────────────────────────────────────────


class ExpiringPolicyItem(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    policy_number: str
    coverage_type: CoverageType
    premium_amount: float
    expiration_date: date
    days_until_expiry: int


class ExpiringPoliciesResponse(BaseModel):
    model_config = _camel_config()

    items: list[ExpiringPolicyItem]


class RenewalPreviewResponse(BaseModel):
    model_config = _camel_config()

    policy_id: int
    policy_number: str
    current_premium: float
    renewal_premium: float
    premium_difference: float
    premium_breakdown: list[PremiumBreakdownItem]
    coverage_type: CoverageType
    effective_date: date
    expiration_date: date


class RenewalPolicyResponse(BaseModel):
    model_config = _camel_config(from_attributes=True)

    id: int
    policy_number: str
    quote_id: int
    status: PolicyStatus
    coverage_type: CoverageType
    premium_amount: float
    effective_date: date
    expiration_date: date
    renewed_from_policy_id: Optional[int] = None
    renewed_to_policy_id: Optional[int] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_vin: Optional[str] = None
    driver_first_name: Optional[str] = None
    driver_last_name: Optional[str] = None
    created_at: datetime
