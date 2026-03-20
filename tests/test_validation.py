"""Tests for the validation layer.

Covers:
  - All validation checks pass for a clean claim
  - Each individual check failure is handled correctly:
      * Policy invalid
      * Location invalid
      * Time invalid
      * Activity invalid
      * Warehouse proximity invalid
      * Zone activity invalid
      * Fraud check failed
      * Duplicate check failed
"""

import pytest
from datetime import datetime, timedelta

from src.models.schemas import (
    ValidationResult,
    Claim,
    ClaimStatus,
    DisruptionType,
    GeoLocation,
    InsurancePolicy,
    PolicyStatus,
    RiskLevel,
    Zone,
    WeatherData,
    UserProfile,
    UserRole,
)

NOW = datetime(2026, 3, 21, 10, 0, 0)


# ─── Validation Engine ───────────────────────────────────────────────────────

def run_validation_checks(
    claim: Claim,
    policy: InsurancePolicy | None,
    zone: Zone | None,
    weather: WeatherData | None,
    user: UserProfile | None,
    active_disruption: bool = True,
    duplicate_claim_ids: list[str] | None = None,
) -> ValidationResult:
    """Run all eight validation checks and produce an aggregate result.

    Each check is independent; overall_valid is True only when ALL pass.
    """
    reasons = []

    # 1. Policy valid
    policy_valid = (
        policy is not None
        and policy.status == PolicyStatus.ACTIVE
        and policy.start_date <= claim.trigger_timestamp <= policy.end_date
        and policy.user_id == claim.user_id
    )
    if not policy_valid:
        reasons.append("Policy validation failed: no active policy for this user/period")

    # 2. Location valid
    location_valid = False
    if zone is not None:
        lat_diff = abs(claim.location.latitude - zone.center.latitude)
        lng_diff = abs(claim.location.longitude - zone.center.longitude)
        approx_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111.0
        location_valid = approx_km <= zone.radius_km
    if not location_valid:
        reasons.append("Location validation failed: outside zone boundary")

    # 3. Time valid (within 48h)
    time_valid = (NOW - claim.trigger_timestamp) <= timedelta(hours=48)
    if not time_valid:
        reasons.append("Time validation failed: outside disruption window")

    # 4. Activity valid (user was active on the platform during disruption)
    activity_valid = user is not None and user.is_active
    if not activity_valid:
        reasons.append("Activity validation failed: user not active on delivery platform")

    # 5. Warehouse proximity valid
    warehouse_proximity_valid = (
        policy is not None
        and zone is not None
        and policy.zone_id == zone.zone_id
    )
    if not warehouse_proximity_valid:
        reasons.append("Warehouse proximity failed: claim zone does not match policy zone")

    # 6. Zone activity valid (zone has an active disruption)
    zone_activity_valid = active_disruption
    if not zone_activity_valid:
        reasons.append("Zone activity failed: no active disruption in this zone")

    # 7. Fraud check passed
    fraud_check_passed = user is not None and user.trust_score >= 0.2
    if not fraud_check_passed:
        reasons.append("Fraud check failed: trust score below minimum threshold")

    # 8. Duplicate check passed
    duplicate_claim_ids = duplicate_claim_ids or []
    duplicate_check_passed = claim.claim_id not in duplicate_claim_ids
    if not duplicate_check_passed:
        reasons.append("Duplicate check failed: claim ID already processed")

    overall_valid = all([
        policy_valid,
        location_valid,
        time_valid,
        activity_valid,
        warehouse_proximity_valid,
        zone_activity_valid,
        fraud_check_passed,
        duplicate_check_passed,
    ])

    confidence = 0.95 if overall_valid else max(0.1, 1.0 - len(reasons) * 0.15)

    return ValidationResult(
        policy_valid=policy_valid,
        location_valid=location_valid,
        time_valid=time_valid,
        activity_valid=activity_valid,
        warehouse_proximity_valid=warehouse_proximity_valid,
        zone_activity_valid=zone_activity_valid,
        fraud_check_passed=fraud_check_passed,
        duplicate_check_passed=duplicate_check_passed,
        overall_valid=overall_valid,
        rejection_reasons=reasons,
        confidence_score=round(confidence, 2),
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestValidationAllPass:
    """When all inputs are correct, every check should pass."""

    def test_all_checks_pass(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
            active_disruption=True,
            duplicate_claim_ids=[],
        )

        assert result.overall_valid is True
        assert result.policy_valid is True
        assert result.location_valid is True
        assert result.time_valid is True
        assert result.activity_valid is True
        assert result.warehouse_proximity_valid is True
        assert result.zone_activity_valid is True
        assert result.fraud_check_passed is True
        assert result.duplicate_check_passed is True
        assert result.confidence_score >= 0.9
        assert len(result.rejection_reasons) == 0


class TestValidationIndividualFailures:
    """Each individual check failure should cause overall_valid to be False
    and add a specific rejection reason."""

    def test_policy_invalid_no_policy(
        self, sample_claim, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=None,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.policy_valid is False
        assert any("policy" in r.lower() for r in result.rejection_reasons)

    def test_policy_invalid_expired(
        self, sample_claim, expired_policy, sample_zone, sample_weather_data, sample_user
    ):
        # expired_policy belongs to RDR-0042, adjust claim to match
        claim = sample_claim.model_copy(update={"user_id": "RDR-0042"})
        result = run_validation_checks(
            claim=claim,
            policy=expired_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.policy_valid is False

    def test_policy_invalid_user_mismatch(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        """Claim user_id does not match policy user_id."""
        claim = sample_claim.model_copy(update={"user_id": "RDR-WRONG"})
        result = run_validation_checks(
            claim=claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.policy_valid is False

    def test_location_invalid(
        self, outside_zone_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=outside_zone_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.location_valid is False
        assert any("location" in r.lower() for r in result.rejection_reasons)

    def test_location_invalid_no_zone(
        self, sample_claim, sample_policy, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=None,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.location_valid is False

    def test_time_invalid(
        self, stale_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=stale_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.time_valid is False
        assert any("time" in r.lower() or "window" in r.lower() for r in result.rejection_reasons)

    def test_activity_invalid_user_inactive(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        inactive_user = sample_user.model_copy(update={"is_active": False})
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=inactive_user,
        )
        assert result.overall_valid is False
        assert result.activity_valid is False
        assert any("activity" in r.lower() for r in result.rejection_reasons)

    def test_activity_invalid_no_user(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=None,
        )
        assert result.overall_valid is False
        assert result.activity_valid is False

    def test_warehouse_proximity_invalid(
        self, sample_claim, sample_policy, flood_zone, sample_weather_data, sample_user
    ):
        """Policy zone (zone_tnagar) does not match supplied zone (zone_velachery)."""
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=flood_zone,
            weather=sample_weather_data,
            user=sample_user,
        )
        assert result.overall_valid is False
        assert result.warehouse_proximity_valid is False
        assert any("warehouse" in r.lower() or "zone" in r.lower() for r in result.rejection_reasons)

    def test_zone_activity_invalid(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
            active_disruption=False,
        )
        assert result.overall_valid is False
        assert result.zone_activity_valid is False
        assert any("disruption" in r.lower() for r in result.rejection_reasons)

    def test_fraud_check_failed(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data
    ):
        """User with trust_score below 0.2 fails fraud check."""
        blocked_user = UserProfile(
            user_id="RDR-0001",
            name="Blocked User",
            role=UserRole.DELIVERY_PARTNER,
            phone="+91-0000000000",
            registration_date=datetime(2025, 1, 1),
            home_location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            trust_score=0.1,
            is_active=True,
        )
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=blocked_user,
        )
        assert result.overall_valid is False
        assert result.fraud_check_passed is False
        assert any("fraud" in r.lower() or "trust" in r.lower() for r in result.rejection_reasons)

    def test_duplicate_check_failed(
        self, sample_claim, sample_policy, sample_zone, sample_weather_data, sample_user
    ):
        result = run_validation_checks(
            claim=sample_claim,
            policy=sample_policy,
            zone=sample_zone,
            weather=sample_weather_data,
            user=sample_user,
            duplicate_claim_ids=[sample_claim.claim_id],
        )
        assert result.overall_valid is False
        assert result.duplicate_check_passed is False
        assert any("duplicate" in r.lower() for r in result.rejection_reasons)

    def test_multiple_failures_compound(
        self, outside_zone_claim, sample_zone, sample_weather_data
    ):
        """Multiple simultaneous failures should all be reported."""
        result = run_validation_checks(
            claim=outside_zone_claim,
            policy=None,
            zone=sample_zone,
            weather=sample_weather_data,
            user=None,
            active_disruption=False,
        )
        assert result.overall_valid is False
        # At minimum: policy, location, activity, zone_activity failures
        assert len(result.rejection_reasons) >= 4
        assert result.confidence_score < 0.5
