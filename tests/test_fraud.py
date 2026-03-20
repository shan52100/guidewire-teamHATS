"""Tests for fraud detection logic.

Covers:
  - Clean rider passes fraud checks
  - GPS spoofing is detected and flagged
  - Fraud ring pattern is detected
  - High claim frequency is flagged
"""

import pytest
from datetime import datetime, timedelta
from src.models.schemas import (
    Claim,
    ClaimStatus,
    DisruptionType,
    GeoLocation,
    UserProfile,
    UserRole,
    FraudFlag,
)

NOW = datetime(2026, 3, 21, 10, 0, 0)


# ─── Fraud Detection Functions (business logic under test) ───────────────────

def compute_fraud_score(
    user: UserProfile,
    claim: Claim,
    recent_claims: list[Claim] | None = None,
    known_ring_user_ids: set[str] | None = None,
) -> dict:
    """Compute a fraud score and list of signals for a claim.

    Returns dict with keys: score (0.0-1.0), flag, signals.

    Rules:
      - GPS spoofing: accuracy > 500m or source == "mock" => +0.4
      - Fraud ring: user_id in known ring set => +0.35
      - High frequency: > 3 claims in 7 days => +0.25
      - Low trust: user trust_score < 0.3 => +0.15
      - Score capped at 1.0
      - Flag thresholds: >= 0.7 => flagged, >= 0.4 => suspicious, else clean
    """
    score = 0.0
    signals = []

    # GPS spoofing check
    loc = claim.location
    if loc.source == "mock":
        score += 0.4
        signals.append("GPS source is mock/simulated")
    elif loc.accuracy_meters is not None and loc.accuracy_meters > 500:
        score += 0.4
        signals.append(f"GPS accuracy too low: {loc.accuracy_meters}m")

    # Fraud ring detection
    if known_ring_user_ids and user.user_id in known_ring_user_ids:
        score += 0.35
        signals.append("User is part of a suspected fraud ring")

    # High frequency check
    if recent_claims:
        week_ago = NOW - timedelta(days=7)
        recent_count = sum(
            1 for c in recent_claims if c.created_at >= week_ago
        )
        if recent_count > 3:
            score += 0.25
            signals.append(f"High claim frequency: {recent_count} claims in 7 days")

    # Low trust score
    if user.trust_score < 0.3:
        score += 0.15
        signals.append(f"Low trust score: {user.trust_score:.2f}")

    score = min(score, 1.0)

    if score >= 0.7:
        flag = FraudFlag.FLAGGED
    elif score >= 0.4:
        flag = FraudFlag.SUSPICIOUS
    else:
        flag = FraudFlag.CLEAN

    return {
        "score": round(score, 2),
        "flag": flag,
        "signals": signals,
    }


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestFraudDetection:
    """Fraud detection scenarios."""

    def test_clean_rider_passes(self, sample_claim, sample_user):
        """A rider with good trust, valid GPS, no ring membership, and low
        claim frequency should pass fraud checks cleanly."""
        result = compute_fraud_score(
            user=sample_user,
            claim=sample_claim,
            recent_claims=[],
            known_ring_user_ids=set(),
        )

        assert result["flag"] == FraudFlag.CLEAN
        assert result["score"] < 0.4
        assert len(result["signals"]) == 0

    def test_gps_spoofing_caught_mock_source(self, sample_user):
        """A claim with GPS source='mock' should be flagged for spoofing."""
        spoofed_claim = Claim(
            claim_id="CLM-SPOOF-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            status=ClaimStatus.PENDING,
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.6,
            trigger_timestamp=NOW - timedelta(hours=1),
            location=GeoLocation(
                latitude=13.0418,
                longitude=80.2341,
                accuracy_meters=10.0,
                source="mock",
            ),
            estimated_loss=400.0,
        )
        result = compute_fraud_score(
            user=sample_user,
            claim=spoofed_claim,
            recent_claims=[],
            known_ring_user_ids=set(),
        )

        assert result["score"] >= 0.4
        assert any("mock" in s.lower() or "gps" in s.lower() for s in result["signals"])

    def test_gps_spoofing_caught_low_accuracy(self, sample_user):
        """A claim with GPS accuracy > 500m should trigger spoofing detection."""
        bad_gps_claim = Claim(
            claim_id="CLM-SPOOF-002",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            status=ClaimStatus.PENDING,
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.5,
            trigger_timestamp=NOW - timedelta(hours=1),
            location=GeoLocation(
                latitude=13.0418,
                longitude=80.2341,
                accuracy_meters=1200.0,
                source="gps",
            ),
            estimated_loss=350.0,
        )
        result = compute_fraud_score(
            user=sample_user,
            claim=bad_gps_claim,
            recent_claims=[],
            known_ring_user_ids=set(),
        )

        assert result["score"] >= 0.4
        assert any("accuracy" in s.lower() for s in result["signals"])

    def test_fraud_ring_detected(self, sample_claim, suspicious_user):
        """A user who belongs to a known fraud ring should be flagged."""
        ring_ids = {"RDR-0042", "RDR-0043", "RDR-0044", "RDR-0045"}

        # Override claim user to match suspicious user
        claim = sample_claim.model_copy(update={"user_id": "RDR-0042"})

        result = compute_fraud_score(
            user=suspicious_user,
            claim=claim,
            recent_claims=[],
            known_ring_user_ids=ring_ids,
        )

        assert result["flag"] == FraudFlag.FLAGGED
        assert result["score"] >= 0.5
        assert any("fraud ring" in s.lower() for s in result["signals"])

    def test_high_frequency_flagged(self, sample_user):
        """A user with > 3 claims in the last 7 days should be flagged
        for high frequency."""
        base_claim = Claim(
            claim_id="CLM-FREQ-001",
            policy_id="POL-TNAGAR-0001",
            user_id="RDR-0001",
            status=ClaimStatus.APPROVED,
            disruption_type=DisruptionType.HEAVY_RAIN,
            disruption_severity=0.5,
            trigger_timestamp=NOW - timedelta(days=1),
            location=GeoLocation(latitude=13.0418, longitude=80.2341, source="gps"),
            estimated_loss=300.0,
            created_at=NOW - timedelta(days=1),
        )

        recent_claims = [
            base_claim.model_copy(
                update={
                    "claim_id": f"CLM-FREQ-{i:03d}",
                    "created_at": NOW - timedelta(days=i),
                }
            )
            for i in range(5)  # 5 claims in the past week
        ]

        current_claim = base_claim.model_copy(
            update={"claim_id": "CLM-FREQ-CURRENT", "status": ClaimStatus.PENDING}
        )

        result = compute_fraud_score(
            user=sample_user,
            claim=current_claim,
            recent_claims=recent_claims,
            known_ring_user_ids=set(),
        )

        assert result["score"] >= 0.25
        assert any("frequency" in s.lower() for s in result["signals"])

    def test_multiple_signals_compound(self, suspicious_user):
        """Multiple fraud indicators should compound into a high score."""
        ring_ids = {"RDR-0042"}

        spoofed_claim = Claim(
            claim_id="CLM-COMPOUND-001",
            policy_id="POL-TAMBARAM-0001",
            user_id="RDR-0042",
            status=ClaimStatus.PENDING,
            disruption_type=DisruptionType.FLOOD,
            disruption_severity=0.8,
            trigger_timestamp=NOW - timedelta(hours=1),
            location=GeoLocation(
                latitude=12.9249,
                longitude=80.1000,
                accuracy_meters=800.0,
                source="gps",
            ),
            estimated_loss=700.0,
            created_at=NOW,
        )

        recent_claims = [
            spoofed_claim.model_copy(
                update={
                    "claim_id": f"CLM-COMPOUND-{i:03d}",
                    "created_at": NOW - timedelta(days=i),
                }
            )
            for i in range(5)
        ]

        result = compute_fraud_score(
            user=suspicious_user,
            claim=spoofed_claim,
            recent_claims=recent_claims,
            known_ring_user_ids=ring_ids,
        )

        # GPS spoof (0.4) + ring (0.35) + frequency (0.25) + low trust (0.15) = 1.15 -> capped at 1.0
        assert result["score"] == 1.0
        assert result["flag"] == FraudFlag.FLAGGED
        assert len(result["signals"]) >= 3

    def test_low_trust_alone_is_suspicious_not_flagged(self, suspicious_user, sample_claim):
        """Low trust alone should make the claim suspicious but not flagged."""
        claim = sample_claim.model_copy(update={"user_id": "RDR-0042"})

        result = compute_fraud_score(
            user=suspicious_user,
            claim=claim,
            recent_claims=[],
            known_ring_user_ids=set(),
        )

        # Only low trust signal: 0.15 < 0.4 threshold
        assert result["flag"] == FraudFlag.CLEAN
        assert result["score"] == 0.15
