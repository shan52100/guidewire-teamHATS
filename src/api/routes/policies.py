"""Policies API routes: subscribe, retrieve, and calculate premiums."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from src.api.middleware.auth import rate_limiter, verify_token
from src.config.settings import settings
from src.models.schemas import (
    GeoLocation,
    InsurancePolicy,
    PolicyStatus,
    PremiumCalculation,
    RiskLevel,
)
from src.utils.helpers import format_currency, generate_id

router = APIRouter(prefix="/policies", tags=["Policies"])

# ─── In-memory policy store (demo) ───────────────────────────────────────────
_policies_db: Dict[str, InsurancePolicy] = {}


# ─── Request / Response models ───────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    """Subscribe to a weekly insurance plan."""
    user_id: str
    zone_id: str
    warehouse_id: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    weeks: int = Field(default=1, ge=1, le=12)


class PremiumCalcRequest(BaseModel):
    """Calculate premium without subscribing."""
    zone_id: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    clean_months: int = Field(default=0, ge=0, le=60)
    weeks: int = Field(default=1, ge=1, le=12)


class SubscribeResponse(BaseModel):
    policy: InsurancePolicy
    premium_details: PremiumCalculation
    message: str


# ─── Premium calculation ─────────────────────────────────────────────────────

def _calculate_premium(
    zone_id: str,
    risk_level: RiskLevel,
    clean_months: int = 0,
    weeks: int = 1,
) -> PremiumCalculation:
    """Compute the final weekly premium based on risk, zone, and history.

    Formula:
        final = base_premium * risk_multiplier * zone_factor * (1 - history_discount) * weeks
    """
    base = settings.base_premium_weekly
    risk_mult = settings.premium_risk_multipliers.get(risk_level.value, 1.0)
    zone_factor = settings.premium_zone_factors.get(zone_id, 1.0)
    history_disc = min(
        clean_months * settings.history_discount_per_clean_month,
        settings.max_history_discount,
    )

    final = round(base * risk_mult * zone_factor * (1 - history_disc) * weeks, 2)

    # Coverage is a function of premium
    coverage = round(final * 15, 2)  # ~15x leverage
    coverage = max(settings.min_coverage_amount, min(coverage, settings.max_coverage_amount))

    return PremiumCalculation(
        base_premium=base,
        risk_multiplier=risk_mult,
        zone_factor=zone_factor,
        history_discount=round(history_disc, 4),
        final_premium=final,
        breakdown={
            "base_premium_weekly": base,
            "risk_multiplier": risk_mult,
            "zone_factor": zone_factor,
            "history_discount_pct": round(history_disc * 100, 1),
            "weeks": weeks,
            "coverage_amount": coverage,
            "formula": f"{base} * {risk_mult} * {zone_factor} * (1 - {history_disc:.2f}) * {weeks}",
        },
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a weekly insurance plan",
    dependencies=[Depends(rate_limiter)],
)
async def subscribe(
    req: SubscribeRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> SubscribeResponse:
    """Create a new insurance policy for a delivery partner (weekly plan)."""
    premium = _calculate_premium(
        zone_id=req.zone_id,
        risk_level=req.risk_level,
        clean_months=0,
        weeks=req.weeks,
    )

    now = datetime.utcnow()
    policy_id = generate_id("POL")
    coverage_amount = premium.breakdown.get("coverage_amount", settings.min_coverage_amount)

    policy = InsurancePolicy(
        policy_id=policy_id,
        user_id=req.user_id,
        status=PolicyStatus.ACTIVE,
        premium_amount=premium.final_premium,
        coverage_amount=coverage_amount,
        start_date=now,
        end_date=now + timedelta(weeks=req.weeks),
        zone_id=req.zone_id,
        warehouse_id=req.warehouse_id,
        risk_level=req.risk_level,
        created_at=now,
    )

    _policies_db[policy_id] = policy
    logger.info(
        "Policy {} created for user {} | premium={} coverage={}",
        policy_id,
        req.user_id,
        format_currency(premium.final_premium),
        format_currency(coverage_amount),
    )

    return SubscribeResponse(
        policy=policy,
        premium_details=premium,
        message=f"Policy {policy_id} activated. Coverage: {format_currency(coverage_amount)} for {req.weeks} week(s).",
    )


@router.get(
    "/{policy_id}",
    response_model=InsurancePolicy,
    summary="Get a policy by ID",
)
async def get_policy(
    policy_id: str,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> InsurancePolicy:
    """Retrieve a single policy by its ID."""
    policy = _policies_db.get(policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )
    return policy


@router.get(
    "/user/{user_id}",
    response_model=List[InsurancePolicy],
    summary="Get all policies for a user",
)
async def get_user_policies(
    user_id: str,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> List[InsurancePolicy]:
    """Retrieve all policies belonging to a specific user."""
    user_policies = [p for p in _policies_db.values() if p.user_id == user_id]
    return sorted(user_policies, key=lambda p: p.created_at, reverse=True)


@router.post(
    "/calculate-premium",
    response_model=PremiumCalculation,
    summary="Calculate premium without subscribing",
    dependencies=[Depends(rate_limiter)],
)
async def calculate_premium(
    req: PremiumCalcRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> PremiumCalculation:
    """Preview the premium for a given zone, risk level, and history without creating a policy."""
    premium = _calculate_premium(
        zone_id=req.zone_id,
        risk_level=req.risk_level,
        clean_months=req.clean_months,
        weeks=req.weeks,
    )
    logger.debug("Premium calculation preview: {}", premium.final_premium)
    return premium
