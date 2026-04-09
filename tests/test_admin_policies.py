"""Tests for admin policy list and lifecycle actions (AISDLC-23)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import AuditLog, Policy, PolicyStatus


class TestAdminPolicyList:
    """Tests for GET /api/v1/admin/policies (REQ-007 / US-007)."""

    def test_list_all_policies(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-001: Admin can view paginated policy list."""
        resp = admin_client.get("/api/v1/admin/policies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "policyNumber" in item
        assert "customerName" in item
        assert "vehicleSummary" in item
        assert "status" in item

    def test_list_filter_by_status(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-002: Filter policies by status."""
        resp = admin_client.get("/api/v1/admin/policies?status=active")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "active"

    def test_list_search_by_policy_number(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-003: Search policies by policy number."""
        resp = admin_client.get(f"/api/v1/admin/policies?search={active_policy.policy_number}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_search_by_customer_name(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-004: Search policies by customer name."""
        resp = admin_client.get("/api/v1/admin/policies?search=John")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_non_admin_rejected(self, user_client: TestClient) -> None:
        """TC-005: Non-admin user gets 403."""
        resp = user_client.get("/api/v1/admin/policies")
        assert resp.status_code == 403


class TestCancelPolicy:
    """Tests for POST /api/v1/admin/policies/{id}/cancel (REQ-008 / US-008)."""

    def test_cancel_active_policy(self, admin_client: TestClient, active_policy: Policy, db_session: Session) -> None:
        """TC-006: Cancel an active policy with reason."""
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Customer requested cancellation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["cancellationReason"] == "Customer requested cancellation"
        assert data["cancellationDate"] is not None

    def test_cancel_already_cancelled_rejected(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-007: Cannot cancel an already cancelled policy."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "First cancellation"},
        )
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Second attempt"},
        )
        assert resp.status_code == 400

    def test_cancel_without_reason_rejected(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-008: Cancellation without reason is rejected."""
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": ""},
        )
        assert resp.status_code == 422

    def test_cancel_nonexistent_policy(self, admin_client: TestClient) -> None:
        """TC-009: Cancel non-existent policy returns 404."""
        resp = admin_client.post("/api/v1/admin/policies/99999/cancel", json={"reason": "test"})
        assert resp.status_code == 404

    def test_cancel_creates_audit_log(self, admin_client: TestClient, active_policy: Policy, db_session: Session) -> None:
        """TC-010: Cancel creates an audit log entry."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Audit test"},
        )
        db_session.expire_all()
        log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "policy",
            AuditLog.entity_id == active_policy.id,
            AuditLog.action == "cancel",
        ).first()
        assert log is not None
        assert log.details_json["reason"] == "Audit test"


class TestRenewPolicy:
    """Tests for POST /api/v1/admin/policies/{id}/renew (REQ-009 / US-009)."""

    def test_renew_active_policy(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-011: Renew an active policy creates a new one."""
        resp = admin_client.post(f"/api/v1/admin/policies/{active_policy.id}/renew")
        assert resp.status_code == 201
        data = resp.json()
        assert data["policyNumber"] != active_policy.policy_number
        assert data["status"] == "active"
        assert data["renewedFromPolicyId"] == active_policy.id

    def test_renew_cancelled_policy_rejected(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-012: Cannot renew a cancelled policy."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Cancel first"},
        )
        resp = admin_client.post(f"/api/v1/admin/policies/{active_policy.id}/renew")
        assert resp.status_code == 400

    def test_renew_nonexistent_policy(self, admin_client: TestClient) -> None:
        """TC-013: Renew non-existent policy returns 404."""
        resp = admin_client.post("/api/v1/admin/policies/99999/renew")
        assert resp.status_code == 404


class TestReinstatePolicy:
    """Tests for POST /api/v1/admin/policies/{id}/reinstate (REQ-010 / US-010)."""

    def test_reinstate_cancelled_policy(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-014: Reinstate a cancelled policy."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Cancel for test"},
        )
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/reinstate",
            json={"reason": "Customer paid overdue"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reinstated"
        assert data["reinstatementReason"] == "Customer paid overdue"

    def test_reinstate_active_policy_rejected(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-015: Cannot reinstate an active policy."""
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/reinstate",
            json={"reason": "Attempted reinstate"},
        )
        assert resp.status_code == 400

    def test_reinstate_without_reason_rejected(self, admin_client: TestClient, active_policy: Policy) -> None:
        """TC-016: Reinstatement without reason is rejected."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Cancel first"},
        )
        resp = admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/reinstate",
            json={"reason": ""},
        )
        assert resp.status_code == 422

    def test_reinstate_creates_audit_log(self, admin_client: TestClient, active_policy: Policy, db_session: Session) -> None:
        """TC-017: Reinstate creates an audit log entry."""
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/cancel",
            json={"reason": "Cancel for audit test"},
        )
        admin_client.post(
            f"/api/v1/admin/policies/{active_policy.id}/reinstate",
            json={"reason": "Reinstate audit test"},
        )
        db_session.expire_all()
        log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "policy",
            AuditLog.entity_id == active_policy.id,
            AuditLog.action == "reinstate",
        ).first()
        assert log is not None


class TestNonAdminAccess:
    """Security tests — admin endpoints reject non-admin users (NFR-001)."""

    def test_list_forbidden(self, user_client: TestClient) -> None:
        """TC-018: Regular user cannot list admin policies."""
        assert user_client.get("/api/v1/admin/policies").status_code == 403

    def test_cancel_forbidden(self, user_client: TestClient) -> None:
        """TC-019: Regular user cannot cancel policies."""
        assert user_client.post("/api/v1/admin/policies/1/cancel", json={"reason": "x"}).status_code == 403

    def test_renew_forbidden(self, user_client: TestClient) -> None:
        """TC-020: Regular user cannot renew policies."""
        assert user_client.post("/api/v1/admin/policies/1/renew").status_code == 403

    def test_reinstate_forbidden(self, user_client: TestClient) -> None:
        """TC-021: Regular user cannot reinstate policies."""
        assert user_client.post("/api/v1/admin/policies/1/reinstate", json={"reason": "x"}).status_code == 403
