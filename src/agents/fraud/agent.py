"""Fraud detection agent.

Combines an Isolation Forest anomaly detector with rule-based GPS spoofing
checks and fraud-ring heuristics to produce a composite fraud score.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2
from typing import Any

import numpy as np
from loguru import logger
from sklearn.ensemble import IsolationForest

from src.config.settings import settings
from src.models.schemas import (
    Claim,
    ClaimStatus,
    FraudFlag,
    GeoLocation,
    UserProfile,
)


# ── Constants ────────────────────────────────────────────────────────────────

FRAUD_THRESHOLD: float = settings.fraud_score_threshold  # 0.7
MAX_VELOCITY_KPH: float = 120.0   # max realistic delivery-partner speed
MIN_GPS_ACCURACY_M: float = 5.0   # suspiciously precise GPS
TEMPORAL_CLUSTER_WINDOW_MIN: int = 15  # fraud ring temporal window


# ── Haversine helper ─────────────────────────────────────────────────────────

def _haversine_km(loc1: GeoLocation, loc2: GeoLocation) -> float:
    R = 6371.0
    lat1, lon1 = radians(loc1.latitude), radians(loc1.longitude)
    lat2, lon2 = radians(loc2.latitude), radians(loc2.longitude)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ── Isolation Forest anomaly detector ───────────────────────────────────────

def _build_feature_vector(
    claim: Claim,
    user: UserProfile,
    claim_history: list[Claim] | None = None,
) -> np.ndarray:
    """Build a feature vector for the Isolation Forest from claim + user data.

    Features (7-dim):
        0 - claim_frequency        : total claims normalised (0-1)
        1 - gps_accuracy           : location accuracy in metres (lower = more suspicious if too precise)
        2 - payout_ratio           : estimated loss relative to mean
        3 - trust_score_inv        : 1 - trust_score (higher = riskier)
        4 - time_since_last_claim  : hours since registration as proxy (lower = riskier)
        5 - location_source_flag   : 1 if mock, else 0
        6 - severity               : disruption severity claimed
    """
    freq = min(user.total_claims / max(settings.max_claims_per_week, 1), 1.0)

    accuracy = claim.location.accuracy_meters or 15.0
    gps_feat = 1.0 - min(accuracy / 100.0, 1.0)  # very precise → high value

    mean_payout = 300.0  # assumed average payout baseline
    payout_ratio = min(claim.estimated_loss / max(mean_payout, 1.0), 3.0) / 3.0

    trust_inv = 1.0 - user.trust_score

    reg_date = user.registration_date.replace(tzinfo=timezone.utc) if user.registration_date.tzinfo is None else user.registration_date
    hours_since_reg = max(
        (datetime.now(tz=timezone.utc) - reg_date).total_seconds() / 3600, 0.1
    )
    time_feat = 1.0 - min(hours_since_reg / (30 * 24), 1.0)  # new accounts → high

    source_flag = 1.0 if claim.location.source == "mock" else 0.0
    severity = claim.disruption_severity

    return np.array([
        [freq, gps_feat, payout_ratio, trust_inv, time_feat, source_flag, severity]
    ])


def _isolation_forest_score(feature_vector: np.ndarray) -> float:
    """Train a one-class Isolation Forest on a synthetic reference set and
    score the incoming sample.  Returns a fraud probability in [0, 1].

    In production this model would be pre-trained on historical data and
    loaded from disk; here we generate a small reference distribution
    representing normal claims and score the new observation against it.
    """
    rng = np.random.RandomState(42)

    # Synthetic reference: 200 'normal' claims
    n_ref = 200
    ref = np.column_stack([
        rng.beta(2, 5, n_ref),      # claim_frequency - skewed low
        rng.beta(2, 5, n_ref),      # gps_accuracy    - moderate accuracy
        rng.beta(2, 5, n_ref),      # payout_ratio    - moderate payouts
        rng.beta(2, 5, n_ref),      # trust_inv       - mostly trustworthy
        rng.beta(2, 5, n_ref),      # time_feat       - established accounts
        rng.binomial(1, 0.02, n_ref).astype(float),  # source_flag - rare mock
        rng.beta(3, 3, n_ref),      # severity        - moderate
    ])

    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
    )
    model.fit(ref)

    # decision_function returns negative for anomalies; map to [0, 1]
    raw_score: float = model.decision_function(feature_vector)[0]
    # Typical range is roughly [-0.5, 0.5]; clip and invert
    fraud_prob = float(np.clip(0.5 - raw_score, 0.0, 1.0))
    return round(fraud_prob, 4)


def detect_fraud(
    claim: Claim,
    user: UserProfile,
    claim_history: list[Claim] | None = None,
) -> tuple[float, FraudFlag, list[str]]:
    """Run Isolation Forest anomaly detection and return (score, flag, reasons)."""
    features = _build_feature_vector(claim, user, claim_history)
    score = _isolation_forest_score(features)

    reasons: list[str] = []
    if score >= FRAUD_THRESHOLD:
        flag = FraudFlag.FLAGGED
        reasons.append(f"Anomaly score {score:.3f} exceeds threshold {FRAUD_THRESHOLD}")
    elif score >= FRAUD_THRESHOLD * 0.7:
        flag = FraudFlag.SUSPICIOUS
        reasons.append(f"Anomaly score {score:.3f} is in suspicious range")
    else:
        flag = FraudFlag.CLEAN

    return score, flag, reasons


# ── GPS spoofing detection ───────────────────────────────────────────────────

def detect_gps_spoofing(
    claim: Claim,
    trajectory: list[GeoLocation] | None = None,
) -> tuple[bool, list[str]]:
    """Detect GPS spoofing via mock-location flag, suspiciously precise
    accuracy, and trajectory velocity analysis.

    Returns (is_spoofed, reasons).
    """
    reasons: list[str] = []
    is_spoofed = False

    # 1. Mock location check
    if claim.location.source == "mock":
        reasons.append("GPS source reported as 'mock'")
        is_spoofed = True

    # 2. Suspiciously precise accuracy
    accuracy = claim.location.accuracy_meters
    if accuracy is not None and accuracy < MIN_GPS_ACCURACY_M:
        reasons.append(
            f"GPS accuracy ({accuracy:.1f}m) suspiciously precise "
            f"(< {MIN_GPS_ACCURACY_M}m)"
        )
        is_spoofed = True

    # 3. Trajectory / velocity analysis
    if trajectory and len(trajectory) >= 2:
        for i in range(1, len(trajectory)):
            prev, curr = trajectory[i - 1], trajectory[i]
            if prev.timestamp and curr.timestamp:
                dist_km = _haversine_km(prev, curr)
                prev_ts = prev.timestamp.replace(tzinfo=timezone.utc) if prev.timestamp.tzinfo is None else prev.timestamp
                curr_ts = curr.timestamp.replace(tzinfo=timezone.utc) if curr.timestamp.tzinfo is None else curr.timestamp
                dt_hours = max(
                    (curr_ts - prev_ts).total_seconds() / 3600,
                    1e-6,
                )
                velocity_kph = dist_km / dt_hours

                if velocity_kph > MAX_VELOCITY_KPH:
                    reasons.append(
                        f"Impossible velocity {velocity_kph:.0f} km/h between "
                        f"trajectory points {i - 1}→{i}"
                    )
                    is_spoofed = True

        # 4. Check for perfectly identical consecutive coordinates (teleportation)
        unique_coords = {
            (round(p.latitude, 6), round(p.longitude, 6)) for p in trajectory
        }
        if len(unique_coords) == 1 and len(trajectory) > 3:
            reasons.append("All trajectory points have identical coordinates")
            is_spoofed = True

    return is_spoofed, reasons


# ── Fraud ring detection ────────────────────────────────────────────────────

def detect_fraud_ring(
    claim: Claim,
    user: UserProfile,
    recent_claims: list[dict[str, Any]] | None = None,
) -> tuple[bool, float, list[str]]:
    """Detect coordinated fraud rings via temporal clustering, device
    fingerprinting, and behavioral similarity.

    ``recent_claims`` is a list of dicts with keys:
        user_id, claim_id, timestamp (datetime), location (GeoLocation),
        device_id (str|None), estimated_loss (float)

    Returns (is_ring_member, ring_score, reasons).
    """
    if not recent_claims:
        return False, 0.0, []

    reasons: list[str] = []
    ring_indicators: list[float] = []

    claim_ts = claim.trigger_timestamp.replace(tzinfo=timezone.utc) if claim.trigger_timestamp.tzinfo is None else claim.trigger_timestamp

    # ── 1. Temporal clustering ───────────────────────────────────────────
    window = timedelta(minutes=TEMPORAL_CLUSTER_WINDOW_MIN)
    temporally_close = [
        rc for rc in recent_claims
        if rc["user_id"] != user.user_id
        and abs((rc["timestamp"].replace(tzinfo=timezone.utc) if rc["timestamp"].tzinfo is None else rc["timestamp"]) - claim_ts) <= window
    ]

    if len(temporally_close) >= 3:
        reasons.append(
            f"{len(temporally_close)} other claims within "
            f"{TEMPORAL_CLUSTER_WINDOW_MIN}-min window"
        )
        ring_indicators.append(min(len(temporally_close) / 5, 1.0))

    # ── 2. Device fingerprinting ─────────────────────────────────────────
    claim_device = getattr(claim, "device_id", None)
    if claim_device:
        shared_device = [
            rc for rc in recent_claims
            if rc.get("device_id") == claim_device
            and rc["user_id"] != user.user_id
        ]
        if shared_device:
            reasons.append(
                f"Device ID shared with {len(shared_device)} other user(s)"
            )
            ring_indicators.append(1.0)

    # ── 3. Behavioral similarity (loss amount clustering) ────────────────
    if temporally_close:
        losses = [rc["estimated_loss"] for rc in temporally_close]
        mean_loss = np.mean(losses)
        if mean_loss > 0:
            deviation = abs(claim.estimated_loss - mean_loss) / mean_loss
            if deviation < 0.15:
                reasons.append(
                    f"Claim loss (₹{claim.estimated_loss:.0f}) suspiciously "
                    f"similar to cluster mean (₹{mean_loss:.0f})"
                )
                ring_indicators.append(1.0 - deviation)

    # ── 4. Spatial clustering ────────────────────────────────────────────
    if temporally_close:
        distances = []
        for rc in temporally_close:
            rc_loc = rc["location"]
            if isinstance(rc_loc, dict):
                rc_loc = GeoLocation(**rc_loc)
            distances.append(_haversine_km(claim.location, rc_loc))
        avg_dist = np.mean(distances)
        if avg_dist < 0.5:  # within 500m
            reasons.append(
                f"Spatially clustered: avg {avg_dist:.2f} km from "
                f"{len(temporally_close)} concurrent claims"
            )
            ring_indicators.append(1.0 - min(avg_dist / 0.5, 1.0))

    ring_score = float(np.mean(ring_indicators)) if ring_indicators else 0.0
    is_ring = ring_score >= 0.5

    return is_ring, round(ring_score, 4), reasons


# ── LangGraph node ──────────────────────────────────────────────────────────

async def fraud_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fraud_validator.

    Runs anomaly detection, GPS spoofing checks, and fraud ring analysis.
    Updates ``state["fraud_score"]`` and may set decision to ``"fraud_detected"``
    which the orchestrator routes to rejection.
    """
    logger.info("Fraud agent: starting fraud detection")

    try:
        claim: Claim | None = state.get("claim")
        user: UserProfile | None = state.get("user")

        if claim is None or user is None:
            logger.error("Fraud agent: missing claim or user in state")
            return {
                **state,
                "reasoning": state.get("reasoning", []) + [
                    "Fraud agent: missing claim or user data"
                ],
            }

        reasoning = state.get("reasoning", []).copy()

        # ── Isolation Forest ─────────────────────────────────────────────
        anomaly_score, fraud_flag, anomaly_reasons = detect_fraud(claim, user)
        reasoning.extend(anomaly_reasons)
        logger.info(f"Fraud agent: anomaly_score={anomaly_score:.3f} flag={fraud_flag.value}")

        # ── GPS spoofing ─────────────────────────────────────────────────
        trajectory = state.get("trajectory")  # optional list[GeoLocation]
        is_spoofed, spoof_reasons = detect_gps_spoofing(claim, trajectory)
        reasoning.extend(spoof_reasons)

        if is_spoofed:
            logger.warning("Fraud agent: GPS spoofing indicators detected")
            anomaly_score = min(anomaly_score + 0.3, 1.0)

        # ── Fraud ring ───────────────────────────────────────────────────
        recent_claims = state.get("recent_claims")  # optional list[dict]
        is_ring, ring_score, ring_reasons = detect_fraud_ring(
            claim, user, recent_claims
        )
        reasoning.extend(ring_reasons)

        if is_ring:
            logger.warning(f"Fraud agent: fraud ring indicators (score={ring_score:.3f})")
            anomaly_score = min(anomaly_score + ring_score * 0.3, 1.0)

        # ── Composite decision ───────────────────────────────────────────
        final_score = round(anomaly_score, 4)
        decision = state.get("decision", "continue")

        if final_score >= FRAUD_THRESHOLD:
            decision = "fraud_detected"
            claim.status = ClaimStatus.FLAGGED
            claim.fraud_score = final_score
            reasoning.append(
                f"FRAUD DETECTED: composite score {final_score:.3f} >= {FRAUD_THRESHOLD}"
            )
            logger.warning(f"Fraud agent: claim {claim.claim_id} flagged (score={final_score})")
        else:
            claim.fraud_score = final_score
            reasoning.append(
                f"Fraud check passed: score {final_score:.3f} < {FRAUD_THRESHOLD}"
            )

        return {
            **state,
            "claim": claim,
            "fraud_score": final_score,
            "decision": decision,
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.exception("Fraud agent failed")
        return {
            **state,
            "error": f"Fraud agent error: {exc}",
            "reasoning": state.get("reasoning", []) + [f"Fraud agent error: {exc}"],
        }
