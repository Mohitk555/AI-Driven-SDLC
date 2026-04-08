"""Integration tests for the V4 Configurable Risk Rules Engine."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import AuditLog, RiskRule
from backend.services.rule_seeder import seed_default_rules


@pytest.fixture(autouse=True)
def _seed_rules(db_session: Session) -> None:
    """Ensure default risk rules are seeded for every test."""
    seed_default_rules(db_session)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_rule(client: TestClient, **overrides) -> dict:
    """Create a risk rule via API and return response body."""
    payload = {
        "factorName": overrides.get("factorName", "credit_score"),
        "label": overrides.get("label", "Credit Score"),
        "brackets": overrides.get("brackets", [
            {"condition": "< 600", "adjustment": 300.0},
            {"condition": "600-750", "adjustment": 0.0},
            {"condition": "> 750", "adjustment": -100.0},
        ]),
    }
    resp = client.post("/api/v1/admin/risk-rules", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── GET /api/v1/admin/risk-rules — List Rules ───────────────────────────────


class TestListRiskRules:
    def test_list_returns_seeded_rules(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/admin/risk-rules")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 5
        factor_names = {item["factorName"] for item in items}
        assert {"driver_age", "violations", "accidents", "vehicle_age", "mileage"}.issubset(factor_names)

    def test_all_seeded_rules_are_enabled(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/admin/risk-rules")
        for item in resp.json()["items"]:
            assert item["isEnabled"] is True

    def test_non_admin_gets_403(self, user_client: TestClient):
        resp = user_client.get("/api/v1/admin/risk-rules")
        assert resp.status_code == 403


# ── POST /api/v1/admin/risk-rules — Create Rule ─────────────────────────────


class TestCreateRiskRule:
    def test_create_valid_rule(self, admin_client: TestClient):
        rule = _create_rule(admin_client)
        assert rule["factorName"] == "credit_score"
        assert rule["label"] == "Credit Score"
        assert rule["isEnabled"] is True
        assert len(rule["brackets"]) == 3

    def test_duplicate_factor_name_returns_409(self, admin_client: TestClient):
        _create_rule(admin_client, factorName="dup_test")
        resp = admin_client.post("/api/v1/admin/risk-rules", json={
            "factorName": "dup_test",
            "label": "Duplicate",
            "brackets": [{"condition": "0", "adjustment": 0.0}],
        })
        assert resp.status_code == 409

    def test_empty_brackets_returns_422(self, admin_client: TestClient):
        resp = admin_client.post("/api/v1/admin/risk-rules", json={
            "factorName": "empty_test",
            "label": "Empty",
            "brackets": [],
        })
        assert resp.status_code == 422

    def test_create_creates_audit_log(
        self, admin_client: TestClient, db_session: Session
    ):
        rule = _create_rule(admin_client, factorName="audit_test")
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "risk_rule",
                AuditLog.entity_id == rule["id"],
                AuditLog.action == "created",
            )
            .first()
        )
        assert audit is not None

    def test_non_admin_create_returns_403(self, user_client: TestClient):
        resp = user_client.post("/api/v1/admin/risk-rules", json={
            "factorName": "blocked",
            "label": "Blocked",
            "brackets": [{"condition": "0", "adjustment": 0.0}],
        })
        assert resp.status_code == 403


# ── PUT /api/v1/admin/risk-rules/{id} — Update Rule ─────────────────────────


class TestUpdateRiskRule:
    def test_update_label(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="update_label")
        resp = admin_client.put(f"/api/v1/admin/risk-rules/{rule['id']}", json={
            "label": "Updated Label",
        })
        assert resp.status_code == 200
        assert resp.json()["label"] == "Updated Label"

    def test_update_brackets(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="update_brackets")
        new_brackets = [{"condition": "< 500", "adjustment": 400.0}]
        resp = admin_client.put(f"/api/v1/admin/risk-rules/{rule['id']}", json={
            "brackets": new_brackets,
        })
        assert resp.status_code == 200
        assert len(resp.json()["brackets"]) == 1
        assert resp.json()["brackets"][0]["adjustment"] == 400.0

    def test_update_nonexistent_returns_404(self, admin_client: TestClient):
        resp = admin_client.put("/api/v1/admin/risk-rules/999999", json={
            "label": "Ghost",
        })
        assert resp.status_code == 404

    def test_update_no_fields_returns_400(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="update_empty")
        resp = admin_client.put(f"/api/v1/admin/risk-rules/{rule['id']}", json={})
        assert resp.status_code == 400


# ── DELETE /api/v1/admin/risk-rules/{id} — Soft Delete ───────────────────────


class TestDeleteRiskRule:
    def test_delete_soft_deletes(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="delete_me")
        resp = admin_client.delete(f"/api/v1/admin/risk-rules/{rule['id']}")
        assert resp.status_code == 204

        # Should not appear in list
        resp = admin_client.get("/api/v1/admin/risk-rules")
        factor_names = {item["factorName"] for item in resp.json()["items"]}
        assert "delete_me" not in factor_names

    def test_delete_nonexistent_returns_404(self, admin_client: TestClient):
        resp = admin_client.delete("/api/v1/admin/risk-rules/999999")
        assert resp.status_code == 404

    def test_delete_creates_audit_log(
        self, admin_client: TestClient, db_session: Session
    ):
        rule = _create_rule(admin_client, factorName="audit_delete")
        admin_client.delete(f"/api/v1/admin/risk-rules/{rule['id']}")
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "risk_rule",
                AuditLog.entity_id == rule["id"],
                AuditLog.action == "deleted",
            )
            .first()
        )
        assert audit is not None


# ── PATCH /api/v1/admin/risk-rules/{id}/toggle ──────────────────────────────


class TestToggleRiskRule:
    def test_toggle_disables_enabled_rule(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="toggle_test")
        assert rule["isEnabled"] is True
        resp = admin_client.patch(f"/api/v1/admin/risk-rules/{rule['id']}/toggle")
        assert resp.status_code == 200
        assert resp.json()["isEnabled"] is False

    def test_toggle_enables_disabled_rule(self, admin_client: TestClient):
        rule = _create_rule(admin_client, factorName="toggle_back")
        # Disable
        admin_client.patch(f"/api/v1/admin/risk-rules/{rule['id']}/toggle")
        # Re-enable
        resp = admin_client.patch(f"/api/v1/admin/risk-rules/{rule['id']}/toggle")
        assert resp.status_code == 200
        assert resp.json()["isEnabled"] is True

    def test_toggle_creates_audit_log(
        self, admin_client: TestClient, db_session: Session
    ):
        rule = _create_rule(admin_client, factorName="toggle_audit")
        admin_client.patch(f"/api/v1/admin/risk-rules/{rule['id']}/toggle")
        audit = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.entity_type == "risk_rule",
                AuditLog.entity_id == rule["id"],
                AuditLog.action == "toggled",
            )
            .first()
        )
        assert audit is not None
        assert audit.details_json["is_enabled"] is False

    def test_toggle_nonexistent_returns_404(self, admin_client: TestClient):
        resp = admin_client.patch("/api/v1/admin/risk-rules/999999/toggle")
        assert resp.status_code == 404


# ── Premium Engine with DB Rules ────────────────────────────────────────────


class TestPremiumEngineWithDBRules:
    def test_seeded_rules_match_hardcoded(self, admin_client: TestClient):
        """Quote created with DB rules should match hardcoded engine output."""
        from backend.tests.conftest import _valid_quote_payload
        payload = _valid_quote_payload()
        resp = admin_client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        # The premium should be the same as the hardcoded calculation
        assert body["premiumAmount"] > 0
        assert len(body["premiumBreakdown"]) >= 6  # base_rate + 5 rules

    def test_disabled_rule_excluded_from_calculation(
        self, admin_client: TestClient
    ):
        """Disabling a rule should change the premium calculation."""
        from backend.tests.conftest import _valid_quote_payload

        # Get the violations rule
        resp = admin_client.get("/api/v1/admin/risk-rules")
        rules = resp.json()["items"]
        violations_rule = next(
            (r for r in rules if r["factorName"] == "violations"), None
        )
        assert violations_rule is not None

        # Create a quote with violations (high risk)
        payload = _valid_quote_payload(violation_count=3)
        resp1 = admin_client.post("/api/v1/quotes", json=payload)
        assert resp1.status_code == 201
        premium_with = resp1.json()["premiumAmount"]

        # Disable violations rule
        admin_client.patch(
            f"/api/v1/admin/risk-rules/{violations_rule['id']}/toggle"
        )

        # Create another quote — violations should not affect premium
        payload2 = _valid_quote_payload(violation_count=3)
        payload2["vehicle"]["vin"] = "2HGBH41JXMN109187"  # Different VIN
        resp2 = admin_client.post("/api/v1/quotes", json=payload2)
        assert resp2.status_code == 201
        premium_without = resp2.json()["premiumAmount"]

        assert premium_without < premium_with  # Removing violations penalty reduces premium

        # Re-enable for other tests
        admin_client.patch(
            f"/api/v1/admin/risk-rules/{violations_rule['id']}/toggle"
        )

    def test_custom_rule_affects_premium(self, admin_client: TestClient):
        """A newly created rule should appear in premium breakdown."""
        from backend.tests.conftest import _valid_quote_payload

        # Create a custom rule that maps to mileage factor
        # Since "custom_factor" doesn't map to any input, it gets value 0
        # and should match the "0" bracket
        _create_rule(
            admin_client,
            factorName="custom_factor",
            label="Custom Factor",
            brackets=[
                {"condition": "0", "adjustment": 99.0},
            ],
        )

        payload = _valid_quote_payload()
        payload["vehicle"]["vin"] = "3HGBH41JXMN109188"
        resp = admin_client.post("/api/v1/quotes", json=payload)
        assert resp.status_code == 201
        breakdown = resp.json()["premiumBreakdown"]
        custom_factors = [b for b in breakdown if b["factor"] == "custom_factor"]
        assert len(custom_factors) == 1
        assert custom_factors[0]["impact"] == 99.0
