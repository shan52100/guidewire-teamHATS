"""Shared pytest fixtures with realistic Chennai zone data."""

import pytest
from datetime import datetime, timedelta

from src.models.schemas import (
    UserProfile,
    GeoLocation,
    InsurancePolicy,
    Claim,
    WeatherData,
    Zone,
    Warehouse,
    DisruptionEvent,
    ValidationResult,
    PolicyStatus,
    ClaimStatus,
    DisruptionType,
    RiskLevel,
    UserRole,
)


# ─── Time helpers ────────────────────────────────────────────────────────────

NOW = datetime(2026, 3, 21, 10, 0, 0)


# ─── GeoLocations for Chennai zones ─────────────────────────────────────────

COORDS_TNAGAR = GeoLocation(latitude=13.0418, longitude=80.2341, source="gps")
COORDS_VELACHERY = GeoLocation(latitude=12.9815, longitude=80.2180, source="gps")
COORDS_ANNANAGAR = GeoLocation(latitude=13.0850, longitude=80.2101, source="gps")
COORDS_TAMBARAM = GeoLocation(latitude=12.9249, longitude=80.1000, source="gps")
COORDS_ADYAR = GeoLocation(latitude=13.0012, longitude=80.2565, source="gps")


# ─── User fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_user():
    """A standard delivery partner registered in T. Nagar."""
    return UserProfile(
        user_id="RDR-0001",
        name="Rajesh Kumar",
        role=UserRole.DELIVERY_PARTNER,
        phone="+91-9876543210",
        email="rajesh.k@zepto.co",
        registration_date=datetime(2025, 6, 15),
        home_location=COORDS_TNAGAR,
        assigned_warehouse_id="WH-TNAGAR-01",
        delivery_platform="zepto",
        risk_score=0.3,
        trust_score=0.82,
        total_claims=3,
        total_payouts=960.0,
        is_active=True,
    )


@pytest.fixture
def new_user():
    """A recently registered rider with no claim history."""
    return UserProfile(
        user_id="RDR-0099",
        name="Meena Lakshmi",
        role=UserRole.DELIVERY_PARTNER,
        phone="+91-9123456789",
        registration_date=NOW - timedelta(days=7),
        home_location=COORDS_ADYAR,
        assigned_warehouse_id="WH-ADYAR-01",
        delivery_platform="blinkit",
        risk_score=0.5,
        trust_score=0.5,
        total_claims=0,
        total_payouts=0.0,
        is_active=True,
    )


@pytest.fixture
def suspicious_user():
    """A rider with a history of frequent claims and low trust."""
    return UserProfile(
        user_id="RDR-0042",
        name="Deepa Venkat",
        role=UserRole.DELIVERY_PARTNER,
        phone="+91-9988776655",
        registration_date=datetime(2025, 1, 10),
        home_location=COORDS_TAMBARAM,
        assigned_warehouse_id="WH-TAMBARAM-01",
        delivery_platform="zepto",
        risk_score=0.85,
        trust_score=0.22,
        total_claims=18,
        total_payouts=8400.0,
        is_active=True,
    )


# ─── Policy fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_policy():
    """Active policy for the standard user in T. Nagar zone."""
    return InsurancePolicy(
        policy_id="POL-TNAGAR-0001",
        user_id="RDR-0001",
        status=PolicyStatus.ACTIVE,
        premium_amount=50.0,
        coverage_amount=2000.0,
        start_date=NOW - timedelta(days=3),
        end_date=NOW + timedelta(days=4),
        zone_id="zone_tnagar",
        warehouse_id="WH-TNAGAR-01",
        risk_level=RiskLevel.MEDIUM,
    )


@pytest.fixture
def expired_policy():
    """An expired policy that should cause claim rejection."""
    return InsurancePolicy(
        policy_id="POL-VELACHERY-0005",
        user_id="RDR-0042",
        status=PolicyStatus.EXPIRED,
        premium_amount=70.0,
        coverage_amount=2000.0,
        start_date=NOW - timedelta(days=14),
        end_date=NOW - timedelta(days=7),
        zone_id="zone_velachery",
        warehouse_id="WH-VELACHERY-01",
        risk_level=RiskLevel.HIGH,
    )


# ─── Zone fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_zone():
    """T. Nagar zone - medium risk, good order density."""
    return Zone(
        zone_id="zone_tnagar",
        name="T. Nagar",
        center=COORDS_TNAGAR,
        radius_km=4.0,
        risk_level=RiskLevel.MEDIUM,
        avg_order_density=85.0,
        is_active=True,
    )


@pytest.fixture
def safe_zone():
    """Anna Nagar zone - low risk, high order density."""
    return Zone(
        zone_id="zone_annanagar",
        name="Anna Nagar",
        center=COORDS_ANNANAGAR,
        radius_km=5.0,
        risk_level=RiskLevel.LOW,
        avg_order_density=110.0,
        is_active=True,
    )


@pytest.fixture
def flood_zone():
    """Velachery zone - high risk, flood-prone area."""
    return Zone(
        zone_id="zone_velachery",
        name="Velachery",
        center=COORDS_VELACHERY,
        radius_km=4.5,
        risk_level=RiskLevel.HIGH,
        avg_order_density=62.0,
        is_active=True,
    )


@pytest.fixture
def tambaram_zone():
    """Tambaram zone - high risk, lower density."""
    return Zone(
        zone_id="zone_tambaram",
        name="Tambaram",
        center=COORDS_TAMBARAM,
        radius_km=5.0,
        risk_level=RiskLevel.HIGH,
        avg_order_density=45.0,
        is_active=True,
    )


@pytest.fixture
def adyar_zone():
    """Adyar zone - medium risk."""
    return Zone(
        zone_id="zone_adyar",
        name="Adyar",
        center=COORDS_ADYAR,
        radius_km=4.0,
        risk_level=RiskLevel.MEDIUM,
        avg_order_density=78.0,
        is_active=True,
    )


# ─── Warehouse fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_warehouse():
    return Warehouse(
        warehouse_id="WH-TNAGAR-01",
        name="T. Nagar Dark Store",
        zone_id="zone_tnagar",
        location=GeoLocation(latitude=13.0410, longitude=80.2335, source="manual"),
        radius_km=5.0,
        is_operational=True,
        avg_orders_per_hour=80.0,
    )


# ─── Weather fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_weather_data():
    """Heavy rain weather data triggering a claim in T. Nagar."""
    return WeatherData(
        zone_id="zone_tnagar",
        timestamp=NOW - timedelta(hours=1),
        temperature=28.5,
        humidity=92.0,
        rainfall_mm=45.0,
        wind_speed=32.0,
        aqi=85,
        flood_alert_level=1,
        visibility_km=2.5,
        condition="heavy_rain",
    )


@pytest.fixture
def clear_weather():
    """Clear weather - no disruption expected."""
    return WeatherData(
        zone_id="zone_annanagar",
        timestamp=NOW,
        temperature=32.0,
        humidity=55.0,
        rainfall_mm=0.0,
        wind_speed=8.0,
        aqi=65,
        flood_alert_level=0,
        visibility_km=10.0,
        condition="clear",
    )


@pytest.fixture
def flood_weather():
    """Severe flooding conditions in Velachery."""
    return WeatherData(
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


@pytest.fixture
def pollution_weather():
    """High pollution event in Tambaram."""
    return WeatherData(
        zone_id="zone_tambaram",
        timestamp=NOW,
        temperature=35.0,
        humidity=40.0,
        rainfall_mm=0.0,
        wind_speed=5.0,
        aqi=380,
        flood_alert_level=0,
        visibility_km=3.0,
        condition="haze",
    )


# ─── Claim fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_claim():
    """A valid heavy rain claim in T. Nagar zone."""
    return Claim(
        claim_id="CLM-20260321-001",
        policy_id="POL-TNAGAR-0001",
        user_id="RDR-0001",
        status=ClaimStatus.PENDING,
        disruption_type=DisruptionType.HEAVY_RAIN,
        disruption_severity=0.72,
        trigger_timestamp=NOW - timedelta(hours=1),
        location=GeoLocation(
            latitude=13.0420,
            longitude=80.2345,
            accuracy_meters=15.0,
            timestamp=NOW - timedelta(hours=1),
            source="gps",
        ),
        estimated_loss=500.0,
    )


@pytest.fixture
def flood_claim():
    """A severe flood claim in Velachery."""
    return Claim(
        claim_id="CLM-20260321-002",
        policy_id="POL-VELACHERY-0001",
        user_id="RDR-0002",
        status=ClaimStatus.PENDING,
        disruption_type=DisruptionType.FLOOD,
        disruption_severity=0.91,
        trigger_timestamp=NOW - timedelta(hours=2),
        location=COORDS_VELACHERY,
        estimated_loss=900.0,
    )


@pytest.fixture
def multi_trigger_claim():
    """Multi-trigger event combining rain and platform outage."""
    return Claim(
        claim_id="CLM-20260321-007",
        policy_id="POL-VELACHERY-0001",
        user_id="RDR-0007",
        status=ClaimStatus.PENDING,
        disruption_type=DisruptionType.MULTI_TRIGGER,
        disruption_severity=0.95,
        trigger_timestamp=NOW - timedelta(hours=1),
        location=COORDS_VELACHERY,
        estimated_loss=1200.0,
    )


@pytest.fixture
def outside_zone_claim():
    """Claim with location far outside any covered zone."""
    return Claim(
        claim_id="CLM-20260321-OOZ",
        policy_id="POL-TNAGAR-0001",
        user_id="RDR-0001",
        status=ClaimStatus.PENDING,
        disruption_type=DisruptionType.HEAVY_RAIN,
        disruption_severity=0.6,
        trigger_timestamp=NOW - timedelta(hours=1),
        location=GeoLocation(
            latitude=11.0000,
            longitude=79.0000,
            source="gps",
        ),
        estimated_loss=400.0,
    )


@pytest.fixture
def stale_claim():
    """Claim filed well after the disruption window closed."""
    return Claim(
        claim_id="CLM-20260321-STALE",
        policy_id="POL-TNAGAR-0001",
        user_id="RDR-0001",
        status=ClaimStatus.PENDING,
        disruption_type=DisruptionType.HEAVY_RAIN,
        disruption_severity=0.5,
        trigger_timestamp=NOW - timedelta(days=5),
        location=COORDS_TNAGAR,
        estimated_loss=300.0,
    )


# ─── Disruption event fixtures ───────────────────────────────────────────────

@pytest.fixture
def sample_disruption():
    """Active heavy rain disruption in T. Nagar."""
    return DisruptionEvent(
        event_id="EVT-20260321-001",
        zone_id="zone_tnagar",
        disruption_type=DisruptionType.HEAVY_RAIN,
        severity=0.72,
        start_time=NOW - timedelta(hours=2),
        end_time=None,
        affected_warehouses=["WH-TNAGAR-01"],
        is_active=True,
    )


@pytest.fixture
def ended_disruption():
    """A disruption that has already ended."""
    return DisruptionEvent(
        event_id="EVT-20260320-005",
        zone_id="zone_tnagar",
        disruption_type=DisruptionType.HEAVY_RAIN,
        severity=0.55,
        start_time=NOW - timedelta(days=1, hours=6),
        end_time=NOW - timedelta(days=1, hours=2),
        affected_warehouses=["WH-TNAGAR-01"],
        is_active=False,
    )


# ─── Validation result fixtures ──────────────────────────────────────────────

@pytest.fixture
def all_valid_result():
    """A validation result where every check passes."""
    return ValidationResult(
        policy_valid=True,
        location_valid=True,
        time_valid=True,
        activity_valid=True,
        warehouse_proximity_valid=True,
        zone_activity_valid=True,
        fraud_check_passed=True,
        duplicate_check_passed=True,
        overall_valid=True,
        rejection_reasons=[],
        confidence_score=0.95,
    )
