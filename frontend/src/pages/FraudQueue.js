import React, { useState, useCallback } from "react";
import StatusBadge from "../components/StatusBadge";
import useApi from "../hooks/useApi";

const FALLBACK_FLAGGED = [
  {
    claim_id: "CLM-20260321-004",
    rider_name: "Deepa V.",
    rider_id: "RDR-0042",
    zone_name: "Tambaram",
    disruption_type: "flood",
    fraud_score: 0.82,
    signals: ["GPS location mismatch", "Claim filed outside active delivery window"],
    status: "flagged",
    total_claims: 12,
    trust_score: 0.35,
    created_at: "2026-03-21T07:55:00",
  },
  {
    claim_id: "CLM-20260320-019",
    rider_name: "Vikram T.",
    rider_id: "RDR-0118",
    zone_name: "Velachery",
    disruption_type: "heavy_rain",
    fraud_score: 0.74,
    signals: ["Duplicate claim pattern detected", "3 claims in 24h from same zone"],
    status: "flagged",
    total_claims: 8,
    trust_score: 0.42,
    created_at: "2026-03-20T16:30:00",
  },
  {
    claim_id: "CLM-20260320-023",
    rider_name: "Ganesh P.",
    rider_id: "RDR-0067",
    zone_name: "T. Nagar",
    disruption_type: "platform_outage",
    fraud_score: 0.91,
    signals: [
      "Part of suspected fraud ring (4 linked riders)",
      "GPS spoofing indicators",
      "Claims submitted within 2 min of each other",
    ],
    status: "flagged",
    total_claims: 15,
    trust_score: 0.18,
    created_at: "2026-03-20T14:12:00",
  },
  {
    claim_id: "CLM-20260319-031",
    rider_name: "Anitha R.",
    rider_id: "RDR-0205",
    zone_name: "Adyar",
    disruption_type: "pollution",
    fraud_score: 0.69,
    signals: ["High claim frequency: 5 claims this week"],
    status: "flagged",
    total_claims: 5,
    trust_score: 0.51,
    created_at: "2026-03-19T11:45:00",
  },
];

export default function FraudQueue() {
  const { data: apiFlagged } = useApi("/fraud/queue", { initialData: null });
  const { execute: updateClaim } = useApi("/fraud/review", {
    manual: true,
    method: "post",
  });

  const [localOverrides, setLocalOverrides] = useState({});

  const flaggedClaims = apiFlagged || FALLBACK_FLAGGED;

  const handleAction = useCallback(
    async (claimId, action) => {
      try {
        await updateClaim({ claim_id: claimId, action });
      } catch {
        // API not available, apply locally for demo
      }
      setLocalOverrides((prev) => ({
        ...prev,
        [claimId]: action === "approve" ? "approved" : "rejected",
      }));
    },
    [updateClaim]
  );

  const getFraudScoreClass = (score) => {
    if (score >= 0.85) return "fraud-score--critical";
    if (score >= 0.7) return "fraud-score--high";
    return "fraud-score--medium";
  };

  return (
    <div className="page">
      <div className="page__header">
        <h1 className="page__title">Fraud Review Queue</h1>
        <p className="page__subtitle">
          {flaggedClaims.length} flagged claims require manual review
        </p>
      </div>

      <div className="fraud-queue">
        {flaggedClaims.map((claim) => {
          const overriddenStatus = localOverrides[claim.claim_id];
          const displayStatus = overriddenStatus || claim.status;
          const isResolved = !!overriddenStatus;

          return (
            <div
              key={claim.claim_id}
              className={`fraud-card ${isResolved ? "fraud-card--resolved" : ""}`}
            >
              <div className="fraud-card__header">
                <div className="fraud-card__id-row">
                  <span className="fraud-card__id">{claim.claim_id}</span>
                  <StatusBadge status={displayStatus} />
                </div>
                <div
                  className={`fraud-card__score ${getFraudScoreClass(
                    claim.fraud_score
                  )}`}
                >
                  Fraud Score: {Math.round(claim.fraud_score * 100)}%
                </div>
              </div>

              <div className="fraud-card__body">
                <div className="fraud-card__rider">
                  <div className="fraud-card__row">
                    <span className="fraud-card__label">Rider</span>
                    <span>
                      {claim.rider_name} ({claim.rider_id})
                    </span>
                  </div>
                  <div className="fraud-card__row">
                    <span className="fraud-card__label">Zone</span>
                    <span>{claim.zone_name}</span>
                  </div>
                  <div className="fraud-card__row">
                    <span className="fraud-card__label">Total Claims</span>
                    <span>{claim.total_claims}</span>
                  </div>
                  <div className="fraud-card__row">
                    <span className="fraud-card__label">Trust Score</span>
                    <span
                      className={
                        claim.trust_score < 0.3
                          ? "text-danger"
                          : claim.trust_score < 0.5
                          ? "text-warning"
                          : ""
                      }
                    >
                      {Math.round(claim.trust_score * 100)}%
                    </span>
                  </div>
                </div>

                <div className="fraud-card__signals">
                  <span className="fraud-card__label">Fraud Signals</span>
                  <ul className="fraud-card__signal-list">
                    {claim.signals.map((signal, idx) => (
                      <li key={idx} className="fraud-card__signal-item">
                        {signal}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {!isResolved && (
                <div className="fraud-card__actions">
                  <button
                    className="btn btn--approve"
                    onClick={() => handleAction(claim.claim_id, "approve")}
                  >
                    Approve Claim
                  </button>
                  <button
                    className="btn btn--reject"
                    onClick={() => handleAction(claim.claim_id, "reject")}
                  >
                    Reject Claim
                  </button>
                </div>
              )}
            </div>
          );
        })}

        {flaggedClaims.length === 0 && (
          <div className="empty-state">
            No flagged claims in queue. All clear!
          </div>
        )}
      </div>
    </div>
  );
}
