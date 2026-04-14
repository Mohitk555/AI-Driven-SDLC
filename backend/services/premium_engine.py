"""Configurable risk-rule premium calculation engine."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.models import CoverageType, RiskRule

# ── Base rates by coverage tier ──────────────────────────────────────────────

BASE_RATES: dict[CoverageType, float] = {
    CoverageType.BASIC: 800.0,
    CoverageType.FULL: 1500.0,
}

MINIMUM_PREMIUM = 300.0


# ── Hardcoded adjustment helpers (fallback when no DB) ──────────────────────


def _driver_age_adjustment(dob: date) -> dict[str, Any]:
    """Return adjustment based on driver age bracket."""
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 25:
        return {"factor": "driver_age", "value": f"{age} (under 25)", "impact": 200.0}
    if age > 65:
        return {"factor": "driver_age", "value": f"{age} (over 65)", "impact": 100.0}
    return {"factor": "driver_age", "value": f"{age} (25-65)", "impact": -50.0}


def _violation_adjustment(count: int) -> dict[str, Any]:
    """Return adjustment based on violation count."""
    if count == 0:
        return {"factor": "violations", "value": "0", "impact": 0.0}
    if count == 1:
        return {"factor": "violations", "value": "1", "impact": 150.0}
    return {"factor": "violations", "value": f"{count} (2+)", "impact": 350.0}


def _accident_adjustment(count: int) -> dict[str, Any]:
    """Return adjustment based on accident count."""
    if count == 0:
        return {"factor": "accidents", "value": "0", "impact": 0.0}
    if count == 1:
        return {"factor": "accidents", "value": "1", "impact": 200.0}
    return {"factor": "accidents", "value": f"{count} (2+)", "impact": 450.0}


def _vehicle_age_adjustment(vehicle_year: int) -> dict[str, Any]:
    """Return adjustment based on vehicle age."""
    vehicle_age = date.today().year - vehicle_year
    if vehicle_age < 3:
        return {"factor": "vehicle_age", "value": f"{vehicle_age}yr (<3)", "impact": 100.0}
    if vehicle_age <= 7:
        return {"factor": "vehicle_age", "value": f"{vehicle_age}yr (3-7)", "impact": 0.0}
    return {"factor": "vehicle_age", "value": f"{vehicle_age}yr (>7)", "impact": 75.0}


def _mileage_adjustment(mileage: int) -> dict[str, Any]:
    """Return adjustment based on annual mileage."""
    if mileage < 10_000:
        return {"factor": "mileage", "value": f"{mileage} (<10k)", "impact": -50.0}
    if mileage <= 30_000:
        return {"factor": "mileage", "value": f"{mileage} (10k-30k)", "impact": 0.0}
    return {"factor": "mileage", "value": f"{mileage} (>30k)", "impact": 100.0}


# ── Dynamic bracket evaluation ──────────────────────────────────────────────


def _resolve_input_value(
    factor_name: str,
    driver_dob: date,
    violation_count: int,
    accident_count: int,
    vehicle_year: int,
    vehicle_mileage: int,
) -> float | int:
    """Map a factor_name to its numeric input value."""
    if factor_name == "driver_age":
        today = date.today()
        return today.year - driver_dob.year - (
            (today.month, today.day) < (driver_dob.month, driver_dob.day)
        )
    if factor_name == "violations":
        return violation_count
    if factor_name == "accidents":
        return accident_count
    if factor_name == "vehicle_age":
        return date.today().year - vehicle_year
    if factor_name == "mileage":
        return vehicle_mileage
    return 0


def _match_bracket(
    value: float | int,
    brackets: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the first bracket whose condition matches the given value."""
    for bracket in brackets:
        condition: str = bracket["condition"].strip()
        if _condition_matches(value, condition):
            return bracket
    return None


def _condition_matches(value: float | int, condition: str) -> bool:
    """Evaluate whether *value* satisfies *condition*.

    Supported formats:
        "< 25", "> 65", "25-65", "0", "2+", "10000-30000"
    """
    # "< N" or "<N"
    m = re.match(r"^<\s*(\d+(?:\.\d+)?)$", condition)
    if m:
        return value < float(m.group(1))

    # "> N" or ">N"
    m = re.match(r"^>\s*(\d+(?:\.\d+)?)$", condition)
    if m:
        return value > float(m.group(1))

    # "N+" (N or more)
    m = re.match(r"^(\d+(?:\.\d+)?)\+$", condition)
    if m:
        return value >= float(m.group(1))

    # "A-B" range (inclusive)
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", condition)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return lo <= value <= hi

    # Exact match "N"
    m = re.match(r"^(\d+(?:\.\d+)?)$", condition)
    if m:
        return value == float(m.group(1))

    return False


def _evaluate_db_rules(
    db: Session,
    driver_dob: date,
    violation_count: int,
    accident_count: int,
    vehicle_year: int,
    vehicle_mileage: int,
) -> list[dict[str, Any]]:
    """Load enabled rules from DB and evaluate each against input values."""
    rules = (
        db.query(RiskRule)
        .filter(RiskRule.is_enabled == True, RiskRule.is_deleted == False)  # noqa: E712
        .all()
    )

    adjustments: list[dict[str, Any]] = []
    for rule in rules:
        input_val = _resolve_input_value(
            rule.factor_name, driver_dob, violation_count,
            accident_count, vehicle_year, vehicle_mileage,
        )
        matched = _match_bracket(input_val, rule.brackets_json)
        impact = matched["adjustment"] if matched else 0.0
        adjustments.append({
            "factor": rule.factor_name,
            "value": str(input_val),
            "impact": impact,
        })

    return adjustments


# ── Hardcoded fallback calculation ──────────────────────────────────────────


def _calculate_hardcoded(
    coverage_type: CoverageType,
    driver_dob: date,
    violation_count: int,
    accident_count: int,
    vehicle_year: int,
    vehicle_mileage: int,
) -> tuple[float, list[dict[str, Any]]]:
    """Original hardcoded premium calculation."""
    base = BASE_RATES[coverage_type]
    breakdown: list[dict[str, Any]] = [
        {"factor": "base_rate", "value": coverage_type.value, "impact": base},
    ]

    adjustments = [
        _driver_age_adjustment(driver_dob),
        _violation_adjustment(violation_count),
        _accident_adjustment(accident_count),
        _vehicle_age_adjustment(vehicle_year),
        _mileage_adjustment(vehicle_mileage),
    ]
    breakdown.extend(adjustments)

    total = base + sum(a["impact"] for a in adjustments)
    final = max(total, MINIMUM_PREMIUM)
    return round(final, 2), breakdown


# ── Public API ───────────────────────────────────────────────────────────────


def calculate_premium(
    coverage_type: CoverageType,
    driver_dob: date,
    violation_count: int,
    accident_count: int,
    vehicle_year: int,
    vehicle_mileage: int,
    db: Session | None = None,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate premium and return (amount, breakdown_items).

    When *db* is provided, enabled risk rules are loaded from the
    database.  Otherwise the original hardcoded logic is used as a
    backwards-compatible fallback.
    """
    if db is None:
        return _calculate_hardcoded(
            coverage_type, driver_dob, violation_count,
            accident_count, vehicle_year, vehicle_mileage,
        )

    base = BASE_RATES[coverage_type]
    breakdown: list[dict[str, Any]] = [
        {"factor": "base_rate", "value": coverage_type.value, "impact": base},
    ]

    adjustments = _evaluate_db_rules(
        db, driver_dob, violation_count,
        accident_count, vehicle_year, vehicle_mileage,
    )
    breakdown.extend(adjustments)

    total = base + sum(a["impact"] for a in adjustments)
    final = max(total, MINIMUM_PREMIUM)
    return round(final, 2), breakdown
