"""Admin API routes: dashboard stats, fraud queue, overrides, zone management."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from src.api.middleware.auth import verify_token
from src.config.settings import settings
from src.models.schemas import (
    Claim,
    ClaimStatus,
    GeoLocation,
    RiskLevel,
    Zone,
)
from src.utils.helpers import format_currency

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── Shared references to in-memory stores ───────────────────────────────────
# These are imported lazily to avoid circular imports at module level.

def _get_claims_db() -> Dict[str, Claim]:
    from src.api.routes.claims import _claims_db
    return _claims_db


def _get_states_db() -> Dict[str, Any]:
    from src.api.routes.claims import _states_db
    return _states_db


def _get_users_db() -> Dict[str, Any]:
    from src.api.routes.users import _users_db
    return _users_db


def _get_policies_db() -> Dict[str, Any]:
    from src.api.routes.policies import _policies_db
    return _policies_db


# ─── Zone data ────────────────────────────────────────────────────────────────

_ZONES: List[Zone] = [
    Zone(
        zone_id="CHN-TNG",
        name="T. Nagar",
        center=GeoLocation(latitude=13.0418, longitude=80.2341),
        radius_km=5.0,
        risk_level=RiskLevel.MEDIUM,
        avg_order_density=45.0,
    ),
    Zone(
        zone_id="CHN-VLC",
        name="Velachery",
        center=GeoLocation(latitude=12.9815, longitude=80.2180),
        radius_km=5.0,
        risk_level=RiskLevel.HIGH,
        avg_order_density=38.0,
    ),
    Zone(
        zone_id="CHN-ANG",
        name="Anna Nagar",
        center=GeoLocation(latitude=13.0850, longitude=80.2101),
        radius_km=5.0,
        risk_level=RiskLevel.LOW,
        avg_order_density=55.0,
    ),
    Zone(
        zone_id="CHN-MYL",
        name="Mylapore",
        center=GeoLocation(latitude=13.0368, longitude=80.2676),
        radius_km=4.0,
        risk_level=RiskLevel.MEDIUM,
        avg_order_density=42.0,
    ),
    Zone(
        zone_id="CHN-ADR",
        name="Adyar",
        center=GeoLocation(latitude=13.0067, longitude=80.2572),
        radius_km=4.5,
        risk_level=RiskLevel.HIGH,
        avg_order_density=40.0,
    ),
]


# ─── Response models ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int
    total_policies: int
    total_claims: int
    claims_by_status: Dict[str, int]
    total_payouts: str
    avg_fraud_score: float
    flagged_claims: int
    approval_rate: float
    active_zones: int


class FraudQueueItem(BaseModel):
    claim: Claim
    fraud_score: float
    reasoning: List[str]


class OverrideRequest(BaseModel):
    new_status: ClaimStatus
    reason: str
    admin_id: str
    payout_amount: Optional[float] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Admin dashboard statistics",
)
async def get_dashboard(
    token_data: Dict[str, Any] = Depends(verify_token),
) -> DashboardStats:
    """Aggregate statistics for the admin dashboard."""
    claims_db = _get_claims_db()
    users_db = _get_users_db()
    policies_db = _get_policies_db()

    # Claims by status
    status_counts: Dict[str, int] = {}
    total_payout_amount = 0.0
    fraud_scores: List[float] = []
    approved_count = 0
    resolved_count = 0

    for claim in claims_db.values():
        st = claim.status.value
        status_counts[st] = status_counts.get(st, 0) + 1
        total_payout_amount += claim.approved_payout
        fraud_scores.append(claim.fraud_score)
        if claim.status in (ClaimStatus.APPROVED, ClaimStatus.PAID):
            approved_count += 1
        if claim.status not in (ClaimStatus.PENDING, ClaimStatus.VALIDATING):
            resolved_count += 1

    avg_fraud = round(sum(fraud_scores) / len(fraud_scores), 3) if fraud_scores else 0.0
    approval_rate = round(approved_count / resolved_count, 3) if resolved_count > 0 else 0.0
    flagged = status_counts.get("flagged", 0)

    stats = DashboardStats(
        total_users=len(users_db),
        total_policies=len(policies_db),
        total_claims=len(claims_db),
        claims_by_status=status_counts,
        total_payouts=format_currency(total_payout_amount),
        avg_fraud_score=avg_fraud,
        flagged_claims=flagged,
        approval_rate=approval_rate,
        active_zones=len(_ZONES),
    )

    logger.debug("Dashboard stats generated: {} claims, {} users", stats.total_claims, stats.total_users)
    return stats


@router.get(
    "/fraud-queue",
    response_model=List[FraudQueueItem],
    summary="Get flagged/suspicious claims for review",
)
async def get_fraud_queue(
    token_data: Dict[str, Any] = Depends(verify_token),
) -> List[FraudQueueItem]:
    """Return all claims flagged for manual fraud review, ordered by fraud score descending."""
    claims_db = _get_claims_db()
    states_db = _get_states_db()

    queue: List[FraudQueueItem] = []
    for claim_id, claim in claims_db.items():
        if claim.status == ClaimStatus.FLAGGED or claim.fraud_score >= settings.fraud_score_threshold:
            state = states_db.get(claim_id)
            reasoning = state.reasoning if state else []
            queue.append(
                FraudQueueItem(
                    claim=claim,
                    fraud_score=claim.fraud_score,
                    reasoning=reasoning,
                )
            )

    queue.sort(key=lambda item: item.fraud_score, reverse=True)
    logger.debug("Fraud queue returned {} items", len(queue))
    return queue


@router.post(
    "/override/{claim_id}",
    response_model=Claim,
    summary="Admin override a claim decision",
)
async def admin_override(
    claim_id: str,
    req: OverrideRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> Claim:
    """Allow an admin to manually approve, reject, or re-flag a claim."""
    claims_db = _get_claims_db()
    states_db = _get_states_db()

    claim = claims_db.get(claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    old_status = claim.status
    claim.status = req.new_status
    claim.resolved_at = datetime.utcnow()

    if req.payout_amount is not None and req.new_status in (ClaimStatus.APPROVED, ClaimStatus.PAID):
        claim.approved_payout = min(req.payout_amount, settings.payout_cap_per_claim)

    # Audit trail
    state = states_db.get(claim_id)
    if state:
        state.reasoning.append(
            f"[ADMIN] {req.admin_id}: override {old_status.value} -> {req.new_status.value} | {req.reason}"
        )

    claims_db[claim_id] = claim
    logger.info(
        "Admin override on {}: {} -> {} by {}",
        claim_id,
        old_status.value,
        req.new_status.value,
        req.admin_id,
    )

    return claim


@router.get(
    "/zones",
    response_model=List[Zone],
    summary="List all configured zones",
)
async def list_zones(
    token_data: Dict[str, Any] = Depends(verify_token),
) -> List[Zone]:
    """Return all zones configured in the system with their risk levels and metadata."""
    return _ZONES
