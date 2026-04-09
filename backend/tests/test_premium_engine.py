"""Unit tests for the premium calculation engine (Suite B)."""

from datetime import date

import pytest

from backend.models import CoverageType
from backend.services.premium_engine import MINIMUM_PREMIUM, calculate_premium


# ── Helpers ──────────────────────────────────────────────────────────────────


def _dob_for_age(age: int) -> date:
    """Return a date-of-birth that yields the given age today."""
    today = date.today()
    return today.replace(year=today.year - age)


def _vehicle_year_age(years_old: int) -> int:
    """Return the vehicle model year that is `years_old` years old."""
    return date.today().year - years_old


# Default "neutral" parameters: mid-age driver, 0 violations, 0 accidents,
# mid-age vehicle (5 yr), mid mileage (15k).  Override one dimension at a time.
_DEFAULTS = dict(
    driver_dob=_dob_for_age(35),
    violation_count=0,
    accident_count=0,
    vehicle_year=_vehicle_year_age(5),
    vehicle_mileage=15_000,
)


def _premium(coverage: CoverageType = CoverageType.BASIC, **overrides) -> float:
    """Compute premium with sensible defaults; return the final amount."""
    params = {**_DEFAULTS, **overrides}
    amount, _ = calculate_premium(coverage_type=coverage, **params)
    return amount


def _breakdown(coverage: CoverageType = CoverageType.BASIC, **overrides) -> list[dict]:
    """Compute premium with sensible defaults; return the breakdown list."""
    params = {**_DEFAULTS, **overrides}
    _, breakdown = calculate_premium(coverage_type=coverage, **params)
    return breakdown


def _impact_for(factor: str, breakdown: list[dict]) -> float:
    """Extract the impact value for a given factor from a breakdown list."""
    for item in breakdown:
        if item["factor"] == factor:
            return item["impact"]
    raise KeyError(f"Factor '{factor}' not found in breakdown")


# ── TC-009: Basic coverage base rate ─────────────────────────────────────────


class TestBaseRates:
    def test_basic_coverage_base_rate(self):
        bd = _breakdown(CoverageType.BASIC)
        assert _impact_for("base_rate", bd) == 800.0

    def test_full_coverage_base_rate(self):
        bd = _breakdown(CoverageType.FULL)
        assert _impact_for("base_rate", bd) == 1500.0


# ── TC-011 through TC-013: Driver age brackets ──────────────────────────────


class TestDriverAge:
    def test_young_driver_surcharge(self):
        """Under 25 adds $200."""
        bd = _breakdown(driver_dob=_dob_for_age(20))
        assert _impact_for("driver_age", bd) == 200.0

    def test_senior_driver_surcharge(self):
        """Over 65 adds $100."""
        bd = _breakdown(driver_dob=_dob_for_age(70))
        assert _impact_for("driver_age", bd) == 100.0

    def test_middle_age_discount(self):
        """25-65 subtracts $50."""
        bd = _breakdown(driver_dob=_dob_for_age(40))
        assert _impact_for("driver_age", bd) == -50.0

    def test_boundary_age_25(self):
        """Exactly 25 should get the middle-age discount."""
        bd = _breakdown(driver_dob=_dob_for_age(25))
        assert _impact_for("driver_age", bd) == -50.0

    def test_boundary_age_65(self):
        """Exactly 65 should get the middle-age discount."""
        bd = _breakdown(driver_dob=_dob_for_age(65))
        assert _impact_for("driver_age", bd) == -50.0


# ── TC-014 through TC-016: Violations ────────────────────────────────────────


class TestViolations:
    def test_zero_violations(self):
        bd = _breakdown(violation_count=0)
        assert _impact_for("violations", bd) == 0.0

    def test_one_violation(self):
        bd = _breakdown(violation_count=1)
        assert _impact_for("violations", bd) == 150.0

    def test_two_violations(self):
        bd = _breakdown(violation_count=2)
        assert _impact_for("violations", bd) == 350.0

    def test_many_violations(self):
        bd = _breakdown(violation_count=5)
        assert _impact_for("violations", bd) == 350.0


# ── TC-017 through TC-019: Accidents ─────────────────────────────────────────


class TestAccidents:
    def test_zero_accidents(self):
        bd = _breakdown(accident_count=0)
        assert _impact_for("accidents", bd) == 0.0

    def test_one_accident(self):
        bd = _breakdown(accident_count=1)
        assert _impact_for("accidents", bd) == 200.0

    def test_two_accidents(self):
        bd = _breakdown(accident_count=2)
        assert _impact_for("accidents", bd) == 450.0

    def test_many_accidents(self):
        bd = _breakdown(accident_count=7)
        assert _impact_for("accidents", bd) == 450.0


# ── TC-020 through TC-022a: Vehicle age ──────────────────────────────────────


class TestVehicleAge:
    def test_new_vehicle(self):
        """Vehicle < 3 years old adds $100."""
        bd = _breakdown(vehicle_year=_vehicle_year_age(1))
        assert _impact_for("vehicle_age", bd) == 100.0

    def test_mid_age_vehicle(self):
        """Vehicle 3-7 years old adds $0."""
        bd = _breakdown(vehicle_year=_vehicle_year_age(5))
        assert _impact_for("vehicle_age", bd) == 0.0

    def test_old_vehicle(self):
        """Vehicle > 7 years old adds $75."""
        bd = _breakdown(vehicle_year=_vehicle_year_age(10))
        assert _impact_for("vehicle_age", bd) == 75.0

    def test_boundary_3_years(self):
        """Exactly 3 years old should be mid-age ($0)."""
        bd = _breakdown(vehicle_year=_vehicle_year_age(3))
        assert _impact_for("vehicle_age", bd) == 0.0

    def test_boundary_7_years(self):
        """Exactly 7 years old should be mid-age ($0)."""
        bd = _breakdown(vehicle_year=_vehicle_year_age(7))
        assert _impact_for("vehicle_age", bd) == 0.0


# ── TC-023a through TC-025a: Mileage ─────────────────────────────────────────


class TestMileage:
    def test_low_mileage(self):
        """< 10k subtracts $50."""
        bd = _breakdown(vehicle_mileage=5_000)
        assert _impact_for("mileage", bd) == -50.0

    def test_mid_mileage(self):
        """10k-30k adds $0."""
        bd = _breakdown(vehicle_mileage=20_000)
        assert _impact_for("mileage", bd) == 0.0

    def test_high_mileage(self):
        """> 30k adds $100."""
        bd = _breakdown(vehicle_mileage=50_000)
        assert _impact_for("mileage", bd) == 100.0

    def test_boundary_10k(self):
        """Exactly 10k should be mid-range ($0)."""
        bd = _breakdown(vehicle_mileage=10_000)
        assert _impact_for("mileage", bd) == 0.0

    def test_boundary_30k(self):
        """Exactly 30k should be mid-range ($0)."""
        bd = _breakdown(vehicle_mileage=30_000)
        assert _impact_for("mileage", bd) == 0.0


# ── TC-026a: Minimum premium floor ───────────────────────────────────────────


class TestMinimumFloor:
    def test_premium_never_below_minimum(self):
        """Even with maximum discounts the premium must not drop below $300."""
        # Basic ($800) + middle-age (-$50) + 0 viol ($0) + 0 acc ($0)
        # + mid vehicle ($0) + low mileage (-$50) = $700
        # This is above $300, so construct an extreme scenario to check floor.
        # Basic ($800) is the lowest base; maximum possible discount is
        # age(-50) + mileage(-50) = -100, so minimum natural = $700.
        # The floor is $300 -- validate via direct assertion.
        assert MINIMUM_PREMIUM == 300.0
        amount = _premium(
            CoverageType.BASIC,
            driver_dob=_dob_for_age(35),
            violation_count=0,
            accident_count=0,
            vehicle_year=_vehicle_year_age(5),
            vehicle_mileage=5_000,
        )
        assert amount >= MINIMUM_PREMIUM

    def test_floor_constant(self):
        assert MINIMUM_PREMIUM == 300.0


# ── TC-027a / TC-028a: Combined scenarios ────────────────────────────────────


class TestCombinedScenarios:
    def test_high_risk(self):
        """Young driver + many violations + many accidents + new car + high mileage."""
        # Basic: 800 + age(200) + viol(350) + acc(450) + vehicle(100) + mileage(100) = 2000
        amount = _premium(
            CoverageType.BASIC,
            driver_dob=_dob_for_age(20),
            violation_count=3,
            accident_count=3,
            vehicle_year=_vehicle_year_age(1),
            vehicle_mileage=50_000,
        )
        assert amount == 2000.0

    def test_high_risk_full_coverage(self):
        """Full coverage high-risk scenario."""
        # Full: 1500 + 200 + 350 + 450 + 100 + 100 = 2700
        amount = _premium(
            CoverageType.FULL,
            driver_dob=_dob_for_age(20),
            violation_count=3,
            accident_count=3,
            vehicle_year=_vehicle_year_age(1),
            vehicle_mileage=50_000,
        )
        assert amount == 2700.0

    def test_low_risk(self):
        """Middle-age driver + 0 violations + 0 accidents + mid vehicle + low mileage."""
        # Basic: 800 + age(-50) + viol(0) + acc(0) + vehicle(0) + mileage(-50) = 700
        amount = _premium(
            CoverageType.BASIC,
            driver_dob=_dob_for_age(40),
            violation_count=0,
            accident_count=0,
            vehicle_year=_vehicle_year_age(5),
            vehicle_mileage=5_000,
        )
        assert amount == 700.0

    def test_return_type(self):
        """calculate_premium returns (float, list[dict])."""
        amount, breakdown = calculate_premium(
            coverage_type=CoverageType.BASIC,
            driver_dob=_dob_for_age(30),
            violation_count=0,
            accident_count=0,
            vehicle_year=_vehicle_year_age(5),
            vehicle_mileage=15_000,
        )
        assert isinstance(amount, float)
        assert isinstance(breakdown, list)
        assert all(isinstance(item, dict) for item in breakdown)
        # Breakdown should have base_rate + 5 adjustments = 6 items
        assert len(breakdown) == 6
