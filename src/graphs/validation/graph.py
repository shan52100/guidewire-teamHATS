"""Validation sub-graph: runs all verification checks against a claim.

Checks performed:
1. ``policy_valid``            -- policy is active and covers the period.
2. ``location_valid``          -- coordinates are valid and not spoofed.
3. ``time_valid``              -- trigger timestamp falls within policy window.
4. ``activity_valid``          -- rider was active on the platform recently.
5. ``warehouse_proximity``     -- rider is within operational radius of warehouse.
6. ``zone_activity``           -- zone had real order activity at claim time.
7. ``duplicate_check``         -- no duplicate claim in the cooldown window.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from loguru import logger

from src.config.settings import settings
from src.models.schemas import (
    AgentState,
    ClaimStatus,
    PolicyStatus,
    ValidationResult,
)
from src.services.delivery import DeliveryPlatformService
from src.services.location import LocationService

# Shared service instances (lightweight, no external connections)
_location_svc = LocationService()
_delivery_svc = DeliveryPlatformService()

# In-memory claim ID set for duplicate detection (demo)
_processed_claim_ids: dict[str, datetime] = {}


async def _check_policy(state: AgentState) -> tuple[bool, str]:
    """Verify the policy is active and the trigger falls within its coverage window."""
    policy = state.policy
    claim = state.claim
    if policy is None or claim is None:
        return False, "Policy or claim data missing"

    if policy.status != PolicyStatus.ACTIVE:
        return False, f"Policy status is {policy.status.value}"

    if not (policy.start_date <= claim.trigger_timestamp <= policy.end_date):
        return False, (
            f"Trigger timestamp {claim.trigger_timestamp.isoformat()} outside "
            f"policy window [{policy.start_date.isoformat()} - {policy.end_date.isoformat()}]"
        )
    return True, "Policy is active and covers claim period"


async def _check_location(state: AgentState) -> tuple[bool, str]:
    """Validate coordinates and run GPS spoofing check."""
    claim = state.claim
    user = state.user
    if claim is None or user is None:
        return False, "Claim or user data missing"

    valid, msg = _location_svc.validate_coordinates_check(
        claim.location.latitude,
        claim.location.longitude,
    )
    if not valid:
        return False, msg

    is_suspicious, spoof_reasons = _location_svc.detect_gps_spoofing(
        user.user_id,
        claim.location,
        max_velocity_kmh=settings.fraud_velocity_threshold_kmh,
    )
    if is_suspicious:
        return False, f"GPS spoofing suspected: {'; '.join(spoof_reasons)}"

    return True, "Location coordinates valid"


async def _check_time(state: AgentState) -> tuple[bool, str]:
    """Ensure the trigger timestamp is recent (within 24 hours)."""
    claim = state.claim
    if claim is None:
        return False, "Claim data missing"

    now = datetime.utcnow()
    delta = now - claim.trigger_timestamp
    if delta > timedelta(hours=24):
        return False, f"Trigger is {delta.total_seconds() / 3600:.1f}h old; max 24h"
    if delta < timedelta(seconds=0):
        return False, "Trigger timestamp is in the future"
    return True, "Trigger timestamp is within acceptable window"


async def _check_activity(state: AgentState) -> tuple[bool, str]:
    """Verify the rider was active on the delivery platform recently."""
    user = state.user
    if user is None:
        return False, "User data missing"

    rider_status = await _delivery_svc.get_rider_status(user.user_id)
    if not rider_status.get("is_online") and rider_status.get("status") != "online":
        # Check if they were online in the last few hours (recent order)
        orders = await _delivery_svc.get_order_history(user.user_id, hours=4)
        if len(orders) < 1:
            return False, "Rider has no recent orders and is offline"
    return True, "Rider was active on platform"


async def _check_warehouse_proximity(state: AgentState) -> tuple[bool, str]:
    """Verify the claim location is within range of the assigned warehouse."""
    claim = state.claim
    warehouse = state.warehouse
    if claim is None or warehouse is None:
        return False, "Claim or warehouse data missing"

    valid, dist = _location_svc.validate_warehouse_proximity(claim.location, warehouse)
    if not valid:
        return False, f"Location is {dist:.2f} km from warehouse (max {warehouse.radius_km} km)"
    return True, f"Within warehouse range ({dist:.2f} km)"


async def _check_zone_activity(state: AgentState) -> tuple[bool, str]:
    """Verify the zone had genuine delivery activity at claim time."""
    zone = state.zone
    if zone is None:
        return False, "Zone data missing"

    activity = await _delivery_svc.get_zone_activity(zone.zone_id)
    orders = activity.get("orders_last_hour", 0)
    if orders < settings.min_activity_threshold * zone.avg_order_density:
        return False, (
            f"Zone {zone.zone_id} activity too low ({orders} orders/h vs "
            f"expected {zone.avg_order_density})"
        )
    return True, f"Zone activity confirmed ({orders} orders/h)"


async def _check_duplicate(state: AgentState) -> tuple[bool, str]:
    """Check for duplicate claims from the same user within the cooldown window."""
    claim = state.claim
    user = state.user
    if claim is None or user is None:
        return False, "Claim or user data missing"

    cooldown = timedelta(hours=settings.cooldown_hours)
    now = datetime.utcnow()

    for cid, ts in list(_processed_claim_ids.items()):
        # Prune old entries
        if now - ts > timedelta(days=7):
            del _processed_claim_ids[cid]

    # Check for recent claims from same user
    user_prefix = f"{user.user_id}:"
    for key, ts in _processed_claim_ids.items():
        if key.startswith(user_prefix) and (now - ts) < cooldown:
            return False, (
                f"Duplicate claim: user {user.user_id} already claimed "
                f"{(now - ts).total_seconds() / 3600:.1f}h ago (cooldown={settings.cooldown_hours}h)"
            )

    # Record this claim
    _processed_claim_ids[f"{user.user_id}:{claim.claim_id}"] = now
    return True, "No duplicate claims detected"


# ─── Orchestrator ─────────────────────────────────────────────────────────────

async def run_validation(state: AgentState) -> AgentState:
    """Execute all validation checks and populate ``state.validation``.

    The overall result is ``True`` only when **all** individual checks pass.
    A confidence score is computed as the fraction of passed checks.

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with :class:`ValidationResult` attached.
    """
    checks = {
        "policy_valid": _check_policy,
        "location_valid": _check_location,
        "time_valid": _check_time,
        "activity_valid": _check_activity,
        "warehouse_proximity_valid": _check_warehouse_proximity,
        "zone_activity_valid": _check_zone_activity,
        "duplicate_check_passed": _check_duplicate,
    }

    results: dict[str, bool] = {}
    rejection_reasons: List[str] = []

    for field_name, check_fn in checks.items():
        try:
            passed, reason = await check_fn(state)
        except Exception as exc:
            logger.error("Validation check {} raised: {}", field_name, exc)
            passed, reason = False, f"Check error: {exc}"

        results[field_name] = passed
        if not passed:
            rejection_reasons.append(f"[{field_name}] {reason}")
            logger.debug("Validation FAIL: {} - {}", field_name, reason)
        else:
            logger.debug("Validation PASS: {} - {}", field_name, reason)

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    confidence = round(passed_count / total_count, 2) if total_count > 0 else 0.0
    overall = all(results.values())

    validation = ValidationResult(
        policy_valid=results.get("policy_valid", False),
        location_valid=results.get("location_valid", False),
        time_valid=results.get("time_valid", False),
        activity_valid=results.get("activity_valid", False),
        warehouse_proximity_valid=results.get("warehouse_proximity_valid", False),
        zone_activity_valid=results.get("zone_activity_valid", False),
        fraud_check_passed=state.fraud_score < settings.fraud_score_threshold,
        duplicate_check_passed=results.get("duplicate_check_passed", False),
        overall_valid=overall,
        rejection_reasons=rejection_reasons,
        confidence_score=confidence,
    )

    state.validation = validation
    state.reasoning.append(
        f"Validation complete: {passed_count}/{total_count} checks passed "
        f"(confidence={confidence:.2f}, overall={'PASS' if overall else 'FAIL'})"
    )

    if state.claim:
        state.claim.validation_results = validation

    logger.info(
        "Validation for claim {}: {} ({}/{})",
        state.claim.claim_id if state.claim else "?",
        "PASS" if overall else "FAIL",
        passed_count,
        total_count,
    )
    return state
