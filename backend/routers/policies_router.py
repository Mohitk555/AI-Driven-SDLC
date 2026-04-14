"""Policy management routes: purchase, list, detail, PDF download, renewal."""

import secrets
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import (
    AuditLog,
    Policy,
    PolicyStatus,
    Quote,
    QuoteStatus,
    User,
)
from backend.policy_schemas import (
    ExpiringPoliciesResponse,
    ExpiringPolicyItem,
    PaginatedResponse,
    PolicyCreateRequest,
    PolicyResponse,
    PolicySummaryResponse,
    PremiumBreakdownItem,
    RenewalPolicyResponse,
    RenewalPreviewResponse,
)
from backend.services.document_service import generate_policy_pdf
from backend.services.premium_engine import calculate_premium

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _generate_policy_number() -> str:
    """Return a unique policy number in POL-YYYYMMDD-XXXXX format."""
    today = date.today().strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()[:5]
    return f"POL-{today}-{suffix}"


def _get_renewed_to_id(db: Session, policy_id: int) -> int | None:
    """Return the ID of the policy that renewed this one, if any."""
    renewed = (
        db.query(Policy.id)
        .filter(Policy.renewed_from_policy_id == policy_id)
        .first()
    )
    return renewed[0] if renewed else None


def _policy_to_response(
    policy: Policy, quote: Quote, renewed_to_id: int | None = None
) -> PolicyResponse:
    """Map an ORM Policy + its Quote to the response schema."""
    return PolicyResponse(
        id=policy.id,
        policy_number=policy.policy_number,
        quote_id=policy.quote_id,
        status=policy.status,
        coverage_type=policy.coverage_type,
        premium_amount=policy.premium_amount,
        effective_date=policy.effective_date,
        expiration_date=policy.expiration_date,
        renewed_from_policy_id=policy.renewed_from_policy_id,
        renewed_to_policy_id=renewed_to_id,
        vehicle_make=quote.vehicle_make,
        vehicle_model=quote.vehicle_model,
        vehicle_year=quote.vehicle_year,
        vehicle_vin=quote.vehicle_vin,
        driver_first_name=quote.driver_first_name,
        driver_last_name=quote.driver_last_name,
        created_at=policy.created_at,
    )


def _policy_to_summary(policy: Policy, quote: Quote) -> PolicySummaryResponse:
    """Map an ORM Policy + its Quote to the summary schema."""
    vehicle_summary = f"{quote.vehicle_year} {quote.vehicle_make} {quote.vehicle_model}"
    return PolicySummaryResponse(
        id=policy.id,
        policy_number=policy.policy_number,
        coverage_type=policy.coverage_type,
        premium_amount=policy.premium_amount,
        status=policy.status,
        vehicle_summary=vehicle_summary,
        effective_date=policy.effective_date,
        expiration_date=policy.expiration_date,
    )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Purchase a policy from an existing quote",
)
def create_policy(
    payload: PolicyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyResponse:
    """Convert a pending quote into an active policy."""
    quote = db.query(Quote).filter(Quote.id == payload.quote_id).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Quote {payload.quote_id} not found.",
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

    if quote.status == QuoteStatus.PURCHASED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://httpstatuses.com/409",
                "title": "Conflict",
                "detail": "This quote has already been purchased.",
            },
        )

    expires_at = quote.expires_at if quote.expires_at.tzinfo else quote.expires_at.replace(tzinfo=timezone.utc)
    if quote.status == QuoteStatus.EXPIRED or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://httpstatuses.com/400",
                "title": "Bad Request",
                "detail": "This quote has expired. Please request a new quote.",
            },
        )

    effective = date.today()
    expiration = date(effective.year + 1, effective.month, effective.day)

    policy = Policy(
        policy_number=_generate_policy_number(),
        user_id=current_user.id,
        quote_id=quote.id,
        coverage_type=quote.coverage_type,
        premium_amount=quote.premium_amount,
        status=PolicyStatus.ACTIVE,
        effective_date=effective,
        expiration_date=expiration,
    )
    db.add(policy)

    quote.status = QuoteStatus.PURCHASED
    db.flush()

    db.add(AuditLog(
        entity_type="policy",
        entity_id=policy.id,
        action="created",
        actor_id=current_user.id,
        details_json={
            "quote_id": quote.id,
            "policy_number": policy.policy_number,
        },
    ))

    db.commit()
    db.refresh(policy)
    return _policy_to_response(policy, quote)


@router.get(
    "",
    response_model=PaginatedResponse[PolicySummaryResponse],
    summary="List current user's policies (paginated)",
)
def list_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated list of the authenticated user's policies."""
    base = db.query(Policy).filter(Policy.user_id == current_user.id)
    total: int = base.with_entities(func.count(Policy.id)).scalar() or 0

    policies = (
        base.order_by(Policy.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Pre-load quotes for summaries
    quote_ids = [p.quote_id for p in policies]
    quotes_map: dict[int, Quote] = {}
    if quote_ids:
        quotes = db.query(Quote).filter(Quote.id.in_(quote_ids)).all()
        quotes_map = {q.id: q for q in quotes}

    return {
        "items": [_policy_to_summary(p, quotes_map[p.quote_id]) for p in policies],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/expiring",
    response_model=ExpiringPoliciesResponse,
    summary="List user's policies expiring within 30 days",
)
def list_expiring_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpiringPoliciesResponse:
    """Return active/reinstated policies expiring within 30 days."""
    today = date.today()
    threshold = today + timedelta(days=30)

    policies = (
        db.query(Policy)
        .filter(
            Policy.user_id == current_user.id,
            Policy.status.in_([PolicyStatus.ACTIVE, PolicyStatus.REINSTATED]),
            Policy.expiration_date <= threshold,
            Policy.expiration_date >= today,
        )
        .order_by(Policy.expiration_date.asc())
        .all()
    )

    items = [
        ExpiringPolicyItem(
            id=p.id,
            policy_number=p.policy_number,
            coverage_type=p.coverage_type,
            premium_amount=p.premium_amount,
            expiration_date=p.expiration_date,
            days_until_expiry=(p.expiration_date - today).days,
        )
        for p in policies
    ]
    return ExpiringPoliciesResponse(items=items)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get policy detail",
)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyResponse:
    """Retrieve a single policy by ID (ownership check)."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Policy {policy_id} not found.",
            },
        )
    if policy.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this policy.",
            },
        )

    quote = db.query(Quote).filter(Quote.id == policy.quote_id).first()
    renewed_to_id = _get_renewed_to_id(db, policy.id)
    return _policy_to_response(policy, quote, renewed_to_id)  # type: ignore[arg-type]


@router.get(
    "/{policy_id}/document",
    summary="Download policy PDF document",
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_policy_document(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Generate and stream a policy PDF document."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Policy {policy_id} not found.",
            },
        )
    if policy.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this policy.",
            },
        )

    quote = db.query(Quote).filter(Quote.id == policy.quote_id).first()
    pdf_bytes = generate_policy_pdf(policy, quote)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{policy.policy_number}.pdf"'
        },
    )


# ── Renewal Endpoints ───────────────────────────────────────────────────────


def _get_user_policy_or_404(
    policy_id: int, db: Session, current_user: User
) -> Policy:
    """Fetch a policy, enforcing existence and ownership."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Policy {policy_id} not found.",
            },
        )
    if policy.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this policy.",
            },
        )
    return policy


def _check_already_renewed(db: Session, policy_id: int) -> None:
    """Raise 409 if the policy has already been renewed."""
    existing = (
        db.query(Policy.id)
        .filter(Policy.renewed_from_policy_id == policy_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://httpstatuses.com/409",
                "title": "Already Renewed",
                "detail": "This policy has already been renewed.",
                "renewedPolicyId": existing[0],
            },
        )


def _recalculate_premium(
    quote: Quote, policy: Policy
) -> tuple[float, list[dict]]:
    """Recalculate premium from the original quote data with current driver age."""
    return calculate_premium(
        coverage_type=policy.coverage_type,
        driver_dob=quote.driver_date_of_birth,
        violation_count=quote.driver_violation_count,
        accident_count=quote.driver_accident_count,
        vehicle_year=quote.vehicle_year,
        vehicle_mileage=quote.vehicle_mileage,
    )


@router.get(
    "/{policy_id}/renewal-preview",
    response_model=RenewalPreviewResponse,
    summary="Preview renewal premium recalculation",
)
def renewal_preview(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RenewalPreviewResponse:
    """Show the recalculated premium for a policy renewal."""
    policy = _get_user_policy_or_404(policy_id, db, current_user)

    if policy.status == PolicyStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://httpstatuses.com/400",
                "title": "Bad Request",
                "detail": "Cancelled policies cannot be renewed. Contact support to reinstate first.",
            },
        )

    _check_already_renewed(db, policy.id)

    quote = db.query(Quote).filter(Quote.id == policy.quote_id).first()
    new_premium, breakdown = _recalculate_premium(quote, policy)  # type: ignore[arg-type]

    today = date.today()
    return RenewalPreviewResponse(
        policy_id=policy.id,
        policy_number=policy.policy_number,
        current_premium=policy.premium_amount,
        renewal_premium=new_premium,
        premium_difference=round(new_premium - policy.premium_amount, 2),
        premium_breakdown=[
            PremiumBreakdownItem(
                factor=item["factor"],
                value=str(item["value"]),
                impact=item["impact"],
            )
            for item in breakdown
        ],
        coverage_type=policy.coverage_type,
        effective_date=today,
        expiration_date=today + timedelta(days=365),
    )


@router.post(
    "/{policy_id}/renew",
    response_model=RenewalPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Renew a policy (user self-service)",
)
def renew_policy_user(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RenewalPolicyResponse:
    """Create a new policy from an existing one with recalculated premium."""
    policy = _get_user_policy_or_404(policy_id, db, current_user)

    if policy.status == PolicyStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://httpstatuses.com/400",
                "title": "Bad Request",
                "detail": "Cancelled policies cannot be renewed. Contact support to reinstate first.",
            },
        )

    _check_already_renewed(db, policy.id)

    quote = db.query(Quote).filter(Quote.id == policy.quote_id).first()
    new_premium, breakdown = _recalculate_premium(quote, policy)  # type: ignore[arg-type]

    today = date.today()
    new_policy = Policy(
        policy_number=_generate_policy_number(),
        user_id=current_user.id,
        quote_id=policy.quote_id,
        coverage_type=policy.coverage_type,
        premium_amount=new_premium,
        status=PolicyStatus.ACTIVE,
        effective_date=today,
        expiration_date=today + timedelta(days=365),
        renewed_from_policy_id=policy.id,
        renewal_premium_breakdown_json=breakdown,
    )
    db.add(new_policy)
    db.flush()

    db.add(AuditLog(
        entity_type="policy",
        entity_id=new_policy.id,
        action="user_renewal",
        actor_id=current_user.id,
        details_json={
            "original_policy_id": policy.id,
            "original_policy_number": policy.policy_number,
            "original_premium": policy.premium_amount,
            "new_premium": new_premium,
            "premium_difference": round(new_premium - policy.premium_amount, 2),
        },
    ))

    db.commit()
    db.refresh(new_policy)

    return RenewalPolicyResponse(
        id=new_policy.id,
        policy_number=new_policy.policy_number,
        quote_id=new_policy.quote_id,
        status=new_policy.status,
        coverage_type=new_policy.coverage_type,
        premium_amount=new_policy.premium_amount,
        effective_date=new_policy.effective_date,
        expiration_date=new_policy.expiration_date,
        renewed_from_policy_id=new_policy.renewed_from_policy_id,
        renewed_to_policy_id=None,
        vehicle_make=quote.vehicle_make,
        vehicle_model=quote.vehicle_model,
        vehicle_year=quote.vehicle_year,
        vehicle_vin=quote.vehicle_vin,
        driver_first_name=quote.driver_first_name,
        driver_last_name=quote.driver_last_name,
        created_at=new_policy.created_at,
    )
