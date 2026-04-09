"""Integration tests for the V3 Policy Renewal API."""

import secrets
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import (
    CoverageType,
    Policy,
    PolicyStatus,
    Quote,
    QuoteStatus,
    User,
)
from backend.tests.conftest import _valid_quote_payload


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_quote(client: TestClient) -> dict:
    payload = _valid_quote_payload()
    resp = client.post("/api/v1/quotes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _purchase_policy(client: TestClient, quote_id: int) -> dict:
    resp = client.post("/api/v1/policies", json={"quoteId": quote_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_active_policy(client: TestClient) -> dict:
    quote = _create_quote(client)
    return _purchase_policy(client, quote["id"])


def _create_policy_in_db(
    db_session: Session, user: User, *, status: PolicyStatus = PolicyStatus.ACTIVE
) -> Policy:
    """Insert a quote + policy directly in the DB for a given user."""
    quote = Quote(
        user_id=user.id,
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=date.today().year - 2,
        vehicle_vin="1HGBH41JXMN109186",
        vehicle_mileage=15000,
        driver_first_name="Jane",
        driver_last_name="Doe",
        driver_date_of_birth=date(1990, 6, 15),
        driver_license_number="DL-12345678",
        driver_address_json={"street": "123 Main St", "city": "Austin", "state": "TX", "zip_code": "78701"},
        driver_accident_count=0,
        driver_violation_count=0,
        driver_years_licensed=10,
        coverage_type=CoverageType.BASIC,
        premium_amount=700.0,
        premium_breakdown_json=[{"factor": "base_rate", "value": "basic", "impact": 800.0}],
        status=QuoteStatus.PURCHASED,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(quote)
    db_session.flush()

    suffix = secrets.token_hex(3).upper()[:5]
    policy = Policy(
        policy_number=f"POL-{date.today().strftime('%Y%m%d')}-{suffix}",
        user_id=user.id,
        quote_id=quote.id,
        coverage_type=CoverageType.BASIC,
        premium_amount=700.0,
        status=status,
        effective_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


def _set_expiration(
    db_session: Session, policy_id: int, days_from_now: int
) -> None:
    """Update a policy's expiration date to N days from today."""
    policy = db_session.query(Policy).filter(Policy.id == policy_id).first()
    policy.expiration_date = date.today() + timedelta(days=days_from_now)
    db_session.commit()


# ── GET /api/v1/policies/expiring ────────────────────────────────────────────


class TestExpiringPolicies:
    def test_no_expiring_policies(self, client: TestClient):
        """No policies at all — empty list."""
        resp = client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []

    def test_policy_expiring_within_30_days(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        _set_expiration(db_session, policy["id"], days_from_now=15)

        resp = client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == policy["id"]
        assert items[0]["daysUntilExpiry"] == 15

    def test_policy_expiring_beyond_30_days_not_shown(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        _set_expiration(db_session, policy["id"], days_from_now=60)

        resp = client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_cancelled_policy_not_shown(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        _set_expiration(db_session, policy["id"], days_from_now=10)
        db_policy = db_session.query(Policy).filter(Policy.id == policy["id"]).first()
        db_policy.status = PolicyStatus.CANCELLED
        db_session.commit()

        resp = client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_policy_expiring_today_shown(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        _set_expiration(db_session, policy["id"], days_from_now=0)

        resp = client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["daysUntilExpiry"] == 0

    def test_other_user_policies_not_shown(
        self, other_client: TestClient, db_session: Session, test_user: User
    ):
        """Policy owned by test_user should not show for other_user."""
        policy = _create_policy_in_db(db_session, test_user)
        _set_expiration(db_session, policy.id, days_from_now=10)

        resp = other_client.get("/api/v1/policies/expiring")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ── GET /api/v1/policies/{id}/renewal-preview ────────────────────────────────


class TestRenewalPreview:
    def test_preview_returns_recalculated_premium(
        self, client: TestClient
    ):
        policy = _create_active_policy(client)
        resp = client.get(f"/api/v1/policies/{policy['id']}/renewal-preview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["policyId"] == policy["id"]
        assert body["policyNumber"] == policy["policyNumber"]
        assert "currentPremium" in body
        assert "renewalPremium" in body
        assert "premiumDifference" in body
        assert "premiumBreakdown" in body
        assert len(body["premiumBreakdown"]) > 0
        assert "effectiveDate" in body
        assert "expirationDate" in body

    def test_preview_cancelled_policy_returns_400(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        db_policy = db_session.query(Policy).filter(Policy.id == policy["id"]).first()
        db_policy.status = PolicyStatus.CANCELLED
        db_session.commit()

        resp = client.get(f"/api/v1/policies/{policy['id']}/renewal-preview")
        assert resp.status_code == 400

    def test_preview_already_renewed_returns_409(
        self, client: TestClient
    ):
        policy = _create_active_policy(client)
        # Renew the policy first
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 201
        # Now preview should fail
        resp = client.get(f"/api/v1/policies/{policy['id']}/renewal-preview")
        assert resp.status_code == 409

    def test_preview_nonexistent_policy_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/policies/999999/renewal-preview")
        assert resp.status_code == 404

    def test_preview_other_user_returns_403(
        self, other_client: TestClient, db_session: Session, test_user: User
    ):
        policy = _create_policy_in_db(db_session, test_user)
        resp = other_client.get(f"/api/v1/policies/{policy.id}/renewal-preview")
        assert resp.status_code == 403


# ── POST /api/v1/policies/{id}/renew ────────────────────────────────────────


class TestRenewPolicy:
    def test_renew_active_policy_creates_new_policy(
        self, client: TestClient
    ):
        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 201
        body = resp.json()
        assert body["policyNumber"].startswith("POL-")
        assert body["policyNumber"] != policy["policyNumber"]
        assert body["status"] == "active"
        assert body["renewedFromPolicyId"] == policy["id"]
        assert body["effectiveDate"] == str(date.today())
        assert "premiumAmount" in body

    def test_renewed_policy_has_12_month_term(self, client: TestClient):
        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        body = resp.json()
        effective = date.fromisoformat(body["effectiveDate"])
        expiration = date.fromisoformat(body["expirationDate"])
        diff = (expiration - effective).days
        assert 364 <= diff <= 366  # account for leap years

    def test_renew_cancelled_policy_returns_400(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        db_policy = db_session.query(Policy).filter(Policy.id == policy["id"]).first()
        db_policy.status = PolicyStatus.CANCELLED
        db_session.commit()

        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 400

    def test_renew_expired_policy_succeeds(
        self, client: TestClient, db_session: Session
    ):
        policy = _create_active_policy(client)
        db_policy = db_session.query(Policy).filter(Policy.id == policy["id"]).first()
        db_policy.status = PolicyStatus.EXPIRED
        db_session.commit()

        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 201

    def test_double_renewal_returns_409(self, client: TestClient):
        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 201
        # Second renewal attempt
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 409

    def test_renew_nonexistent_returns_404(self, client: TestClient):
        resp = client.post("/api/v1/policies/999999/renew")
        assert resp.status_code == 404

    def test_renew_other_user_returns_403(
        self, other_client: TestClient, db_session: Session, test_user: User
    ):
        policy = _create_policy_in_db(db_session, test_user)
        resp = other_client.post(f"/api/v1/policies/{policy.id}/renew")
        assert resp.status_code == 403

    def test_renewal_creates_audit_log(
        self, client: TestClient, db_session: Session
    ):
        from backend.models import AuditLog

        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        assert resp.status_code == 201
        new_policy_id = resp.json()["id"]

        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "policy",
                AuditLog.entity_id == new_policy_id,
                AuditLog.action == "user_renewal",
            )
            .first()
        )
        assert audit is not None
        assert audit.details_json["original_policy_id"] == policy["id"]
        assert "new_premium" in audit.details_json
        assert "original_premium" in audit.details_json


# ── GET /api/v1/policies/{id} — Renewal Chain ───────────────────────────────


class TestPolicyDetailRenewalChain:
    def test_renewed_policy_shows_renewed_from(self, client: TestClient):
        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        new_policy = resp.json()

        resp = client.get(f"/api/v1/policies/{new_policy['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["renewedFromPolicyId"] == policy["id"]

    def test_original_policy_shows_renewed_to(self, client: TestClient):
        policy = _create_active_policy(client)
        resp = client.post(f"/api/v1/policies/{policy['id']}/renew")
        new_policy = resp.json()

        resp = client.get(f"/api/v1/policies/{policy['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["renewedToPolicyId"] == new_policy["id"]

    def test_policy_without_renewal_has_null_chain(self, client: TestClient):
        policy = _create_active_policy(client)
        resp = client.get(f"/api/v1/policies/{policy['id']}")
        body = resp.json()
        assert body["renewedFromPolicyId"] is None
        assert body["renewedToPolicyId"] is None


# ── Auth tests (renewal endpoints) ──────────────────────────────────────────


class TestRenewalAuth:
    def test_expiring_no_token_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.get("/api/v1/policies/expiring")
        assert resp.status_code == 401

    def test_preview_no_token_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.get("/api/v1/policies/1/renewal-preview")
        assert resp.status_code == 401

    def test_renew_no_token_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.post("/api/v1/policies/1/renew")
        assert resp.status_code == 401
