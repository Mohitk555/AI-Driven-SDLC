"""Seed default risk rules into the database on first startup."""

from sqlalchemy.orm import Session

from backend.models import RiskRule

# ── Default rule definitions ────────────────────────────────────────────────

DEFAULT_RULES: list[dict] = [
    {
        "factor_name": "driver_age",
        "label": "Driver Age",
        "brackets_json": [
            {"condition": "< 25", "adjustment": 200.0},
            {"condition": "25-65", "adjustment": -50.0},
            {"condition": "> 65", "adjustment": 100.0},
        ],
    },
    {
        "factor_name": "violations",
        "label": "Violation Count",
        "brackets_json": [
            {"condition": "0", "adjustment": 0.0},
            {"condition": "1", "adjustment": 150.0},
            {"condition": "2+", "adjustment": 350.0},
        ],
    },
    {
        "factor_name": "accidents",
        "label": "Accident Count",
        "brackets_json": [
            {"condition": "0", "adjustment": 0.0},
            {"condition": "1", "adjustment": 200.0},
            {"condition": "2+", "adjustment": 450.0},
        ],
    },
    {
        "factor_name": "vehicle_age",
        "label": "Vehicle Age",
        "brackets_json": [
            {"condition": "< 3", "adjustment": 100.0},
            {"condition": "3-7", "adjustment": 0.0},
            {"condition": "> 7", "adjustment": 75.0},
        ],
    },
    {
        "factor_name": "mileage",
        "label": "Annual Mileage",
        "brackets_json": [
            {"condition": "< 10000", "adjustment": -50.0},
            {"condition": "10000-30000", "adjustment": 0.0},
            {"condition": "> 30000", "adjustment": 100.0},
        ],
    },
]


def seed_default_rules(db: Session) -> None:
    """Insert default risk rules if the table is empty.

    This is safe to call on every startup; it only inserts when zero
    rows exist in the risk_rules table.
    """
    count = db.query(RiskRule).count()
    if count > 0:
        return

    for rule_data in DEFAULT_RULES:
        db.add(RiskRule(**rule_data))

    db.commit()
