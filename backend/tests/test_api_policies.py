"""Integration tests for the Policies API (Suite C)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import Quote, QuoteStatus
from backend.tests.conftest import _valid_quote_payload


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_quote(client: TestClient) -> dict:
    """Create a valid quote via the API and return its response body."""
    payload = _valid_quote_payload()
    resp = client.post("/api/v1/quotes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _purchase_policy(client: TestClient, quote_id: int) -> dict:
    """Purchase a policy from a quote and return its response body."""
    resp = client.post("/api/v1/policies", json={"quoteId": quote_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── TC-022: POST valid quoteId ───────────────────────────────────────────────


class TestCreatePolicy:
    def test_valid_quote_returns_201(self, client: TestClient):
        quote = _create_quote(client)
        resp = client.post("/api/v1/policies", json={"quoteId": quote["id"]})
        assert resp.status_code == 201
        body = resp.json()
        assert body["policyNumber"].startswith("POL-")
        assert body["status"] == "active"
        assert body["quoteId"] == quote["id"]
        assert body["coverageType"] == quote["coverageType"]
        assert body["premiumAmount"] == quote["premiumAmount"]
        assert "effectiveDate" in body
        assert "expirationDate" in body
        assert "createdAt" in body

    def test_policy_number_format(self, client: TestClient):
        quote = _create_quote(client)
        body = _purchase_policy(client, quote["id"])
        pn = body["policyNumber"]
        # Format: POL-YYYYMMDD-XXXXX
        parts = pn.split("-")
        assert parts[0] == "POL"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 5  # hex suffix

    def test_policy_carries_vehicle_driver_info(self, client: TestClient):
        quote = _create_quote(client)
        body = _purchase_policy(client, quote["id"])
        assert body["vehicleMake"] == "Toyota"
        assert body["vehicleModel"] == "Camry"
        assert body["driverFirstName"] == "Jane"
        assert body["driverLastName"] == "Doe"


# ── TC-023: Already purchased quote ──────────────────────────────────────────


class TestDuplicatePurchase:
    def test_already_purchased_returns_409(self, client: TestClient):
        quote = _create_quote(client)
        _purchase_policy(client, quote["id"])
        # Attempt to purchase the same quote again
        resp = client.post("/api/v1/policies", json={"quoteId": quote["id"]})
        assert resp.status_code == 409


# ── TC-024: Expired quote ────────────────────────────────────────────────────


class TestExpiredQuote:
    def test_expired_quote_returns_400(
        self, client: TestClient, sample_quote: Quote, db_session: Session
    ):
        """Mark the quote as expired and attempt to purchase."""
        sample_quote.status = QuoteStatus.EXPIRED
        db_session.commit()
        resp = client.post("/api/v1/policies", json={"quoteId": sample_quote.id})
        assert resp.status_code == 400

    def test_time_expired_quote_returns_400(
        self, client: TestClient, sample_quote: Quote, db_session: Session
    ):
        """Set expires_at to the past (status still PENDING but time-expired)."""
        sample_quote.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        resp = client.post("/api/v1/policies", json={"quoteId": sample_quote.id})
        assert resp.status_code == 400


# ── TC-025: Non-existent quote ───────────────────────────────────────────────


class TestNonExistentQuote:
    def test_returns_404(self, client: TestClient):
        resp = client.post("/api/v1/policies", json={"quoteId": 999999})
        assert resp.status_code == 404


# ── TC-026: GET list (paginated) ─────────────────────────────────────────────


class TestListPolicies:
    def test_empty_list(self, client: TestClient):
        resp = client.get("/api/v1/policies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_returns_created_policy(self, client: TestClient):
        quote = _create_quote(client)
        _purchase_policy(client, quote["id"])
        resp = client.get("/api/v1/policies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["policyNumber"].startswith("POL-")


# ── TC-027: GET detail ───────────────────────────────────────────────────────


class TestGetPolicyDetail:
    def test_existing_policy(self, client: TestClient):
        quote = _create_quote(client)
        policy = _purchase_policy(client, quote["id"])
        resp = client.get(f"/api/v1/policies/{policy['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == policy["id"]
        assert body["policyNumber"] == policy["policyNumber"]

    def test_nonexistent_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/policies/999999")
        assert resp.status_code == 404


# ── TC-028: Document download ────────────────────────────────────────────────


class TestPolicyDocument:
    def test_pdf_download(self, client: TestClient):
        quote = _create_quote(client)
        policy = _purchase_policy(client, quote["id"])
        resp = client.get(f"/api/v1/policies/{policy['id']}/document")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF files start with %PDF
        assert resp.content[:4] == b"%PDF"

    def test_document_nonexistent_policy_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/policies/999999/document")
        assert resp.status_code == 404


# ── TC-029: Ownership checks ────────────────────────────────────────────────


class TestPolicyOwnership:
    def test_other_user_get_detail_returns_403(
        self, client: TestClient, other_client: TestClient
    ):
        quote = _create_quote(client)
        policy = _purchase_policy(client, quote["id"])
        # other_client is authenticated as a different user
        resp = other_client.get(f"/api/v1/policies/{policy['id']}")
        assert resp.status_code == 403

    def test_other_user_document_returns_403(
        self, client: TestClient, other_client: TestClient
    ):
        quote = _create_quote(client)
        policy = _purchase_policy(client, quote["id"])
        resp = other_client.get(f"/api/v1/policies/{policy['id']}/document")
        assert resp.status_code == 403

    def test_other_user_purchase_others_quote_returns_403(
        self, client: TestClient, other_client: TestClient
    ):
        """other_user tries to purchase a quote owned by test_user."""
        quote = _create_quote(client)
        resp = other_client.post("/api/v1/policies", json={"quoteId": quote["id"]})
        assert resp.status_code == 403


# ── Auth tests (policies) ───────────────────────────────────────────────────


class TestPoliciesAuth:
    def test_no_token_list_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.get("/api/v1/policies")
        assert resp.status_code == 401

    def test_no_token_create_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.post("/api/v1/policies", json={"quoteId": 1})
        assert resp.status_code == 401
