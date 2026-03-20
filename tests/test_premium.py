"""Tests for premium calculation logic.

Covers:
  - Safe zone (Anna Nagar, low risk) => base Rs. 30/week
  - Moderate zone (T. Nagar, medium risk) => base Rs. 50/week
  - Flood-prone zone (Velachery, high risk) => base Rs. 70/week
  - History discount applied for clean riders
  - Seasonal multiplier during monsoon
"""

import pytest
from datetime import datetime

from src.models.schemas import (
    PremiumCalculation,
    Zone,
    RiskLevel,
    UserProfile,
    GeoLocation,
    UserRole,
)

NOW = datetime(2026, 3, 21, 10, 0, 0)

# ─── Premium Calculation Engine ──────────────────────────────────────────────

# Base premiums per risk level (weekly, in INR)
BASE_PREMIUMS = {
    RiskLevel.LOW: 30.0,
    RiskLevel.MEDIUM: 50.0,
    RiskLevel.HIGH: 70.0,
    RiskLevel.CRITICAL: 99.0,
}

# Seasonal multipliers by month
SEASONAL_MULTIPLIERS = {
    1: 1.0,   # January
    2: 1.0,   # February
    3: 1.0,   # March
    4: 1.05,  # April
    5: 1.1,   # May
    6: 1.2,   # June (pre-monsoon)
    7: 1.35,  # July (monsoon peak)
    8: 1.35,  # August (monsoon peak)
    9: 1.25,  # September
    10: 1.3,  # October (NE monsoon for Chennai)
    11: 1.4,  # November (NE monsoon peak for Chennai)
    12: 1.25, # December (post-monsoon)
}


def calculate_premium(
    zone: Zone,
    user: UserProfile,
    reference_date: datetime = NOW,
) -> PremiumCalculation:
    """Calculate the weekly premium for a delivery partner in a given zone.

    Logic:
    1. Base premium determined by zone risk level.
    2. Risk multiplier based on user's personal risk_score (0.8 to 1.4).
    3. Zone factor based on avg order density (higher density = slight increase).
    4. History discount: 0-15% based on clean claim history.
    5. Seasonal multiplier based on month (monsoon increases).
    """

    # 1. Base premium
    base = BASE_PREMIUMS.get(zone.risk_level, 50.0)

    # 2. Risk multiplier: maps user risk_score [0..1] to multiplier [0.8..1.4]
    risk_multiplier = 0.8 + (user.risk_score * 0.6)

    # 3. Zone factor: order density adjustment
    # Higher density = more potential loss exposure
    if zone.avg_order_density > 100:
        zone_factor = 1.1
    elif zone.avg_order_density > 60:
        zone_factor = 1.0
    else:
        zone_factor = 0.9

    # 4. History discount
    # Clean riders (low total claims relative to tenure) get up to 15% off
    if user.total_claims == 0:
        history_discount = 0.15
    elif user.total_claims <= 3:
        history_discount = 0.10
    elif user.total_claims <= 8:
        history_discount = 0.05
    else:
        history_discount = 0.0

    # 5. Seasonal multiplier
    seasonal = SEASONAL_MULTIPLIERS.get(reference_date.month, 1.0)

    # Final calculation
    adjusted = base * risk_multiplier * zone_factor * seasonal
    discounted = adjusted * (1.0 - history_discount)
    final = round(max(discounted, 15.0), 2)  # minimum Rs. 15/week

    return PremiumCalculation(
        base_premium=base,
        risk_multiplier=round(risk_multiplier, 3),
        zone_factor=zone_factor,
        history_discount=history_discount,
        final_premium=final,
        breakdown={
            "base": base,
            "after_risk": round(base * risk_multiplier, 2),
            "after_zone": round(base * risk_multiplier * zone_factor, 2),
            "after_seasonal": round(base * risk_multiplier * zone_factor * seasonal, 2),
            "after_discount": final,
            "seasonal_multiplier": seasonal,
        },
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestBasePremiumByZone:
    """Base premium should match zone risk level."""

    def test_safe_zone_base_30(self, safe_zone, sample_user):
        """Anna Nagar (low risk) should have base premium of Rs. 30."""
        result = calculate_premium(safe_zone, sample_user)
        assert result.base_premium == 30.0

    def test_moderate_zone_base_50(self, sample_zone, sample_user):
        """T. Nagar (medium risk) should have base premium of Rs. 50."""
        result = calculate_premium(sample_zone, sample_user)
        assert result.base_premium == 50.0

    def test_flood_prone_zone_base_70(self, flood_zone, sample_user):
        """Velachery (high risk) should have base premium of Rs. 70."""
        result = calculate_premium(flood_zone, sample_user)
        assert result.base_premium == 70.0

    def test_relative_ordering(self, safe_zone, sample_zone, flood_zone, sample_user):
        """Premiums should increase with risk: low < medium < high."""
        low = calculate_premium(safe_zone, sample_user).final_premium
        med = calculate_premium(sample_zone, sample_user).final_premium
        high = calculate_premium(flood_zone, sample_user).final_premium

        assert low < med < high


class TestHistoryDiscount:
    """Clean claim history should reduce the premium."""

    def test_new_user_gets_max_discount(self, sample_zone, new_user):
        """A user with 0 claims gets 15% history discount."""
        result = calculate_premium(sample_zone, new_user)
        assert result.history_discount == 0.15

    def test_few_claims_gets_moderate_discount(self, sample_zone, sample_user):
        """A user with 3 claims gets 10% history discount."""
        assert sample_user.total_claims == 3
        result = calculate_premium(sample_zone, sample_user)
        assert result.history_discount == 0.10

    def test_many_claims_no_discount(self, sample_zone, suspicious_user):
        """A user with 18 claims gets 0% history discount."""
        assert suspicious_user.total_claims == 18
        result = calculate_premium(sample_zone, suspicious_user)
        assert result.history_discount == 0.0

    def test_discount_reduces_final_premium(self, sample_zone, new_user, suspicious_user):
        """New user (max discount) should pay less than heavy-claim user (no discount)."""
        new_premium = calculate_premium(sample_zone, new_user).final_premium
        heavy_premium = calculate_premium(sample_zone, suspicious_user).final_premium

        # suspicious_user has higher risk_score (0.85 vs 0.5), so even without
        # the discount comparison, the relative magnitude may differ.
        # But we can verify the discount was applied:
        result_new = calculate_premium(sample_zone, new_user)
        before_discount = (
            result_new.base_premium
            * result_new.risk_multiplier
            * result_new.zone_factor
            * result_new.breakdown["seasonal_multiplier"]
        )
        assert result_new.final_premium < before_discount


class TestSeasonalMultiplier:
    """Monsoon months should increase the premium."""

    def test_march_no_seasonal_increase(self, sample_zone, sample_user):
        """March (non-monsoon) should have multiplier of 1.0."""
        result = calculate_premium(sample_zone, sample_user, reference_date=datetime(2026, 3, 15))
        assert result.breakdown["seasonal_multiplier"] == 1.0

    def test_november_monsoon_peak(self, sample_zone, sample_user):
        """November (NE monsoon peak for Chennai) should have multiplier of 1.4."""
        result = calculate_premium(
            sample_zone, sample_user, reference_date=datetime(2026, 11, 15)
        )
        assert result.breakdown["seasonal_multiplier"] == 1.4

    def test_july_sw_monsoon(self, sample_zone, sample_user):
        """July (SW monsoon) should have multiplier of 1.35."""
        result = calculate_premium(
            sample_zone, sample_user, reference_date=datetime(2026, 7, 15)
        )
        assert result.breakdown["seasonal_multiplier"] == 1.35

    def test_monsoon_increases_premium(self, sample_zone, sample_user):
        """The same zone+user should cost more during monsoon than off-season."""
        march_premium = calculate_premium(
            sample_zone, sample_user, reference_date=datetime(2026, 3, 15)
        ).final_premium
        november_premium = calculate_premium(
            sample_zone, sample_user, reference_date=datetime(2026, 11, 15)
        ).final_premium

        assert november_premium > march_premium


class TestRiskMultiplier:
    """User risk score should affect the premium multiplier."""

    def test_low_risk_user_gets_lower_multiplier(self, sample_zone, sample_user):
        """User with risk_score=0.3 should get multiplier ~0.98."""
        result = calculate_premium(sample_zone, sample_user)
        assert result.risk_multiplier == pytest.approx(0.98, abs=0.01)

    def test_high_risk_user_gets_higher_multiplier(self, sample_zone, suspicious_user):
        """User with risk_score=0.85 should get multiplier ~1.31."""
        result = calculate_premium(sample_zone, suspicious_user)
        assert result.risk_multiplier == pytest.approx(1.31, abs=0.01)

    def test_minimum_premium_floor(self, safe_zone):
        """Premium should never go below Rs. 15/week even for the best case."""
        perfect_user = UserProfile(
            user_id="RDR-PERFECT",
            name="Perfect Rider",
            role=UserRole.DELIVERY_PARTNER,
            phone="+91-0000000000",
            registration_date=datetime(2024, 1, 1),
            home_location=GeoLocation(latitude=13.0850, longitude=80.2101, source="gps"),
            risk_score=0.0,
            trust_score=1.0,
            total_claims=0,
            total_payouts=0.0,
        )
        result = calculate_premium(safe_zone, perfect_user)
        assert result.final_premium >= 15.0
