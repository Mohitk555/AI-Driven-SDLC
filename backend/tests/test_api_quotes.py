"""Integration tests for the Quotes API (Suite A)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.tests.conftest import _valid_quote_payload


# ── TC-001: POST valid payload ───────────────────────────────────────────────


class TestCreateQuote:
    def test_valid_payload_returns_201(self, client: TestClient, valid_quote_payload: dict):
        resp = client.post("/api/v1/quotes", json=valid_quote_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["premiumAmount"] > 0
        assert body["coverageType"] == "basic"
        assert body["status"] == "pending"
        assert isinstance(body["premiumBreakdown"], list)
        assert len(body["premiumBreakdown"]) > 0
        assert "expiresAt" in body
        assert "createdAt" in body

    def test_valid_full_coverage(self, client: TestClient):
        payload = _valid_quote_payload(coverage_type="full")
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["coverageType"] == "full"
        # Full base is $1500, so premium should be higher than basic base ($800)
        assert body["premiumAmount"] >= 800

    def test_response_fields_match_input(self, client: TestClient, valid_quote_payload: dict):
        resp = client.post("/api/v1/quotes", json=valid_quote_payload)
        body = resp.json()
        assert body["vehicleMake"] == "Toyota"
        assert body["vehicleModel"] == "Camry"
        assert body["vehicleVin"] == "1HGBH41JXMN109186"
        assert body["driverFirstName"] == "Jane"
        assert body["driverLastName"] == "Doe"


# ── TC-002: Missing fields ──────────────────────────────────────────────────


class TestCreateQuoteValidation:
    def test_empty_body_returns_422(self, client: TestClient):
        resp = client.post("/api/v1/quotes", json={})
        assert resp.status_code == 422

    def test_missing_vehicle_returns_422(self, client: TestClient):
        payload = _valid_quote_payload()
        del payload["vehicle"]
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422

    def test_missing_driver_returns_422(self, client: TestClient):
        payload = _valid_quote_payload()
        del payload["driver"]
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422

    def test_missing_coverage_type_returns_422(self, client: TestClient):
        payload = _valid_quote_payload()
        del payload["coverageType"]
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422

    def test_invalid_vin_length_returns_422(self, client: TestClient):
        payload = _valid_quote_payload()
        payload["vehicle"]["vin"] = "SHORT"
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422


# ── TC-003: Future vehicle year ──────────────────────────────────────────────


class TestFutureVehicleYear:
    def test_far_future_year_returns_422(self, client: TestClient):
        payload = _valid_quote_payload(vehicle_year=date.today().year + 5)
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422

    def test_next_year_is_allowed(self, client: TestClient):
        """year + 1 is valid per the schema validator."""
        payload = _valid_quote_payload(vehicle_year=date.today().year + 1)
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 201


# ── TC-004: Underage driver ──────────────────────────────────────────────────


class TestUnderageDriver:
    def test_underage_driver_returns_422(self, client: TestClient):
        dob = date.today().replace(year=date.today().year - 10)
        payload = _valid_quote_payload(driver_dob=str(dob))
        resp = client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 422


# ── TC-005: GET list (paginated) ─────────────────────────────────────────────


class TestListQuotes:
    def test_empty_list(self, client: TestClient):
        resp = client.get("/api/v1/quotes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 20

    def test_list_returns_created_quotes(self, client: TestClient, valid_quote_payload: dict):
        client.post("/api/v1/quotes", json=valid_quote_payload)
        client.post("/api/v1/quotes", json=valid_quote_payload)
        resp = client.get("/api/v1/quotes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    def test_pagination_params(self, client: TestClient, valid_quote_payload: dict):
        # Create 3 quotes
        for _ in range(3):
            client.post("/api/v1/quotes", json=valid_quote_payload)
        resp = client.get("/api/v1/quotes", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2


# ── TC-006: GET detail ───────────────────────────────────────────────────────


class TestGetQuoteDetail:
    def test_existing_quote(self, client: TestClient, valid_quote_payload: dict):
        create_resp = client.post("/api/v1/quotes", json=valid_quote_payload)
        quote_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/quotes/{quote_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == quote_id
        assert body["premiumAmount"] > 0


# ── TC-007: Non-existent quote ───────────────────────────────────────────────


class TestGetQuoteNotFound:
    def test_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/quotes/999999")
        assert resp.status_code == 404


# ── TC-008: No auth token ───────────────────────────────────────────────────


class TestQuotesAuth:
    def test_no_token_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.get("/api/v1/quotes")
        assert resp.status_code == 401

    def test_no_token_post_returns_401(self, unauthed_client: TestClient):
        resp = unauthed_client.post("/api/v1/quotes", json={})
        assert resp.status_code == 401
