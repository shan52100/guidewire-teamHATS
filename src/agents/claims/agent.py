"""Claims processing agent.

Validates an incoming claim against policy, location, timing, and activity
rules.  Updates the AgentState with a full ValidationResult and claim status.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2
from typing import Any

from loguru import logger

from src.config.settings import settings
from src.models.schemas import (
    Claim,
    ClaimStatus,
    GeoLocation,
    InsurancePolicy,
    PolicyStatus,
    UserProfile,
    ValidationResult,
    Warehouse,
)


# ── Geo helpers ──────────────────────────────────────────────────────────────

def _haversine_km(loc1: GeoLocation, loc2: GeoLocation) -> float:
    """Great-circle distance in kilometres between two GeoLocations."""
    R = 6371.0  # Earth radius km
    lat1, lon1 = radians(loc1.latitude), radians(loc1.longitude)
    lat2, lon2 = radians(loc2.latitude), radians(loc2.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ── Individual validators ────────────────────────────────────────────────────

def _validate_policy(
    claim: Claim,
    policy: InsurancePolicy | None,
) -> tuple[bool, list[str]]:
    """Check that the policy exists, is active, and covers this claim."""
    reasons: list[str] = []
    if policy is None:
        reasons.append("No policy found for claim")
        return False, reasons

    if policy.status != PolicyStatus.ACTIVE:
        reasons.append(f"Policy status is '{policy.status.value}', expected 'active'")

    if claim.trigger_timestamp < policy.start_date:
        reasons.append("Claim trigger timestamp is before policy start date")

    if policy.end_date and claim.trigger_timestamp > policy.end_date:
        reasons.append("Claim trigger timestamp is after policy end date")

    if claim.policy_id != policy.policy_id:
        reasons.append("Claim policy_id does not match provided policy")

    return len(reasons) == 0, reasons


def _validate_location(
    claim: Claim,
    warehouse: Warehouse | None,
) -> tuple[bool, list[str]]:
    """Verify the claim location is within the warehouse service radius."""
    reasons: list[str] = []
    if warehouse is None:
        reasons.append("No warehouse reference for proximity check")
        return False, reasons

    distance = _haversine_km(claim.location, warehouse.location)
    max_radius = warehouse.radius_km or settings.warehouse_radius_km

    if distance > max_radius:
        reasons.append(
            f"Claim location is {distance:.2f} km from warehouse "
            f"(max {max_radius} km)"
        )

    return len(reasons) == 0, reasons


def _validate_timing(claim: Claim) -> tuple[bool, list[str]]:
    """Ensure the claim was filed within a reasonable window of the trigger."""
    reasons: list[str] = []
    now = datetime.now(tz=timezone.utc)
    trigger = claim.trigger_timestamp.replace(tzinfo=timezone.utc) if claim.trigger_timestamp.tzinfo is None else claim.trigger_timestamp

    # Must not be in the future
    if trigger > now + timedelta(minutes=5):
        reasons.append("Trigger timestamp is in the future")

    # Must be within last 48 hours
    if (now - trigger) > timedelta(hours=48):
        reasons.append("Trigger event is older than 48 hours")

    return len(reasons) == 0, reasons


def _validate_activity(
    claim: Claim,
    user: UserProfile | None,
) -> tuple[bool, list[str]]:
    """Check user activity and claim frequency."""
    reasons: list[str] = []
    if user is None:
        reasons.append("No user profile found for activity validation")
        return False, reasons

    if not user.is_active:
        reasons.append("User account is inactive")

    if user.total_claims >= settings.max_claims_per_week:
        reasons.append(
            f"User has reached max claims per week ({settings.max_claims_per_week})"
        )

    if user.trust_score < settings.min_activity_threshold:
        reasons.append(
            f"User trust score ({user.trust_score:.2f}) below "
            f"activity threshold ({settings.min_activity_threshold})"
        )

    return len(reasons) == 0, reasons


def _validate_location_source(claim: Claim) -> tuple[bool, list[str]]:
    """Flag mock / spoofed location sources."""
    reasons: list[str] = []
    if claim.location.source == "mock":
        reasons.append("Location source is 'mock' – possible GPS spoofing")
    return len(reasons) == 0, reasons


def _check_duplicate(
    claim: Claim,
    user: UserProfile | None,
) -> tuple[bool, list[str]]:
    """Simple duplicate guard based on claim frequency heuristic.

    A more sophisticated version would query the database; here we use the
    user's total_claims as a proxy (high volume within week = suspicious).
    """
    reasons: list[str] = []
    if user is not None and user.total_claims > settings.max_claims_per_week * 2:
        reasons.append("Potential duplicate: unusually high claim count")
    return len(reasons) == 0, reasons


# ── Composite validation ────────────────────────────────────────────────────

def validate_claim(
    claim: Claim,
    policy: InsurancePolicy | None = None,
    user: UserProfile | None = None,
    warehouse: Warehouse | None = None,
) -> ValidationResult:
    """Run all validation checks and return a unified ValidationResult."""
    all_reasons: list[str] = []

    policy_ok, r = _validate_policy(claim, policy)
    all_reasons.extend(r)

    location_ok, r = _validate_location(claim, warehouse)
    all_reasons.extend(r)

    time_ok, r = _validate_timing(claim)
    all_reasons.extend(r)

    activity_ok, r = _validate_activity(claim, user)
    all_reasons.extend(r)

    source_ok, r = _validate_location_source(claim)
    all_reasons.extend(r)

    dup_ok, r = _check_duplicate(claim, user)
    all_reasons.extend(r)

    warehouse_ok = location_ok  # alias for schema field
    zone_ok = True  # zone-level checks delegated to risk agent

    checks = [policy_ok, location_ok, time_ok, activity_ok, source_ok, dup_ok]
    passed = sum(checks)
    total = len(checks)
    confidence = round(passed / total, 3)
    overall = all(checks)

    return ValidationResult(
        policy_valid=policy_ok,
        location_valid=location_ok,
        time_valid=time_ok,
        activity_valid=activity_ok,
        warehouse_proximity_valid=warehouse_ok,
        zone_activity_valid=zone_ok,
        fraud_check_passed=source_ok,
        duplicate_check_passed=dup_ok,
        overall_valid=overall,
        rejection_reasons=all_reasons,
        confidence_score=confidence,
    )


# ── LangGraph node ──────────────────────────────────────────────────────────

async def claims_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: disruption_analyst.

    Reads claim, policy, user, and warehouse from state, validates the claim,
    and writes back the validation result plus an updated claim status.
    """
    logger.info("Claims agent: starting claim validation")

    try:
        claim: Claim | None = state.get("claim")
        if claim is None:
            logger.error("Claims agent: no claim in state")
            return {
                **state,
                "decision": "rejected",
                "error": "No claim provided",
                "reasoning": state.get("reasoning", []) + ["Claims agent: no claim in state"],
            }

        policy: InsurancePolicy | None = state.get("policy")
        user: UserProfile | None = state.get("user")
        warehouse: Warehouse | None = state.get("warehouse")

        validation = validate_claim(claim, policy, user, warehouse)
        logger.info(
            f"Claims agent: validation overall={validation.overall_valid} "
            f"confidence={validation.confidence_score:.2f}"
        )

        reasoning = state.get("reasoning", []).copy()

        if validation.overall_valid:
            claim.status = ClaimStatus.VALIDATING
            reasoning.append(
                f"Claim passed validation (confidence {validation.confidence_score:.2f})"
            )
        else:
            claim.status = ClaimStatus.REJECTED
            reasoning.append(
                f"Claim failed validation: {'; '.join(validation.rejection_reasons)}"
            )

        return {
            **state,
            "claim": claim,
            "validation": validation,
            "decision": "continue" if validation.overall_valid else "rejected",
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.exception("Claims agent failed")
        return {
            **state,
            "decision": "error",
            "error": f"Claims agent error: {exc}",
            "reasoning": state.get("reasoning", []) + [f"Claims agent error: {exc}"],
        }
