"""Risk assessment agent.

Uses a Random Forest classifier for risk scoring and a rule-based engine for
dynamic premium calculation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from loguru import logger
from sklearn.ensemble import RandomForestClassifier

from src.config.settings import settings
from src.models.schemas import (
    Claim,
    InsurancePolicy,
    PremiumCalculation,
    RiskLevel,
    UserProfile,
    Zone,
)


# ── Constants ────────────────────────────────────────────────────────────────

# Zone-based base premiums (INR per week)
ZONE_PREMIUMS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 30.0,       # Safe zones
    RiskLevel.MEDIUM: 50.0,    # Moderate zones
    RiskLevel.HIGH: 70.0,      # Flood-prone zones
    RiskLevel.CRITICAL: 70.0,  # Same as HIGH; additional surcharge via multiplier
}

# Zone risk factor multipliers
ZONE_FACTORS: dict[RiskLevel, float] = {
    RiskLevel.LOW: 0.8,
    RiskLevel.MEDIUM: 1.0,
    RiskLevel.HIGH: 1.4,
    RiskLevel.CRITICAL: 1.8,
}

# Seasonal multipliers (month → factor)
SEASONAL_FACTORS: dict[int, float] = {
    1: 0.9,   # Jan - dry
    2: 0.9,   # Feb - dry
    3: 1.0,   # Mar - pre-monsoon
    4: 1.1,   # Apr - pre-monsoon
    5: 1.2,   # May - heat
    6: 1.5,   # Jun - monsoon onset
    7: 1.8,   # Jul - peak monsoon
    8: 1.7,   # Aug - monsoon
    9: 1.4,   # Sep - retreating monsoon
    10: 1.1,  # Oct - post-monsoon
    11: 0.9,  # Nov - dry
    12: 0.9,  # Dec - dry
}

# Risk level thresholds for classifier output
RISK_THRESHOLDS: dict[str, float] = {
    "critical": 0.85,
    "high": 0.65,
    "medium": 0.35,
}

# Label encoding for the classifier
RISK_LABEL_MAP: dict[int, RiskLevel] = {
    0: RiskLevel.LOW,
    1: RiskLevel.MEDIUM,
    2: RiskLevel.HIGH,
    3: RiskLevel.CRITICAL,
}


# ── Feature engineering ──────────────────────────────────────────────────────

def _build_risk_features(
    user: UserProfile,
    zone: Zone | None,
    claim: Claim | None,
) -> np.ndarray:
    """Build feature vector for risk classification.

    Features (4-dim):
        0 - zone_risk_history   : numeric encoding of zone risk level (0-3)
        1 - user_claim_frequency: normalised claim count
        2 - seasonal_factor     : current month's seasonal multiplier (normalised)
        3 - registration_age    : account age in days (normalised to [0,1] over 365d)
    """
    # Zone risk history
    zone_risk_map = {
        RiskLevel.LOW: 0.0,
        RiskLevel.MEDIUM: 1.0,
        RiskLevel.HIGH: 2.0,
        RiskLevel.CRITICAL: 3.0,
    }
    zone_risk = zone_risk_map.get(
        zone.risk_level if zone else RiskLevel.MEDIUM, 1.0
    ) / 3.0

    # User claim frequency
    claim_freq = min(user.total_claims / max(settings.max_claims_per_week * 4, 1), 1.0)

    # Seasonal factor
    month = datetime.now(tz=timezone.utc).month
    seasonal = SEASONAL_FACTORS.get(month, 1.0) / 1.8  # normalised to ~[0,1]

    # Registration age
    reg_date = user.registration_date.replace(tzinfo=timezone.utc) if user.registration_date.tzinfo is None else user.registration_date
    age_days = (datetime.now(tz=timezone.utc) - reg_date).days
    age_norm = min(age_days / 365.0, 1.0)

    return np.array([[zone_risk, claim_freq, seasonal, age_norm]])


def _train_risk_classifier() -> RandomForestClassifier:
    """Train a Random Forest on synthetic historical data.

    In production, this would be loaded from a model registry.  Here we
    generate a representative training set to bootstrap the classifier.
    """
    rng = np.random.RandomState(42)
    n = 500

    # Synthetic features
    zone_risk = rng.choice([0.0, 1 / 3, 2 / 3, 1.0], n, p=[0.3, 0.35, 0.25, 0.1])
    claim_freq = rng.beta(2, 5, n)
    seasonal = rng.uniform(0.5, 1.0, n)
    age_norm = rng.beta(5, 2, n)

    X = np.column_stack([zone_risk, claim_freq, seasonal, age_norm])

    # Labels derived from a weighted combination
    score = 0.35 * zone_risk + 0.30 * claim_freq + 0.20 * seasonal + 0.15 * (1 - age_norm)
    y = np.zeros(n, dtype=int)
    y[score >= RISK_THRESHOLDS["medium"]] = 1
    y[score >= RISK_THRESHOLDS["high"]] = 2
    y[score >= RISK_THRESHOLDS["critical"]] = 3

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X, y)
    return clf


# Module-level cached classifier
_risk_clf: RandomForestClassifier | None = None


def _get_classifier() -> RandomForestClassifier:
    global _risk_clf
    if _risk_clf is None:
        _risk_clf = _train_risk_classifier()
    return _risk_clf


# ── Risk assessment ──────────────────────────────────────────────────────────

def assess_risk(
    user: UserProfile,
    zone: Zone | None = None,
    claim: Claim | None = None,
) -> tuple[RiskLevel, float, dict[str, Any]]:
    """Classify risk level using the Random Forest model.

    Returns (risk_level, risk_score, details_dict).
    """
    features = _build_risk_features(user, zone, claim)
    clf = _get_classifier()

    predicted_label: int = int(clf.predict(features)[0])
    probas: np.ndarray = clf.predict_proba(features)[0]

    risk_level = RISK_LABEL_MAP.get(predicted_label, RiskLevel.MEDIUM)

    # Weighted risk score from class probabilities
    weights = np.array([0.0, 0.33, 0.67, 1.0])
    risk_score = float(np.dot(probas, weights[: len(probas)]))
    risk_score = round(min(max(risk_score, 0.0), 1.0), 4)

    details: dict[str, Any] = {
        "predicted_class": predicted_label,
        "class_probabilities": {
            RISK_LABEL_MAP[i].value: round(float(p), 4)
            for i, p in enumerate(probas)
        },
        "features": {
            "zone_risk_history": round(float(features[0, 0]), 4),
            "user_claim_frequency": round(float(features[0, 1]), 4),
            "seasonal_factor": round(float(features[0, 2]), 4),
            "registration_age": round(float(features[0, 3]), 4),
        },
    }

    return risk_level, risk_score, details


# ── Dynamic premium calculation ─────────────────────────────────────────────

def calculate_premium(
    user: UserProfile,
    zone: Zone | None = None,
    risk_level: RiskLevel | None = None,
) -> PremiumCalculation:
    """Calculate the dynamic weekly premium.

    Formula:
        Premium = Base x Zone_Factor x Seasonal x (1 - History_Discount)

    Where Base is determined by zone risk level (Safe=₹30, Moderate=₹50,
    Flood-Prone=₹70).
    """
    effective_risk = risk_level or (zone.risk_level if zone else RiskLevel.MEDIUM)

    # Base premium from zone classification
    base = ZONE_PREMIUMS.get(effective_risk, 50.0)

    # Zone factor
    zone_factor = ZONE_FACTORS.get(effective_risk, 1.0)

    # Seasonal factor
    month = datetime.now(tz=timezone.utc).month
    seasonal = SEASONAL_FACTORS.get(month, 1.0)

    # History discount: loyal users with few claims get up to 20% off
    reg_date = user.registration_date.replace(tzinfo=timezone.utc) if user.registration_date.tzinfo is None else user.registration_date
    tenure_months = max(
        (datetime.now(tz=timezone.utc) - reg_date).days / 30, 0.0
    )
    claim_ratio = user.total_claims / max(tenure_months, 1.0)
    # Low claim ratio + long tenure → higher discount
    history_discount = min(0.20, max(0.0, 0.20 - claim_ratio * 0.05))

    # Final calculation
    final = base * zone_factor * seasonal * (1 - history_discount)
    final = round(final, 2)

    # Risk multiplier (for transparency in breakdown)
    risk_multiplier = round(zone_factor * seasonal * (1 - history_discount), 4)

    return PremiumCalculation(
        base_premium=base,
        risk_multiplier=risk_multiplier,
        zone_factor=zone_factor,
        history_discount=round(history_discount, 4),
        final_premium=final,
        breakdown={
            "base_inr": base,
            "zone_factor": zone_factor,
            "seasonal_factor": seasonal,
            "history_discount_pct": round(history_discount * 100, 2),
            "risk_level": effective_risk.value,
            "month": month,
        },
    )


# ── LangGraph node ──────────────────────────────────────────────────────────

async def risk_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: actuarial_engine.

    Assesses risk using the Random Forest classifier and computes the dynamic
    premium.  Populates ``state["risk_assessment"]`` and updates the claim's
    disruption_severity if the model suggests a different level.
    """
    logger.info("Risk agent: starting risk assessment")

    try:
        user: UserProfile | None = state.get("user")
        zone: Zone | None = state.get("zone")
        claim: Claim | None = state.get("claim")

        if user is None:
            logger.error("Risk agent: no user in state")
            return {
                **state,
                "reasoning": state.get("reasoning", []) + [
                    "Risk agent: no user profile available"
                ],
            }

        reasoning = state.get("reasoning", []).copy()

        # ── Risk classification ──────────────────────────────────────────
        risk_level, risk_score, details = assess_risk(user, zone, claim)
        logger.info(f"Risk agent: level={risk_level.value} score={risk_score:.3f}")
        reasoning.append(
            f"Risk assessment: {risk_level.value} (score {risk_score:.3f})"
        )

        # ── Premium calculation ──────────────────────────────────────────
        premium = calculate_premium(user, zone, risk_level)
        logger.info(
            f"Risk agent: premium ₹{premium.final_premium:.2f} "
            f"(base ₹{premium.base_premium:.2f})"
        )
        reasoning.append(
            f"Premium calculated: ₹{premium.final_premium:.2f}/week "
            f"(base ₹{premium.base_premium:.2f}, zone_factor={premium.zone_factor}, "
            f"discount={premium.history_discount:.1%})"
        )

        # ── Update risk assessment in state ──────────────────────────────
        risk_assessment: dict[str, Any] = {
            "risk_level": risk_level.value,
            "risk_score": risk_score,
            "premium": premium.model_dump(),
            "model_details": details,
        }

        return {
            **state,
            "risk_assessment": risk_assessment,
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.exception("Risk agent failed")
        return {
            **state,
            "error": f"Risk agent error: {exc}",
            "reasoning": state.get("reasoning", []) + [f"Risk agent error: {exc}"],
        }
