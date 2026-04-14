"""Quotes management routes: create, list, detail."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import AuditLog, Quote, QuoteStatus, User
from backend.policy_schemas import (
    PaginatedResponse,
    PremiumBreakdownItem,
    QuoteCreateRequest,
    QuoteResponse,
    QuoteSummaryResponse,
)
from backend.services.premium_engine import calculate_premium

router = APIRouter(prefix="/api/v1/quotes", tags=["Quotes"])

QUOTE_EXPIRY_DAYS = 30


# ── Helpers ──────────────────────────────────────────────────────────────────


def _quote_to_response(quote: Quote) -> QuoteResponse:
    """Map an ORM Quote to the full response schema."""
    breakdown = [
        PremiumBreakdownItem(**item)
        for item in (quote.premium_breakdown_json or [])
    ]
    return QuoteResponse(
        id=quote.id,
        premium_amount=quote.premium_amount,
        coverage_type=quote.coverage_type,
        status=quote.status,
        premium_breakdown=breakdown,
        vehicle_make=quote.vehicle_make,
        vehicle_model=quote.vehicle_model,
        vehicle_year=quote.vehicle_year,
        vehicle_vin=quote.vehicle_vin,
        vehicle_mileage=quote.vehicle_mileage,
        driver_first_name=quote.driver_first_name,
        driver_last_name=quote.driver_last_name,
        driver_date_of_birth=quote.driver_date_of_birth,
        driver_license_number=quote.driver_license_number,
        expires_at=quote.expires_at,
        created_at=quote.created_at,
    )


def _quote_to_summary(quote: Quote) -> QuoteSummaryResponse:
    """Map an ORM Quote to the summary response schema."""
    vehicle_summary = f"{quote.vehicle_year} {quote.vehicle_make} {quote.vehicle_model}"
    return QuoteSummaryResponse(
        id=quote.id,
        coverage_type=quote.coverage_type,
        premium_amount=quote.premium_amount,
        status=quote.status,
        vehicle_summary=vehicle_summary,
        created_at=quote.created_at,
    )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a new auto-insurance quote",
)
def create_quote(
    payload: QuoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteResponse:
    """Validate inputs, calculate premium, persist quote, and audit-log."""
    v = payload.vehicle
    d = payload.driver

    premium_amount, breakdown = calculate_premium(
        coverage_type=payload.coverage_type,
        driver_dob=d.date_of_birth,
        violation_count=d.driving_history.violation_count,
        accident_count=d.driving_history.accident_count,
        vehicle_year=v.year,
        vehicle_mileage=v.mileage,
        db=db,
    )

    quote = Quote(
        user_id=current_user.id,
        vehicle_make=v.make,
        vehicle_model=v.model,
        vehicle_year=v.year,
        vehicle_vin=v.vin,
        vehicle_mileage=v.mileage,
        driver_first_name=d.first_name,
        driver_last_name=d.last_name,
        driver_date_of_birth=d.date_of_birth,
        driver_license_number=d.license_number,
        driver_address_json=d.address.model_dump(),
        driver_accident_count=d.driving_history.accident_count,
        driver_violation_count=d.driving_history.violation_count,
        driver_years_licensed=d.driving_history.years_licensed,
        coverage_type=payload.coverage_type,
        premium_amount=premium_amount,
        premium_breakdown_json=breakdown,
        status=QuoteStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(days=QUOTE_EXPIRY_DAYS),
    )
    db.add(quote)
    db.flush()

    db.add(AuditLog(
        entity_type="quote",
        entity_id=quote.id,
        action="created",
        actor_id=current_user.id,
        details_json={"premium_amount": premium_amount},
    ))

    db.commit()
    db.refresh(quote)
    return _quote_to_response(quote)


@router.get(
    "",
    response_model=PaginatedResponse[QuoteSummaryResponse],
    summary="List current user's quotes (paginated)",
)
def list_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated list of the authenticated user's quotes."""
    base = db.query(Quote).filter(Quote.user_id == current_user.id)
    total: int = base.with_entities(func.count(Quote.id)).scalar() or 0

    quotes = (
        base.order_by(Quote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_quote_to_summary(q) for q in quotes],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Get quote detail",
)
def get_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteResponse:
    """Retrieve a single quote by ID (ownership check)."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Quote {quote_id} not found.",
            },
        )
    if quote.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this quote.",
            },
        )
    return _quote_to_response(quote)
