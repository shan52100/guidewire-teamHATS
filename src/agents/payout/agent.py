"""Payout calculation agent.

Computes income-loss based payouts, applies zone-based caps, and handles
payment processing with retry logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

from src.config.settings import settings
from src.models.schemas import (
    Claim,
    ClaimStatus,
    DisruptionEvent,
    IncomeLossCalculation,
    PayoutRequest,
    RiskLevel,
    UserProfile,
    Warehouse,
    Zone,
)


# ── Zone-based payout caps (INR per event) ───────────────────────────────────

ZONE_PAYOUT_CAPS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 350.0,
    RiskLevel.MEDIUM: 500.0,
    RiskLevel.HIGH: 700.0,
    RiskLevel.CRITICAL: 700.0,  # same as HIGH; capped by weekly limit
}

# Default per-order income assumption for delivery partners
DEFAULT_INCOME_PER_ORDER: float = 35.0
DEFAULT_ORDERS_PER_HOUR: float = 3.0


# ── Income loss calculation ──────────────────────────────────────────────────

def calculate_income_loss(
    disruption: DisruptionEvent | None,
    warehouse: Warehouse | None,
    zone: Zone | None,
    user: UserProfile | None,
    claim: Claim | None,
) -> IncomeLossCalculation:
    """Calculate the income loss for a delivery partner.

    Formula:
        Loss = orders_per_hour x income_per_order x lost_hours x severity

    The result is then capped by the zone-based payout cap and the
    system-wide weekly maximum.
    """
    # Resolve parameters with sensible defaults
    orders_per_hour = (
        warehouse.avg_orders_per_hour / 10  # per-partner share assumption
        if warehouse
        else DEFAULT_ORDERS_PER_HOUR
    )

    income_per_order = DEFAULT_INCOME_PER_ORDER

    # Estimate lost hours from disruption duration or default to 3h
    lost_hours = 3.0
    if disruption and disruption.end_time and disruption.start_time:
        delta = (disruption.end_time - disruption.start_time).total_seconds() / 3600
        lost_hours = max(min(delta, 12.0), 0.5)  # clamp 0.5–12 h

    severity = disruption.severity if disruption else (claim.disruption_severity if claim else 0.5)

    # Base loss
    base_loss = orders_per_hour * income_per_order * lost_hours * severity
    base_loss = round(base_loss, 2)

    # Zone-based cap
    risk_level = zone.risk_level if zone else RiskLevel.MEDIUM
    cap = ZONE_PAYOUT_CAPS.get(risk_level, 500.0)
    cap_applied = base_loss > cap
    adjusted_loss = min(base_loss, cap)

    # Weekly cap
    weekly_remaining = settings.max_weekly_payout - (user.total_payouts if user else 0.0)
    if adjusted_loss > weekly_remaining:
        adjusted_loss = max(weekly_remaining, 0.0)
        cap_applied = True

    final_payout = round(adjusted_loss, 2)

    return IncomeLossCalculation(
        avg_orders_per_hour=orders_per_hour,
        avg_income_per_order=income_per_order,
        lost_hours=lost_hours,
        severity_multiplier=severity,
        base_loss=base_loss,
        adjusted_loss=adjusted_loss,
        payout_cap_applied=cap_applied,
        final_payout=final_payout,
    )


# ── Payment processing with retry ───────────────────────────────────────────

class PaymentGatewayError(Exception):
    """Raised when the payment gateway returns a transient error."""


@retry(
    retry=retry_if_exception_type(PaymentGatewayError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _send_payment(payout: PayoutRequest) -> PayoutRequest:
    """Simulate or invoke a real payment gateway with automatic retries.

    In production, this would call a UPI / NEFT / IMPS API.
    When ``settings.mock_payment_gateway`` is True (default in dev), it
    always succeeds immediately.
    """
    if settings.mock_payment_gateway:
        logger.info(
            f"Mock payment gateway: ₹{payout.amount:.2f} → user {payout.user_id}"
        )
        payout.status = "completed"
        return payout

    # Placeholder for real gateway integration
    # async with httpx.AsyncClient(timeout=15.0) as client:
    #     resp = await client.post(PAYMENT_URL, json=payout.model_dump())
    #     if resp.status_code >= 500:
    #         raise PaymentGatewayError(f"Gateway error {resp.status_code}")
    #     resp.raise_for_status()
    #     payout.status = "completed"
    raise PaymentGatewayError("Real payment gateway not configured")


async def process_payment(payout: PayoutRequest) -> PayoutRequest:
    """Process a payout with retry logic, updating status appropriately."""
    payout.status = "processing"
    try:
        payout = await _send_payment(payout)
        logger.info(f"Payment completed: payout_id={payout.payout_id}")
    except RetryError:
        payout.status = "failed"
        payout.retry_count = payout.max_retries
        logger.error(
            f"Payment failed after {payout.max_retries} retries: "
            f"payout_id={payout.payout_id}"
        )
    except Exception as exc:
        payout.status = "failed"
        logger.error(f"Payment error: {exc}")

    return payout


# ── LangGraph node ──────────────────────────────────────────────────────────

async def payout_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: payout_processor.

    Calculates income loss, creates a PayoutRequest, and processes payment.
    """
    logger.info("Payout agent: starting payout calculation")

    try:
        claim: Claim | None = state.get("claim")
        user: UserProfile | None = state.get("user")
        disruption: DisruptionEvent | None = state.get("disruption")
        warehouse: Warehouse | None = state.get("warehouse")
        zone: Zone | None = state.get("zone")

        if claim is None:
            logger.error("Payout agent: no claim in state")
            return {
                **state,
                "error": "No claim for payout",
                "reasoning": state.get("reasoning", []) + ["Payout agent: no claim in state"],
            }

        reasoning = state.get("reasoning", []).copy()

        # ── Calculate income loss ────────────────────────────────────────
        income_loss = calculate_income_loss(
            disruption=disruption,
            warehouse=warehouse,
            zone=zone,
            user=user,
            claim=claim,
        )

        logger.info(
            f"Payout agent: base_loss=₹{income_loss.base_loss:.2f} "
            f"final=₹{income_loss.final_payout:.2f} cap_applied={income_loss.payout_cap_applied}"
        )

        reasoning.append(
            f"Income loss calculated: ₹{income_loss.base_loss:.2f} base → "
            f"₹{income_loss.final_payout:.2f} after caps"
        )

        if income_loss.final_payout <= 0:
            reasoning.append("Final payout is ₹0 – weekly cap exhausted or no loss")
            claim.status = ClaimStatus.REJECTED
            claim.approved_payout = 0.0
            return {
                **state,
                "claim": claim,
                "income_loss": income_loss,
                "decision": "rejected",
                "reasoning": reasoning,
            }

        # ── Create payout request ────────────────────────────────────────
        payout = PayoutRequest(
            payout_id=f"pay-{uuid4().hex[:12]}",
            claim_id=claim.claim_id,
            user_id=claim.user_id,
            amount=income_loss.final_payout,
            status="pending",
            payment_method="upi",
        )

        # ── Process payment ──────────────────────────────────────────────
        payout = await process_payment(payout)

        if payout.status == "completed":
            claim.status = ClaimStatus.PAID
            claim.approved_payout = payout.amount
            claim.resolved_at = datetime.now(tz=timezone.utc)
            reasoning.append(f"Payment completed: ₹{payout.amount:.2f}")
            decision = "approved"
        else:
            claim.status = ClaimStatus.APPROVED  # approved but payment pending
            claim.approved_payout = payout.amount
            reasoning.append(f"Payment {payout.status}: will retry later")
            decision = "payment_pending"

        return {
            **state,
            "claim": claim,
            "income_loss": income_loss,
            "payout": payout,
            "decision": decision,
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.exception("Payout agent failed")
        return {
            **state,
            "error": f"Payout agent error: {exc}",
            "reasoning": state.get("reasoning", []) + [f"Payout agent error: {exc}"],
        }
