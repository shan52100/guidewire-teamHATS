"""Tests for payout calculation logic.

Covers:
  - Severity scaling: higher severity => proportionally higher payout
  - Zone caps: payout must not exceed zone-based weekly cap
  - New user reduced rate: first-time claimants get a reduced payout
  - Multi-trigger events yield higher payouts than single events
"""

import pytest
from datetime import datetime, timedelta

from src.models.schemas import (
    IncomeLossCalculation,
    Claim,
    ClaimStatus,
    DisruptionType,
    RiskLevel,
    Zone,
    UserProfile,
    GeoLocation,
    UserRole,
)

NOW = datetime(2026, 3, 21, 10, 0, 0)


# ─── Zone Caps (weekly payout cap per risk level, in INR) ────────────────────

ZONE_WEEKLY_CAPS = {
    RiskLevel.LOW: 1500.0,
    RiskLevel.MEDIUM: 2000.0,
    RiskLevel.HIGH: 2000.0,
    RiskLevel.CRITICAL: 2500.0,
}

# Base income parameters
AVG_INCOME_PER_ORDER = 35.0  # Rs. per delivery
BASE_LOST_HOURS = 4.0  # default disruption duration


def calculate_payout(
    claim: Claim,
    zone: Zone,
    user: UserProfile,
    lost_hours: float = BASE_LOST_HOURS,
    existing_weekly_payouts: float = 0.0,
) -> IncomeLossCalculation:
    """Calculate the payout for an approved claim.

    Logic:
    1. Base loss = avg_orders_per_hour * avg_income_per_order * lost_hours
    2. Severity multiplier scales the base loss (0.3x to 1.5x)
    3. Multi-trigger bonus: +25% for multi_trigger events
    4. New user rate: riders with 0 prior claims get 70% of calculated payout
    5. Zone cap: total weekly payouts cannot exceed zone-based cap
    """

    avg_orders = zone.avg_order_density
    avg_income = AVG_INCOME_PER_ORDER

    # 1. Base loss
    base_loss = avg_orders * avg_income * lost_hours

    # 2. Severity multiplier: maps severity [0..1] to [0.3..1.5]
    severity = claim.disruption_severity
    severity_multiplier = 0.3 + (severity * 1.2)

    adjusted = base_loss * severity_multiplier

    # 3. Multi-trigger bonus
    if claim.disruption_type == DisruptionType.MULTI_TRIGGER:
        adjusted *= 1.25

    # 4. New user reduced rate
    new_user_applied = False
    if user.total_claims == 0:
        adjusted *= 0.7
        new_user_applied = True

    # 5. Zone cap
    weekly_cap = ZONE_WEEKLY_CAPS.get(zone.risk_level, 2000.0)
    remaining_cap = max(0.0, weekly_cap - existing_weekly_payouts)

    payout_cap_applied = adjusted > remaining_cap
    final_payout = round(min(adjusted, remaining_cap), 2)

    return IncomeLossCalculation(
        avg_orders_per_hour=avg_orders,
        avg_income_per_order=avg_income,
        lost_hours=lost_hours,
        severity_multiplier=round(severity_multiplier, 3),
        base_loss=round(base_loss, 2),
        adjusted_loss=round(adjusted, 2),
        payout_cap_applied=payout_cap_applied,
        final_payout=final_payout,
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestSeverityScaling:
    """Payout should scale with disruption severity."""

    def test_low_severity_lower_payout(self, sample_zone, sample_user):
        """A claim with 0.2 severity should yield a lower payout than 0.8."""
        low_claim = Claim(
            claim_id="CLM-SEV-LOW",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.2,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=200.0,
        )
        high_claim = low_claim.model_copy(
            update={"claim_id": "CLM-SEV-HIGH", "disruption_severity": 0.8}
        )

        low_result = calculate_payout(low_claim, sample_zone, sample_user)
        high_result = calculate_payout(high_claim, sample_zone, sample_user)

        assert low_result.final_payout < high_result.final_payout
        assert low_result.severity_multiplier < high_result.severity_multiplier

    def test_severity_multiplier_range(self, sample_zone, sample_user):
        """Severity 0.0 => multiplier 0.3, severity 1.0 => multiplier 1.5."""
        min_claim = Claim(
            claim_id="CLM-SEV-MIN",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.0,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=100.0,
        )
        max_claim = min_claim.model_copy(
            update={"claim_id": "CLM-SEV-MAX", "disruption_severity": 1.0}
        )

        min_result = calculate_payout(min_claim, sample_zone, sample_user)
        max_result = calculate_payout(max_claim, sample_zone, sample_user)

        assert min_result.severity_multiplier == pytest.approx(0.3, abs=0.01)
        assert max_result.severity_multiplier == pytest.approx(1.5, abs=0.01)

    def test_moderate_severity_proportional(self, sample_zone, sample_user):
        """Severity 0.5 should yield multiplier ~0.9."""
        claim = Claim(
            claim_id="CLM-SEV-MID",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.5,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=300.0,
        )
        result = calculate_payout(claim, sample_zone, sample_user)
        assert result.severity_multiplier == pytest.approx(0.9, abs=0.01)


class TestZoneCaps:
    """Payout should be capped by zone weekly limits."""

    def test_cap_applied_when_exceeded(self, sample_zone, sample_user):
        """When calculated payout exceeds remaining cap, it should be capped."""
        extreme_claim = Claim(
            claim_id="CLM-CAP-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=1.0,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=5000.0,
        )
        # Existing payouts of Rs. 1800 with cap of Rs. 2000 => only Rs. 200 remaining
        result = calculate_payout(
            extreme_claim, sample_zone, sample_user, existing_weekly_payouts=1800.0
        )

        assert result.payout_cap_applied is True
        assert result.final_payout == 200.0

    def test_no_cap_when_within_limit(self, safe_zone, sample_user):
        """Low-severity claim in safe zone should not hit the cap."""
        small_claim = Claim(
            claim_id="CLM-CAP-002",
            policy_id="POL-ANNANAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.3,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0850, longitude=80.2101, source="gps"),
            estimated_loss=200.0,
        )
        result = calculate_payout(small_claim, safe_zone, sample_user)

        assert result.payout_cap_applied is False
        assert result.final_payout > 0

    def test_cap_is_zero_when_fully_used(self, sample_zone, sample_user):
        """If weekly cap is already reached, payout should be zero."""
        claim = Claim(
            claim_id="CLM-CAP-003",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.5,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=300.0,
        )
        result = calculate_payout(claim, sample_zone, sample_user, existing_weekly_payouts=2000.0)

        assert result.final_payout == 0.0
        assert result.payout_cap_applied is True

    def test_high_risk_zone_has_standard_cap(self, flood_zone, sample_user):
        """High risk zone should have cap of Rs. 2000."""
        claim = Claim(
            claim_id="CLM-CAP-004",
            policy_id="POL-VELACHERY-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.FLOOD,
            disruption_severity=1.0,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=12.9815, longitude=80.2180, source="gps"),
            estimated_loss=3000.0,
        )
        result = calculate_payout(claim, flood_zone, sample_user, lost_hours=8.0)

        assert result.final_payout <= 2000.0


class TestNewUserReducedRate:
    """First-time claimants should receive a reduced payout (70%)."""

    def test_new_user_gets_reduced_rate(self, sample_zone, new_user):
        """A user with 0 prior claims should get 70% of the calculated payout."""
        claim = Claim(
            claim_id="CLM-NEW-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0099",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.6,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=400.0,
        )
        result_new = calculate_payout(claim, sample_zone, new_user)
        result_existing = calculate_payout(claim, sample_zone, sample_user_with_history())

        # New user payout should be approximately 70% of existing user payout
        assert result_new.final_payout < result_existing.final_payout
        ratio = result_new.final_payout / result_existing.final_payout
        assert ratio == pytest.approx(0.7, abs=0.05)

    def test_experienced_user_full_rate(self, sample_zone, sample_user):
        """A user with prior claims should get the full rate."""
        claim = Claim(
            claim_id="CLM-EXP-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.6,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=400.0,
        )
        result = calculate_payout(claim, sample_zone, sample_user)

        # Verify no new-user reduction was applied by checking the math
        expected_base = sample_zone.avg_order_density * AVG_INCOME_PER_ORDER * BASE_LOST_HOURS
        expected_severity = 0.3 + (0.6 * 1.2)
        expected_adjusted = expected_base * expected_severity
        assert result.adjusted_loss == pytest.approx(expected_adjusted, rel=0.01)


class TestMultiTrigger:
    """Multi-trigger events should yield higher payouts."""

    def test_multi_trigger_higher_than_single(self, flood_zone, sample_user):
        """A multi-trigger claim should pay 25% more than a single-trigger
        claim at the same severity."""
        single_claim = Claim(
            claim_id="CLM-MT-SINGLE",
            policy_id="POL-VELACHERY-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.FLOOD,
            disruption_severity=0.7,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=12.9815, longitude=80.2180, source="gps"),
            estimated_loss=600.0,
        )
        multi_claim = single_claim.model_copy(
            update={
                "claim_id": "CLM-MT-MULTI",
                "disruption_type": DisruptionType.MULTI_TRIGGER,
            }
        )

        single_result = calculate_payout(single_claim, flood_zone, sample_user)
        multi_result = calculate_payout(multi_claim, flood_zone, sample_user)

        # Multi-trigger should be ~25% higher (before any cap)
        if not single_result.payout_cap_applied and not multi_result.payout_cap_applied:
            ratio = multi_result.final_payout / single_result.final_payout
            assert ratio == pytest.approx(1.25, abs=0.01)
        else:
            # Even if capped, multi should be >= single
            assert multi_result.final_payout >= single_result.final_payout

    def test_multi_trigger_bonus_value(self, sample_zone, sample_user):
        """Verify the multi-trigger adjusted loss is exactly 1.25x the base adjusted."""
        claim = Claim(
            claim_id="CLM-MT-CHECK",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.MULTI_TRIGGER,
            disruption_severity=0.5,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=500.0,
        )
        result = calculate_payout(claim, sample_zone, sample_user)

        expected_base = sample_zone.avg_order_density * AVG_INCOME_PER_ORDER * BASE_LOST_HOURS
        expected_severity = 0.3 + (0.5 * 1.2)
        expected_adjusted = expected_base * expected_severity * 1.25

        assert result.adjusted_loss == pytest.approx(expected_adjusted, rel=0.01)


class TestPayoutCalculationIntegration:
    """End-to-end payout scenarios combining multiple factors."""

    def test_base_loss_calculation(self, sample_zone, sample_user):
        """Base loss = avg_orders * income_per_order * lost_hours."""
        claim = Claim(
            claim_id="CLM-BASE-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.5,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=300.0,
        )
        result = calculate_payout(claim, sample_zone, sample_user, lost_hours=2.0)

        expected_base = 85.0 * 35.0 * 2.0  # 5950.0
        assert result.base_loss == pytest.approx(expected_base, rel=0.01)
        assert result.avg_orders_per_hour == 85.0
        assert result.avg_income_per_order == 35.0
        assert result.lost_hours == 2.0

    def test_payout_always_non_negative(self, sample_zone, sample_user):
        """Payout should never be negative regardless of inputs."""
        claim = Claim(
            claim_id="CLM-NEG-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.0,
            trigger_timestamp=NOW,
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=0.0,
        )
        result = calculate_payout(
            claim, sample_zone, sample_user, existing_weekly_payouts=5000.0
        )
        assert result.final_payout >= 0.0


# ─── Helper ──────────────────────────────────────────────────────────────────

def sample_user_with_history() -> UserProfile:
    """A user with some claim history (not new, not suspicious)."""
    return UserProfile(
        user_id="RDR-0050",
        name="Karthik R.",
        role=UserRole.DELIVERY_PARTNER,
        phone="+91-9876500050",
        registration_date=datetime(2025, 3, 1),
        home_location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
        risk_score=0.3,
        trust_score=0.8,
        total_claims=5,
        total_payouts=1600.0,
        is_active=True,
    )
