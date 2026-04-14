"""Admin CRUD endpoints for configurable risk rules."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.database import get_db
from backend.models import AuditLog, RiskRule, User
from backend.risk_rule_schemas import (
    RiskRuleCreateRequest,
    RiskRuleListResponse,
    RiskRuleResponse,
    RiskRuleUpdateRequest,
)

router = APIRouter(prefix="/api/v1/admin/risk-rules", tags=["Admin Risk Rules"])


# ── Helpers ─────────────────────────────────────────────────────────────────


def _audit(
    db: Session,
    entity_id: int,
    action: str,
    actor_id: int,
    details: dict | None = None,
) -> None:
    """Write an audit log entry for a risk_rule change."""
    db.add(AuditLog(
        entity_type="risk_rule",
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        details_json=details,
    ))


def _rule_to_response(rule: RiskRule) -> RiskRuleResponse:
    """Map an ORM RiskRule to the response schema."""
    return RiskRuleResponse(
        id=rule.id,
        factor_name=rule.factor_name,
        label=rule.label,
        is_enabled=rule.is_enabled,
        brackets=rule.brackets_json,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _get_rule_or_404(db: Session, rule_id: int) -> RiskRule:
    """Return a non-deleted rule or raise 404."""
    rule = (
        db.query(RiskRule)
        .filter(RiskRule.id == rule_id, RiskRule.is_deleted == False)  # noqa: E712
        .first()
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://httpstatuses.com/404",
                "title": "Not Found",
                "detail": f"Risk rule {rule_id} not found.",
            },
        )
    return rule


# ── GET /api/v1/admin/risk-rules ────────────────────────────────────────────


@router.get("", response_model=RiskRuleListResponse)
def list_risk_rules(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> RiskRuleListResponse:
    """Return all non-deleted risk rules."""
    rules = (
        db.query(RiskRule)
        .filter(RiskRule.is_deleted == False)  # noqa: E712
        .order_by(RiskRule.id)
        .all()
    )
    return RiskRuleListResponse(items=[_rule_to_response(r) for r in rules])


# ── POST /api/v1/admin/risk-rules ───────────────────────────────────────────


@router.post(
    "",
    response_model=RiskRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_rule(
    body: RiskRuleCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RiskRuleResponse:
    """Create a new risk rule. 409 if factor_name already exists."""
    existing = (
        db.query(RiskRule)
        .filter(
            RiskRule.factor_name == body.factor_name,
            RiskRule.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://httpstatuses.com/409",
                "title": "Conflict",
                "detail": f"A risk rule with factor_name '{body.factor_name}' already exists.",
            },
        )

    brackets_raw = [b.model_dump() for b in body.brackets]
    rule = RiskRule(
        factor_name=body.factor_name,
        label=body.label,
        brackets_json=brackets_raw,
    )
    db.add(rule)
    db.flush()

    _audit(db, rule.id, "created", admin.id, {"factor_name": body.factor_name})
    db.commit()
    db.refresh(rule)
    return _rule_to_response(rule)


# ── PUT /api/v1/admin/risk-rules/{rule_id} ──────────────────────────────────


@router.put("/{rule_id}", response_model=RiskRuleResponse)
def update_risk_rule(
    rule_id: int,
    body: RiskRuleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RiskRuleResponse:
    """Update a risk rule's label and/or brackets."""
    rule = _get_rule_or_404(db, rule_id)
    changes: dict = {}

    if body.label is not None:
        changes["label"] = {"old": rule.label, "new": body.label}
        rule.label = body.label

    if body.brackets is not None:
        changes["brackets"] = "updated"
        rule.brackets_json = [b.model_dump() for b in body.brackets]

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://httpstatuses.com/400",
                "title": "Bad Request",
                "detail": "No fields to update.",
            },
        )

    _audit(db, rule.id, "updated", admin.id, changes)
    db.commit()
    db.refresh(rule)
    return _rule_to_response(rule)


# ── DELETE /api/v1/admin/risk-rules/{rule_id} ───────────────────────────────


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """Soft-delete a risk rule."""
    rule = _get_rule_or_404(db, rule_id)
    rule.is_deleted = True
    _audit(db, rule.id, "deleted", admin.id)
    db.commit()


# ── PATCH /api/v1/admin/risk-rules/{rule_id}/toggle ─────────────────────────


@router.patch("/{rule_id}/toggle", response_model=RiskRuleResponse)
def toggle_risk_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> RiskRuleResponse:
    """Toggle a risk rule's is_enabled flag."""
    rule = _get_rule_or_404(db, rule_id)
    rule.is_enabled = not rule.is_enabled
    _audit(
        db, rule.id, "toggled", admin.id,
        {"is_enabled": rule.is_enabled},
    )
    db.commit()
    db.refresh(rule)
    return _rule_to_response(rule)
