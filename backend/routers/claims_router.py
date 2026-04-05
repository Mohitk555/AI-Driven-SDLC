"""Claims management routes: CRUD, status updates, history."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.auth import get_current_user, require_admin
from backend.database import get_db
from backend.models import (
    Claim,
    ClaimStatus,
    ClaimStatusHistory,
    ClaimType,
    User,
    UserRole,
)
from backend.schemas import (
    ClaimCreate,
    ClaimDetailResponse,
    ClaimResponse,
    ClaimStatusHistoryResponse,
    ClaimUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _claim_to_response(claim: Claim) -> ClaimResponse:
    """Map an ORM Claim to the response schema."""
    return ClaimResponse(
        id=claim.id,
        policy_number=claim.policy_number,
        claim_type=claim.claim_type,
        description=claim.description,
        amount=claim.amount,
        status=claim.status,
        filed_by=claim.filed_by,
        filed_by_name=claim.filed_by_user.full_name,
        assigned_to=claim.assigned_to,
        admin_notes=claim.admin_notes,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        document_count=len(claim.documents),
    )


def _claim_to_detail(claim: Claim) -> ClaimDetailResponse:
    """Map an ORM Claim to the detail response schema (with documents)."""
    return ClaimDetailResponse(
        id=claim.id,
        policy_number=claim.policy_number,
        claim_type=claim.claim_type,
        description=claim.description,
        amount=claim.amount,
        status=claim.status,
        filed_by=claim.filed_by,
        filed_by_name=claim.filed_by_user.full_name,
        assigned_to=claim.assigned_to,
        admin_notes=claim.admin_notes,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        document_count=len(claim.documents),
        documents=claim.documents,
    )


def _record_status_change(
    db: Session,
    claim: Claim,
    old_status: ClaimStatus | None,
    new_status: ClaimStatus,
    changed_by: int,
    notes: str | None = None,
) -> None:
    """Insert a row into the status-history audit table."""
    entry = ClaimStatusHistory(
        claim_id=claim.id,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
        changed_by=changed_by,
        notes=notes,
    )
    db.add(entry)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedResponse[ClaimResponse],
    summary="List claims (users see own, admins see all)",
)
def list_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    claim_status: ClaimStatus | None = Query(None, alias="status"),
    claim_type: ClaimType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated, filterable list of claims."""
    query = db.query(Claim).options(
        joinedload(Claim.filed_by_user),
        joinedload(Claim.documents),
    )

    # Non-admin users only see their own claims
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Claim.filed_by == current_user.id)

    if claim_status is not None:
        query = query.filter(Claim.status == claim_status)
    if claim_type is not None:
        query = query.filter(Claim.claim_type == claim_type)

    total = db.query(func.count(Claim.id)).filter(
        *([Claim.filed_by == current_user.id] if current_user.role != UserRole.ADMIN else []),
        *([Claim.status == claim_status] if claim_status else []),
        *([Claim.claim_type == claim_type] if claim_type else []),
    ).scalar() or 0

    claims = (
        query.order_by(Claim.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_claim_to_response(c) for c in claims],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a new claim",
)
def create_claim(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClaimResponse:
    """Create a new insurance claim with status 'submitted'."""
    claim = Claim(
        policy_number=payload.policy_number,
        claim_type=payload.claim_type,
        description=payload.description,
        amount=payload.amount,
        status=ClaimStatus.SUBMITTED,
        filed_by=current_user.id,
    )
    db.add(claim)
    db.flush()

    _record_status_change(
        db, claim, None, ClaimStatus.SUBMITTED, current_user.id, "Claim filed."
    )

    db.commit()
    db.refresh(claim)

    # Eagerly load the relationship for the response
    _ = claim.filed_by_user
    _ = claim.documents
    return _claim_to_response(claim)


@router.get(
    "/{claim_id}",
    response_model=ClaimDetailResponse,
    summary="Get claim detail with documents",
)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClaimDetailResponse:
    """Retrieve a single claim by ID, including its documents."""
    claim = (
        db.query(Claim)
        .options(
            joinedload(Claim.filed_by_user),
            joinedload(Claim.documents),
        )
        .filter(Claim.id == claim_id)
        .first()
    )
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Claim {claim_id} not found.",
            },
        )

    # Non-admin users can only view their own claims
    if current_user.role != UserRole.ADMIN and claim.filed_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this claim.",
            },
        )

    return _claim_to_detail(claim)


@router.put(
    "/{claim_id}",
    response_model=ClaimResponse,
    summary="Admin: update claim status / notes / assignment",
)
def update_claim(
    claim_id: int,
    payload: ClaimUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ClaimResponse:
    """Admin endpoint to approve, reject, request info, or reassign a claim."""
    claim = (
        db.query(Claim)
        .options(joinedload(Claim.filed_by_user), joinedload(Claim.documents))
        .filter(Claim.id == claim_id)
        .first()
    )
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Claim {claim_id} not found.",
            },
        )

    old_status = claim.status

    if payload.status is not None:
        claim.status = payload.status
    if payload.admin_notes is not None:
        claim.admin_notes = payload.admin_notes
    if payload.assigned_to is not None:
        # Verify the assignee exists and is an admin
        assignee = db.query(User).filter(User.id == payload.assigned_to).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://httpstatuses.com/404",
                    "title": "Not Found",
                    "detail": f"Assignee user {payload.assigned_to} not found.",
                },
            )
        claim.assigned_to = payload.assigned_to

    # Record status change if it actually changed
    if payload.status is not None and payload.status != old_status:
        _record_status_change(
            db, claim, old_status, payload.status, admin.id, payload.admin_notes
        )

    db.commit()
    db.refresh(claim)
    return _claim_to_response(claim)


@router.get(
    "/{claim_id}/status-history",
    response_model=list[ClaimStatusHistoryResponse],
    summary="Get status change history for a claim",
)
def get_status_history(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClaimStatusHistoryResponse]:
    """Return the ordered status-change audit trail for a claim."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Claim {claim_id} not found.",
            },
        )

    if current_user.role != UserRole.ADMIN and claim.filed_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://httpstatuses.com/403",
                "title": "Forbidden",
                "detail": "You do not have access to this claim.",
            },
        )

    history = (
        db.query(ClaimStatusHistory)
        .options(joinedload(ClaimStatusHistory.changed_by_user))
        .filter(ClaimStatusHistory.claim_id == claim_id)
        .order_by(ClaimStatusHistory.changed_at.asc())
        .all()
    )

    return [
        ClaimStatusHistoryResponse(
            id=h.id,
            claim_id=h.claim_id,
            old_status=h.old_status,
            new_status=h.new_status,
            changed_by=h.changed_by,
            changed_by_name=h.changed_by_user.full_name,
            notes=h.notes,
            changed_at=h.changed_at,
        )
        for h in history
    ]
