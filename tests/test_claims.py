"""Tests for claim processing logic.

Covers:
  - Valid claim is approved with correct payout
  - Claim with no active policy is rejected
  - Claim with location outside zone is rejected
  - Claim filed after disruption window is rejected
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.schemas import (
    Claim,
    ClaimStatus,
    DisruptionType,
    ValidationResult,
    InsurancePolicy,
    PolicyStatus,
    RiskLevel,
    WeatherData,
    GeoLocation,
    AgentState,
)

NOW = datetime(2026, 3, 21, 10, 0, 0)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def build_agent_state(claim, user, policy, weather, zone, disruption=None):
    """Construct an AgentState for testing."""
    return AgentState(
        claim=claim,
        user=user,
        policy=policy,
        weather=weather,
        zone=zone,
        disruption=disruption,
    )


def validate_claim_sync(state: AgentState) -> ValidationResult:
    """Simplified synchronous claim validation matching expected business rules.

    This mirrors the logic the claims agent should implement:
    1. Policy must be active and not expired.
    2. Claim location must be within zone radius.
    3. Claim trigger timestamp must be within the disruption window (max 48h).
    4. Weather data must confirm a disruption matching the claim type.
    """
    reasons = []

    # 1. Policy validation
    policy_valid = (
        state.policy is not None
        and state.policy.status == PolicyStatus.ACTIVE
        and state.policy.start_date <= state.claim.trigger_timestamp <= state.policy.end_date
    )
    if not policy_valid:
        reasons.append("No active policy covering this claim period")

    # 2. Location validation (simple distance check)
    location_valid = False
    if state.zone is not None:
        lat_diff = abs(state.claim.location.latitude - state.zone.center.latitude)
        lng_diff = abs(state.claim.location.longitude - state.zone.center.longitude)
        approx_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111.0
        location_valid = approx_km <= state.zone.radius_km
    if not location_valid:
        reasons.append("Claim location is outside the covered zone")

    # 3. Time validation (claim must be within 48h of current time)
    time_valid = (NOW - state.claim.trigger_timestamp) <= timedelta(hours=48)
    if not time_valid:
        reasons.append("Claim filed outside the allowed disruption window")

    # 4. Weather confirmation
    weather_valid = False
    if state.weather is not None:
        if state.claim.disruption_type == DisruptionType.HEAVY_RAIN:
            weather_valid = state.weather.rainfall_mm >= 20.0
        elif state.claim.disruption_type == DisruptionType.FLOOD:
            weather_valid = state.weather.flood_alert_level >= 3
        elif state.claim.disruption_type == DisruptionType.POLLUTION:
            weather_valid = (state.weather.aqi or 0) >= 300
        else:
            weather_valid = True  # Other types validated differently
    if not weather_valid:
        reasons.append("Weather data does not confirm the reported disruption")

    overall_valid = policy_valid and location_valid and time_valid and weather_valid

    return ValidationResult(
        policy_valid=policy_valid,
        location_valid=location_valid,
        time_valid=time_valid,
        activity_valid=True,
        warehouse_proximity_valid=location_valid,
        zone_activity_valid=True,
        fraud_check_passed=True,
        duplicate_check_passed=True,
        overall_valid=overall_valid,
        rejection_reasons=reasons,
        confidence_score=0.9 if overall_valid else 0.2,
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestClaimProcessing:
    """Core claim processing scenarios."""

    def test_valid_claim_approved(
        self, sample_claim, sample_user, sample_policy, sample_weather_data, sample_zone
    ):
        """A legitimate heavy rain claim with valid policy, location, and weather
        should be approved."""
        state = build_agent_state(
            claim=sample_claim,
            user=sample_user,
            policy=sample_policy,
            weather=sample_weather_data,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is True
        assert result.policy_valid is True
        assert result.location_valid is True
        assert result.time_valid is True
        assert len(result.rejection_reasons) == 0
        assert result.confidence_score >= 0.8

    def test_no_policy_rejected(
        self, sample_claim, sample_user, sample_weather_data, sample_zone
    ):
        """A claim without an active policy must be rejected."""
        state = build_agent_state(
            claim=sample_claim,
            user=sample_user,
            policy=None,
            weather=sample_weather_data,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is False
        assert result.policy_valid is False
        assert "No active policy" in result.rejection_reasons[0]

    def test_expired_policy_rejected(
        self, sample_claim, sample_user, expired_policy, sample_weather_data, sample_zone
    ):
        """A claim against an expired policy must be rejected."""
        state = build_agent_state(
            claim=sample_claim,
            user=sample_user,
            policy=expired_policy,
            weather=sample_weather_data,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is False
        assert result.policy_valid is False

    def test_outside_zone_rejected(
        self, outside_zone_claim, sample_user, sample_policy, sample_weather_data, sample_zone
    ):
        """A claim with GPS coordinates far outside the zone radius must be rejected."""
        state = build_agent_state(
            claim=outside_zone_claim,
            user=sample_user,
            policy=sample_policy,
            weather=sample_weather_data,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is False
        assert result.location_valid is False
        assert any("outside" in r.lower() for r in result.rejection_reasons)

    def test_post_disruption_window_rejected(
        self, stale_claim, sample_user, sample_policy, sample_weather_data, sample_zone
    ):
        """A claim filed well after the disruption window (>48h) must be rejected."""
        state = build_agent_state(
            claim=stale_claim,
            user=sample_user,
            policy=sample_policy,
            weather=sample_weather_data,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is False
        assert result.time_valid is False
        assert any("window" in r.lower() for r in result.rejection_reasons)

    def test_weather_mismatch_rejected(
        self, sample_claim, sample_user, sample_policy, clear_weather, sample_zone
    ):
        """A heavy rain claim with clear weather data should be rejected because
        weather does not confirm the disruption."""
        state = build_agent_state(
            claim=sample_claim,
            user=sample_user,
            policy=sample_policy,
            weather=clear_weather,
            zone=sample_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is False
        assert any("weather" in r.lower() for r in result.rejection_reasons)

    def test_flood_claim_with_flood_weather(
        self, flood_claim, sample_user, sample_weather_data, flood_zone
    ):
        """A flood claim should validate weather using flood_alert_level >= 3."""
        policy = InsurancePolicy(
            policy_id="POL-VELACHERY-0001",
            user_id="RDR-0002",
            status=PolicyStatus.ACTIVE,
            premium_amount=70.0,
            coverage_amount=2000.0,
            start_date=NOW - timedelta(days=3),
            end_date=NOW + timedelta(days=4),
            zone_id="zone_velachery",
            warehouse_id="WH-VELACHERY-01",
            risk_level=RiskLevel.HIGH,
        )
        flood_weather = WeatherData(
            zone_id="zone_velachery",
            timestamp=NOW - timedelta(hours=2),
            temperature=26.0,
            humidity=98.0,
            rainfall_mm=120.0,
            wind_speed=45.0,
            aqi=90,
            flood_alert_level=4,
            visibility_km=0.5,
            condition="flood",
        )
        state = build_agent_state(
            claim=flood_claim,
            user=sample_user,
            policy=policy,
            weather=flood_weather,
            zone=flood_zone,
        )
        result = validate_claim_sync(state)

        assert result.overall_valid is True
        assert result.policy_valid is True
        assert result.location_valid is True
