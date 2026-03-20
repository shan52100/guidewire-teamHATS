"""Claims API routes: trigger, retrieve, and admin-override claims."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from src.api.middleware.auth import rate_limiter, verify_token
from src.config.settings import settings
from src.graphs.decision import route_after_disruption, route_after_validation, should_process_claim
from src.graphs.fraud_detection import run_fraud_detection
from src.graphs.validation import run_validation
from src.models.schemas import (
    AgentState,
    Claim,
    ClaimStatus,
    DisruptionType,
    GeoLocation,
    IncomeLossCalculation,
    PayoutRequest,
)
from src.services.delivery import DeliveryPlatformService
from src.services.payment import PaymentService
from src.services.weather import WeatherService
from src.utils.helpers import format_currency, generate_id

router = APIRouter(prefix="/claims", tags=["Claims"])

# ─── Shared services ─────────────────────────────────────────────────────────
_weather_svc = WeatherService(mock=True)
_delivery_svc = DeliveryPlatformService()
_payment_svc = PaymentService()

# ─── In-memory claim store (demo) ────────────────────────────────────────────
_claims_db: Dict[str, Claim] = {}
_states_db: Dict[str, AgentState] = {}


# ─── Request / Response models ───────────────────────────────────────────────

class ClaimTriggerRequest(BaseModel):
    """Payload for auto-triggering a claim from weather / disruption data."""
    user_id: str
    policy_id: str
    zone_id: str
    latitude: float
    longitude: float
    disruption_type: DisruptionType
    disruption_severity: float = Field(ge=0.0, le=1.0)


class ClaimOverrideRequest(BaseModel):
    """Payload for an admin manually overriding a claim decision."""
    new_status: ClaimStatus
    reason: str
    admin_id: str
    payout_amount: Optional[float] = None


class ClaimResponse(BaseModel):
    claim: Claim
    decision: str
    reasoning: List[str]
    payout: Optional[Dict[str, Any]] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/trigger",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-trigger a claim from weather/disruption event",
    dependencies=[Depends(rate_limiter)],
)
async def trigger_claim(
    req: ClaimTriggerRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> ClaimResponse:
    """Create and process a new parametric claim triggered by a disruption event.

    The endpoint runs the full pipeline: gate check -> weather analysis ->
    validation -> fraud detection -> decision -> payout.
    """
    # Build claim
    claim_id = generate_id("CLM")
    now = datetime.utcnow()

    location = GeoLocation(
        latitude=req.latitude,
        longitude=req.longitude,
        timestamp=now,
    )

    # Fetch weather
    weather = await _weather_svc.get_weather(req.latitude, req.longitude, req.zone_id)
    events = await _weather_svc.detect_triggers(weather)

    # Compute estimated income loss
    earnings = await _delivery_svc.get_rider_earnings(req.user_id, days=7)
    lost_hours = max(1.0, req.disruption_severity * 8.0)  # up to 8h loss
    base_loss = earnings["avg_orders_per_hour"] * earnings["avg_income_per_order"] * lost_hours
    severity_mult = 1.0 + req.disruption_severity * 0.5
    adjusted_loss = round(base_loss * severity_mult, 2)
    capped = adjusted_loss > settings.payout_cap_per_claim
    final_payout_amount = min(adjusted_loss, settings.payout_cap_per_claim)

    income_loss = IncomeLossCalculation(
        avg_orders_per_hour=earnings["avg_orders_per_hour"],
        avg_income_per_order=earnings["avg_income_per_order"],
        lost_hours=lost_hours,
        severity_multiplier=severity_mult,
        base_loss=round(base_loss, 2),
        adjusted_loss=adjusted_loss,
        payout_cap_applied=capped,
        final_payout=final_payout_amount,
    )

    claim = Claim(
        claim_id=claim_id,
        policy_id=req.policy_id,
        user_id=req.user_id,
        disruption_type=req.disruption_type,
        disruption_severity=req.disruption_severity,
        trigger_timestamp=now,
        location=location,
        estimated_loss=adjusted_loss,
    )

    # Build pipeline state (lightweight; real objects would be DB lookups)
    from src.models.schemas import InsurancePolicy, PolicyStatus, UserProfile, Zone, Warehouse, RiskLevel

    # Create minimal user/policy/zone/warehouse for pipeline
    user = UserProfile(
        user_id=req.user_id,
        name=earnings.get("user_id", req.user_id),
        phone="0000000000",
        registration_date=now,
        home_location=location,
        delivery_platform="zepto",
    )

    policy = InsurancePolicy(
        policy_id=req.policy_id,
        user_id=req.user_id,
        premium_amount=settings.base_premium_weekly,
        coverage_amount=settings.max_coverage_amount,
        start_date=now - timedelta(days=3),
        end_date=now + timedelta(days=4),
        zone_id=req.zone_id,
        warehouse_id=f"WH-{req.zone_id}-01",
        status=PolicyStatus.ACTIVE,
    )

    zone = Zone(
        zone_id=req.zone_id,
        name=req.zone_id,
        center=GeoLocation(latitude=req.latitude, longitude=req.longitude),
        radius_km=10.0,
        avg_order_density=50.0,
    )

    warehouse = Warehouse(
        warehouse_id=f"WH-{req.zone_id}-01",
        name=f"Warehouse {req.zone_id}",
        zone_id=req.zone_id,
        location=GeoLocation(latitude=req.latitude + 0.005, longitude=req.longitude + 0.005),
    )

    disruption = events[0] if events else None

    state = AgentState(
        claim=claim,
        user=user,
        policy=policy,
        weather=weather,
        disruption=disruption,
        zone=zone,
        warehouse=warehouse,
        income_loss=income_loss,
    )

    # ── Pipeline ──────────────────────────────────────────────────────────
    # Step 1: Gate check
    gate = should_process_claim(state)
    if gate == "reject":
        claim.status = ClaimStatus.REJECTED
        _claims_db[claim_id] = claim
        _states_db[claim_id] = state
        return ClaimResponse(claim=claim, decision="rejected", reasoning=state.reasoning)

    # Step 2: Disruption routing
    disruption_route = route_after_disruption(state)
    if disruption_route == "reject":
        claim.status = ClaimStatus.REJECTED
        _claims_db[claim_id] = claim
        _states_db[claim_id] = state
        return ClaimResponse(claim=claim, decision="rejected", reasoning=state.reasoning)

    # Step 3: Fraud detection
    state = await run_fraud_detection(state)

    # Step 4: Validation (unless auto-approved)
    if disruption_route != "auto_approve":
        state = await run_validation(state)
        final_route = route_after_validation(state)
    else:
        final_route = "approve"
        state.decision = "approved"
        claim.status = ClaimStatus.APPROVED

    # Step 5: Process payout if approved
    payout_result = None
    if final_route == "approve" or disruption_route == "auto_approve":
        claim.status = ClaimStatus.APPROVED
        claim.approved_payout = final_payout_amount

        payout_req = PayoutRequest(
            payout_id=generate_id("PAY"),
            claim_id=claim_id,
            user_id=req.user_id,
            amount=final_payout_amount,
        )
        state.payout = payout_req

        payout_result = await _payment_svc.process_payout(payout_req)
        if payout_result.get("status") == "completed":
            claim.status = ClaimStatus.PAID
            state.decision = "paid"
        state.reasoning.append(
            f"Payout processed: {format_currency(final_payout_amount)} | status={payout_result.get('status')}"
        )
    elif final_route == "manual_review":
        claim.status = ClaimStatus.FLAGGED

    claim.resolved_at = datetime.utcnow()
    _claims_db[claim_id] = claim
    _states_db[claim_id] = state

    logger.info("Claim {} processed -> {}", claim_id, state.decision)

    return ClaimResponse(
        claim=claim,
        decision=state.decision,
        reasoning=state.reasoning,
        payout=payout_result,
    )


@router.get(
    "/{claim_id}",
    response_model=Claim,
    summary="Get a claim by ID",
)
async def get_claim(
    claim_id: str,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> Claim:
    """Retrieve a single claim by its ID."""
    claim = _claims_db.get(claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Claim {claim_id} not found")
    return claim


@router.get(
    "/user/{user_id}",
    response_model=List[Claim],
    summary="Get all claims for a user",
)
async def get_user_claims(
    user_id: str,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> List[Claim]:
    """Retrieve all claims belonging to a specific user."""
    user_claims = [c for c in _claims_db.values() if c.user_id == user_id]
    return sorted(user_claims, key=lambda c: c.created_at, reverse=True)


@router.post(
    "/{claim_id}/override",
    response_model=Claim,
    summary="Admin override a claim decision",
)
async def override_claim(
    claim_id: str,
    req: ClaimOverrideRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> Claim:
    """Allow an admin to manually override a claim status (approve/reject/flag)."""
    claim = _claims_db.get(claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Claim {claim_id} not found")

    old_status = claim.status
    claim.status = req.new_status
    claim.resolved_at = datetime.utcnow()

    if req.payout_amount is not None and req.new_status == ClaimStatus.APPROVED:
        claim.approved_payout = min(req.payout_amount, settings.payout_cap_per_claim)

    # Update state reasoning
    state = _states_db.get(claim_id)
    if state:
        state.reasoning.append(
            f"Admin override by {req.admin_id}: {old_status.value} -> {req.new_status.value} | reason: {req.reason}"
        )
        state.decision = req.new_status.value

    logger.info(
        "Claim {} overridden: {} -> {} by admin {}",
        claim_id, old_status.value, req.new_status.value, req.admin_id,
    )

    _claims_db[claim_id] = claim
    return claim
