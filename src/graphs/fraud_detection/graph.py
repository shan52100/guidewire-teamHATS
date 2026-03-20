"""Multi-layer fraud detection sub-graph.

Layers:
1. **Rule-based checks** -- hard limits on claim frequency, amount, timing.
2. **ML anomaly detection** -- statistical outlier scoring using z-scores.
3. **Cross-claim correlation** -- detects coordinated / duplicate claim patterns.

Each layer contributes a partial fraud score; the final score is a weighted average.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
from loguru import logger

from src.config.settings import settings
from src.models.schemas import AgentState, Claim, FraudFlag


# ─── In-memory claim store for correlation (demo) ────────────────────────────
_recent_claims: List[Claim] = []


def _record_claim(claim: Claim) -> None:
    """Keep a rolling window of recent claims for cross-correlation."""
    _recent_claims.append(claim)
    cutoff = datetime.utcnow() - timedelta(days=7)
    while _recent_claims and _recent_claims[0].created_at < cutoff:
        _recent_claims.pop(0)


# ─── Layer 1: Rule-based checks ──────────────────────────────────────────────

def _rule_based_checks(state: AgentState) -> Tuple[float, List[str]]:
    """Apply deterministic business rules.

    Returns:
        ``(score, reasons)`` where score is in [0, 1].
    """
    score = 0.0
    reasons: List[str] = []
    claim = state.claim
    user = state.user

    if claim is None or user is None:
        return 0.0, reasons

    # R1: Too many total claims
    if user.total_claims > settings.max_claims_per_week * 4:
        penalty = min(0.3, user.total_claims * 0.01)
        score += penalty
        reasons.append(f"High claim count ({user.total_claims} total)")

    # R2: Claim amount vs coverage
    if state.policy and claim.estimated_loss > state.policy.coverage_amount * 0.9:
        score += 0.15
        reasons.append("Estimated loss near policy coverage cap")

    # R3: Low trust score
    if user.trust_score < 0.3:
        score += 0.2
        reasons.append(f"Low trust score ({user.trust_score:.2f})")

    # R4: High risk score
    if user.risk_score > 0.7:
        score += 0.15
        reasons.append(f"High risk score ({user.risk_score:.2f})")

    # R5: Claim submitted at unusual hour (midnight - 5am local)
    hour = claim.trigger_timestamp.hour
    if 0 <= hour < 5:
        score += 0.1
        reasons.append(f"Claim at unusual hour ({hour}:00)")

    # R6: GPS source is mock
    if claim.location.source == "mock":
        score += 0.2
        reasons.append("GPS source marked as mock")

    return min(score, 1.0), reasons


# ─── Layer 2: ML anomaly detection ───────────────────────────────────────────

def _anomaly_detection(state: AgentState) -> Tuple[float, List[str]]:
    """Statistical outlier scoring using z-score analysis on claim features.

    Returns:
        ``(score, reasons)`` where score is in [0, 1].
    """
    score = 0.0
    reasons: List[str] = []
    claim = state.claim

    if claim is None:
        return 0.0, reasons

    # Build feature vector from recent claims
    if len(_recent_claims) < 5:
        return 0.0, reasons  # Not enough data

    amounts = np.array([c.estimated_loss for c in _recent_claims])
    severities = np.array([c.disruption_severity for c in _recent_claims])

    # Z-score for estimated loss
    mean_amt, std_amt = float(np.mean(amounts)), float(np.std(amounts))
    if std_amt > 0:
        z_amount = abs(claim.estimated_loss - mean_amt) / std_amt
        if z_amount > settings.fraud_anomaly_zscore:
            penalty = min(0.3, (z_amount - settings.fraud_anomaly_zscore) * 0.1)
            score += penalty
            reasons.append(f"Estimated loss is statistical outlier (z={z_amount:.2f})")

    # Z-score for severity
    mean_sev, std_sev = float(np.mean(severities)), float(np.std(severities))
    if std_sev > 0:
        z_sev = abs(claim.disruption_severity - mean_sev) / std_sev
        if z_sev > settings.fraud_anomaly_zscore:
            penalty = min(0.2, (z_sev - settings.fraud_anomaly_zscore) * 0.08)
            score += penalty
            reasons.append(f"Disruption severity is statistical outlier (z={z_sev:.2f})")

    return min(score, 1.0), reasons


# ─── Layer 3: Cross-claim correlation ────────────────────────────────────────

def _cross_claim_correlation(state: AgentState) -> Tuple[float, List[str]]:
    """Detect coordinated / duplicate claims.

    Checks:
    - Same user claiming multiple times in a short window.
    - Multiple users claiming from suspiciously close locations at the same time.

    Returns:
        ``(score, reasons)`` where score is in [0, 1].
    """
    score = 0.0
    reasons: List[str] = []
    claim = state.claim

    if claim is None:
        return 0.0, reasons

    now = datetime.utcnow()
    dup_window = timedelta(hours=settings.fraud_duplicate_window_hours)

    # Same-user duplicates
    user_recent = [
        c for c in _recent_claims
        if c.user_id == claim.user_id
        and c.claim_id != claim.claim_id
        and (now - c.created_at) < dup_window
    ]
    if len(user_recent) >= settings.fraud_max_claims_per_day:
        score += 0.35
        reasons.append(
            f"User has {len(user_recent)} claims in last "
            f"{settings.fraud_duplicate_window_hours}h (limit {settings.fraud_max_claims_per_day})"
        )

    # Location-cluster check: any other user's claim within cluster radius?
    for other in _recent_claims:
        if other.user_id == claim.user_id or other.claim_id == claim.claim_id:
            continue
        if (now - other.created_at) > dup_window:
            continue
        # Quick lat/lon distance approximation (degrees -> km at Chennai latitude)
        dlat = abs(claim.location.latitude - other.location.latitude) * 111.0
        dlon = abs(claim.location.longitude - other.location.longitude) * 111.0 * math.cos(
            math.radians(claim.location.latitude)
        )
        approx_dist = math.sqrt(dlat ** 2 + dlon ** 2)
        if approx_dist < settings.fraud_cluster_radius_km:
            score += 0.15
            reasons.append(
                f"Claim location within {settings.fraud_cluster_radius_km} km of "
                f"claim {other.claim_id} by user {other.user_id}"
            )
            break  # one match is enough

    return min(score, 1.0), reasons


# ─── Orchestrator ─────────────────────────────────────────────────────────────

async def run_fraud_detection(state: AgentState) -> AgentState:
    """Execute all fraud-detection layers and update the agent state.

    The final fraud score is a weighted combination:
    - Rule-based:       40%
    - Anomaly (ML):     30%
    - Cross-correlation: 30%

    Args:
        state: Current pipeline state.

    Returns:
        Updated state with ``fraud_score`` and reasoning populated.
    """
    if state.claim is None:
        logger.warning("Fraud detection skipped: no claim in state")
        return state

    # Record claim for future correlation
    _record_claim(state.claim)

    # Run layers
    rule_score, rule_reasons = _rule_based_checks(state)
    anomaly_score, anomaly_reasons = _anomaly_detection(state)
    corr_score, corr_reasons = _cross_claim_correlation(state)

    # Weighted combination
    final_score = round(
        rule_score * 0.40 + anomaly_score * 0.30 + corr_score * 0.30,
        3,
    )

    state.fraud_score = final_score
    all_reasons = rule_reasons + anomaly_reasons + corr_reasons
    if all_reasons:
        state.reasoning.append(f"Fraud detection score: {final_score:.3f}")
        state.reasoning.extend([f"  - {r}" for r in all_reasons])

    # Set fraud flag on claim
    if final_score >= settings.fraud_score_threshold:
        state.claim.fraud_score = final_score
        logger.warning(
            "Claim {} flagged: fraud_score={:.3f} reasons={}",
            state.claim.claim_id,
            final_score,
            all_reasons,
        )
    else:
        state.claim.fraud_score = final_score
        logger.info("Claim {} fraud check passed (score={:.3f})", state.claim.claim_id, final_score)

    return state
