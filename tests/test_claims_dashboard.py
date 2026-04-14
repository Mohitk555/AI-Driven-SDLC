"""Integration tests for the V5 Claims Analytics Dashboard."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import (
    Claim,
    ClaimStatus,
    ClaimStatusHistory,
    ClaimType,
    User,
    UserRole,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_claim(
    db: Session,
    user: User,
    *,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    claim_type: ClaimType = ClaimType.AUTO,
    amount: float = 1000.0,
    created_days_ago: int = 5,
) -> Claim:
    """Insert a claim with a given status and creation offset."""
    claim = Claim(
        policy_number="POL-TEST-00001",
        claim_type=claim_type,
        description="Test claim",
        amount=amount,
        status=status,
        filed_by=user.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=created_days_ago),
    )
    db.add(claim)
    db.flush()
    # Record initial status
    db.add(ClaimStatusHistory(
        claim_id=claim.id,
        old_status=None,
        new_status=ClaimStatus.SUBMITTED.value,
        changed_by=user.id,
        changed_at=claim.created_at,
    ))
    db.flush()
    return claim


def _resolve_claim(
    db: Session,
    claim: Claim,
    admin: User,
    new_status: str = "approved",
    days_after_creation: int = 3,
) -> None:
    """Add a resolution entry to status history."""
    resolved_at = claim.created_at + timedelta(days=days_after_creation)
    db.add(ClaimStatusHistory(
        claim_id=claim.id,
        old_status=claim.status.value,
        new_status=new_status,
        changed_by=admin.id,
        changed_at=resolved_at,
    ))
    claim.status = ClaimStatus(new_status)
    db.flush()


# ── Basic Dashboard Stats ───────────────────────────────────────────────────


class TestDashboardBasicStats:
    def test_empty_dashboard(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["totalClaims"] == 0
        assert body["totalAmount"] == 0.0
        assert body["averageAmount"] is None
        assert body["approvedCount"] == 0
        assert body["rejectedCount"] == 0
        assert body["approvalRate"] is None
        assert body["rejectionRate"] is None
        assert body["averageProcessingDays"] is None

    def test_single_claim(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user, amount=5000.0)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["totalClaims"] == 1
        assert body["totalAmount"] == 5000.0
        assert body["averageAmount"] == 5000.0

    def test_multiple_claims_counts(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user, amount=1000.0)
        _make_claim(db_session, regular_user, amount=3000.0)
        _make_claim(db_session, regular_user, amount=2000.0)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        body = resp.json()
        assert body["totalClaims"] == 3
        assert body["totalAmount"] == 6000.0
        assert body["averageAmount"] == 2000.0


# ── Approved / Rejected Breakdown ───────────────────────────────────────────


class TestApprovalRejection:
    def test_approval_rejection_rates(
        self,
        admin_client: TestClient,
        db_session: Session,
        regular_user: User,
        admin_user: User,
    ):
        c1 = _make_claim(db_session, regular_user)
        c2 = _make_claim(db_session, regular_user)
        c3 = _make_claim(db_session, regular_user)
        c4 = _make_claim(db_session, regular_user)
        _resolve_claim(db_session, c1, admin_user, "approved")
        _resolve_claim(db_session, c2, admin_user, "approved")
        _resolve_claim(db_session, c3, admin_user, "approved")
        _resolve_claim(db_session, c4, admin_user, "rejected")
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        body = resp.json()
        assert body["approvedCount"] == 3
        assert body["rejectedCount"] == 1
        assert body["approvalRate"] == 75.0
        assert body["rejectionRate"] == 25.0

    def test_no_resolved_rates_are_null(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user, status=ClaimStatus.SUBMITTED)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        body = resp.json()
        assert body["approvalRate"] is None
        assert body["rejectionRate"] is None


# ── Average Processing Time ─────────────────────────────────────────────────


class TestProcessingTime:
    def test_average_processing_days(
        self,
        admin_client: TestClient,
        db_session: Session,
        regular_user: User,
        admin_user: User,
    ):
        c1 = _make_claim(db_session, regular_user, created_days_ago=10)
        c2 = _make_claim(db_session, regular_user, created_days_ago=10)
        # c1 resolved in 2 days, c2 resolved in 6 days -> avg = 4.0
        _resolve_claim(db_session, c1, admin_user, "approved", days_after_creation=2)
        _resolve_claim(db_session, c2, admin_user, "rejected", days_after_creation=6)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        body = resp.json()
        assert body["averageProcessingDays"] == 4.0

    def test_no_resolved_processing_null(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        assert resp.json()["averageProcessingDays"] is None


# ── Count By Status ─────────────────────────────────────────────────────────


class TestCountByStatus:
    def test_status_breakdown(
        self,
        admin_client: TestClient,
        db_session: Session,
        regular_user: User,
        admin_user: User,
    ):
        c1 = _make_claim(db_session, regular_user, status=ClaimStatus.SUBMITTED)
        c2 = _make_claim(db_session, regular_user, status=ClaimStatus.SUBMITTED)
        c3 = _make_claim(db_session, regular_user, status=ClaimStatus.UNDER_REVIEW)
        c4 = _make_claim(db_session, regular_user)
        _resolve_claim(db_session, c4, admin_user, "approved")
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard")
        cbs = resp.json()["countByStatus"]
        assert cbs["submitted"] == 2
        assert cbs["under_review"] == 1
        assert cbs["approved"] == 1
        assert cbs["rejected"] == 0


# ── Filters ─────────────────────────────────────────────────────────────────


class TestDashboardFilters:
    def test_claim_type_filter(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user, claim_type=ClaimType.AUTO, amount=1000)
        _make_claim(db_session, regular_user, claim_type=ClaimType.HEALTH, amount=2000)
        _make_claim(db_session, regular_user, claim_type=ClaimType.AUTO, amount=3000)
        db_session.commit()

        resp = admin_client.get("/api/v1/admin/claims/dashboard?claimType=auto")
        body = resp.json()
        assert body["totalClaims"] == 2
        assert body["totalAmount"] == 4000.0

    def test_date_range_filter(
        self, admin_client: TestClient, db_session: Session, regular_user: User
    ):
        _make_claim(db_session, regular_user, created_days_ago=60, amount=500)
        _make_claim(db_session, regular_user, created_days_ago=5, amount=1500)
        db_session.commit()

        today = datetime.now(timezone.utc).date()
        date_from = (today - timedelta(days=30)).isoformat()
        resp = admin_client.get(
            f"/api/v1/admin/claims/dashboard?dateFrom={date_from}"
        )
        body = resp.json()
        assert body["totalClaims"] == 1
        assert body["totalAmount"] == 1500.0


# ── Security ────────────────────────────────────────────────────────────────


class TestDashboardSecurity:
    def test_non_admin_returns_403(self, user_client: TestClient):
        resp = user_client.get("/api/v1/admin/claims/dashboard")
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, unauth_client: TestClient):
        resp = unauth_client.get("/api/v1/admin/claims/dashboard")
        assert resp.status_code == 401
