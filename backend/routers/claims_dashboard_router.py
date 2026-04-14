"""Admin claims analytics dashboard endpoint."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.dashboard_schemas import ClaimsDashboardResponse
from backend.database import get_db
from backend.models import Claim, ClaimStatus, ClaimStatusHistory, ClaimType, User

router = APIRouter(
    prefix="/api/v1/admin/claims", tags=["Admin Claims Dashboard"]
)


@router.get("/dashboard", response_model=ClaimsDashboardResponse)
def get_claims_dashboard(
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
    claim_type: ClaimType | None = Query(None, alias="claimType"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ClaimsDashboardResponse:
    """Return aggregated claims statistics for the admin dashboard."""
    base = db.query(Claim)

    if date_from:
        base = base.filter(func.date(Claim.created_at) >= date_from)
    if date_to:
        base = base.filter(func.date(Claim.created_at) <= date_to)
    if claim_type:
        base = base.filter(Claim.claim_type == claim_type)

    # ── Total counts and amounts ────────────────────────────────────────
    stats = base.with_entities(
        func.count(Claim.id).label("total"),
        func.coalesce(func.sum(Claim.amount), 0.0).label("total_amount"),
        func.avg(Claim.amount).label("avg_amount"),
    ).first()

    total_claims: int = stats.total or 0
    total_amount: float = float(stats.total_amount)
    average_amount: float | None = (
        round(float(stats.avg_amount), 2) if stats.avg_amount else None
    )

    # ── Count by status ─────────────────────────────────────────────────
    status_rows = (
        base.with_entities(Claim.status, func.count(Claim.id))
        .group_by(Claim.status)
        .all()
    )
    count_by_status: dict[str, int] = {
        s.value: 0 for s in ClaimStatus
    }
    for status_val, cnt in status_rows:
        key = status_val.value if hasattr(status_val, "value") else status_val
        count_by_status[key] = cnt

    # ── Approved / rejected breakdown ───────────────────────────────────
    approved_count = count_by_status.get("approved", 0)
    rejected_count = count_by_status.get("rejected", 0)
    resolved = approved_count + rejected_count

    approval_rate: float | None = None
    rejection_rate: float | None = None
    if resolved > 0:
        approval_rate = round(approved_count / resolved * 100, 2)
        rejection_rate = round(rejected_count / resolved * 100, 2)

    # ── Average processing time ─────────────────────────────────────────
    average_processing_days = _compute_avg_processing_days(
        db, date_from, date_to, claim_type
    )

    return ClaimsDashboardResponse(
        total_claims=total_claims,
        count_by_status=count_by_status,
        total_amount=total_amount,
        average_amount=average_amount,
        approved_count=approved_count,
        rejected_count=rejected_count,
        approval_rate=approval_rate,
        rejection_rate=rejection_rate,
        average_processing_days=average_processing_days,
    )


def _compute_avg_processing_days(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    claim_type: ClaimType | None,
) -> float | None:
    """Compute average days from claim creation to first resolution.

    Resolution = first claim_status_history entry where new_status
    is 'approved' or 'rejected'.
    """
    from sqlalchemy import and_

    # Subquery: first resolution timestamp per claim
    resolution_sub = (
        db.query(
            ClaimStatusHistory.claim_id,
            func.min(ClaimStatusHistory.changed_at).label("resolved_at"),
        )
        .filter(
            ClaimStatusHistory.new_status.in_(["approved", "rejected"])
        )
        .group_by(ClaimStatusHistory.claim_id)
        .subquery()
    )

    query = (
        db.query(
            func.avg(
                func.julianday(resolution_sub.c.resolved_at)
                - func.julianday(Claim.created_at)
            ).label("avg_days")
        )
        .join(resolution_sub, Claim.id == resolution_sub.c.claim_id)
    )

    if date_from:
        query = query.filter(func.date(Claim.created_at) >= date_from)
    if date_to:
        query = query.filter(func.date(Claim.created_at) <= date_to)
    if claim_type:
        query = query.filter(Claim.claim_type == claim_type)

    result = query.scalar()
    if result is None:
        return None
    return round(float(result), 1)
