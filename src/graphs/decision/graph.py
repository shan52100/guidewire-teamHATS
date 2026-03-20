"""Decision routing logic for the insurance claim pipeline.

These functions act as *conditional edges* in the LangGraph state-graph,
deciding which node the pipeline should visit next based on the current
:class:`AgentState`.
"""
from __future__ import annotations

from loguru import logger

from src.config.settings import settings
from src.models.schemas import AgentState, ClaimStatus, PolicyStatus


def should_process_claim(state: AgentState) -> str:
    """Gate: decide whether an incoming claim should be processed at all.

    Returns one of:
        ``"process"``  -- proceed to disruption analysis.
        ``"reject"``   -- reject immediately (missing data, inactive policy, etc.).
        ``"error"``    -- internal error state.
    """
    reasons: list[str] = []

    # Must have basic objects populated
    if state.claim is None:
        reasons.append("No claim object in state")
    if state.user is None:
        reasons.append("No user profile in state")
    if state.policy is None:
        reasons.append("No insurance policy in state")

    if reasons:
        logger.warning("Claim rejected at gate: {}", reasons)
        state.decision = "rejected"
        state.reasoning.extend(reasons)
        return "reject"

    # Policy must be active
    if state.policy.status != PolicyStatus.ACTIVE:
        reason = f"Policy {state.policy.policy_id} status is {state.policy.status.value}, not active"
        state.decision = "rejected"
        state.reasoning.append(reason)
        logger.warning("Claim rejected: {}", reason)
        return "reject"

    # User must be active
    if not state.user.is_active:
        reason = f"User {state.user.user_id} is deactivated"
        state.decision = "rejected"
        state.reasoning.append(reason)
        logger.warning("Claim rejected: {}", reason)
        return "reject"

    # Basic severity check
    if state.claim.disruption_severity <= 0.0:
        reason = "Disruption severity is zero; no actionable event"
        state.decision = "rejected"
        state.reasoning.append(reason)
        return "reject"

    logger.info("Claim {} passed initial gate -> processing", state.claim.claim_id)
    return "process"


def route_after_disruption(state: AgentState) -> str:
    """Route after disruption analysis completes.

    Returns one of:
        ``"validate"``    -- proceed to full validation sub-graph.
        ``"auto_approve"``-- severity high enough for fast-track approval.
        ``"reject"``      -- disruption does not meet threshold.
    """
    if state.disruption is None:
        state.reasoning.append("No disruption event detected by weather service")
        state.decision = "rejected"
        return "reject"

    severity = state.disruption.severity

    # Fast-track for critical events (severity >= 0.8)
    if severity >= 0.8:
        state.reasoning.append(
            f"Critical disruption (severity={severity:.2f}); fast-tracking to approval"
        )
        logger.info("Fast-track approval for critical disruption (severity={:.2f})", severity)
        return "auto_approve"

    # Moderate severity -> full validation
    if severity >= 0.3:
        state.reasoning.append(
            f"Moderate disruption (severity={severity:.2f}); routing to validation"
        )
        return "validate"

    # Low severity -> reject
    state.reasoning.append(
        f"Low disruption severity ({severity:.2f}); below actionable threshold"
    )
    state.decision = "rejected"
    return "reject"


def route_after_validation(state: AgentState) -> str:
    """Route after the validation sub-graph finishes.

    Returns one of:
        ``"approve"``     -- all checks passed.
        ``"manual_review"``-- fraud flagged or borderline confidence.
        ``"reject"``      -- validation failed.
    """
    v = state.validation
    if v is None:
        state.reasoning.append("Validation result missing")
        state.decision = "rejected"
        return "reject"

    # Fraud score too high -> manual review
    if state.fraud_score >= settings.fraud_score_threshold:
        state.reasoning.append(
            f"Fraud score {state.fraud_score:.2f} exceeds threshold "
            f"{settings.fraud_score_threshold}; flagging for manual review"
        )
        state.decision = "flagged"
        if state.claim:
            state.claim.status = ClaimStatus.FLAGGED
        return "manual_review"

    # Overall valid?
    if v.overall_valid:
        # Confidence gate
        if v.confidence_score < 0.5:
            state.reasoning.append(
                f"Validation passed but low confidence ({v.confidence_score:.2f}); manual review"
            )
            state.decision = "flagged"
            return "manual_review"

        state.reasoning.append(
            f"Validation passed (confidence={v.confidence_score:.2f}); approving"
        )
        state.decision = "approved"
        if state.claim:
            state.claim.status = ClaimStatus.APPROVED
        return "approve"

    # Validation failed
    rejection_detail = "; ".join(v.rejection_reasons) if v.rejection_reasons else "Validation checks failed"
    state.reasoning.append(f"Claim rejected: {rejection_detail}")
    state.decision = "rejected"
    if state.claim:
        state.claim.status = ClaimStatus.REJECTED
    return "reject"
