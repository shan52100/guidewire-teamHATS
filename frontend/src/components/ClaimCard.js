import React from "react";
import StatusBadge from "./StatusBadge";
import { DISRUPTION_TYPES } from "../utils/constants";

/**
 * ClaimCard - displays claim details in a card layout.
 *
 * Props:
 *   claim - object with: claim_id, rider_name, zone_name, disruption_type,
 *           severity, status, payout, created_at
 */
export default function ClaimCard({ claim }) {
  const disruption = DISRUPTION_TYPES[claim.disruption_type] || {
    label: claim.disruption_type,
    icon: "?",
  };

  const severityPercent = Math.round((claim.severity || 0) * 100);
  const severityClass =
    severityPercent >= 75
      ? "severity--high"
      : severityPercent >= 40
      ? "severity--medium"
      : "severity--low";

  return (
    <div className="claim-card">
      <div className="claim-card__header">
        <span className="claim-card__id">{claim.claim_id}</span>
        <StatusBadge status={claim.status} />
      </div>

      <div className="claim-card__body">
        <div className="claim-card__row">
          <span className="claim-card__label">Rider</span>
          <span className="claim-card__value">{claim.rider_name}</span>
        </div>
        <div className="claim-card__row">
          <span className="claim-card__label">Zone</span>
          <span className="claim-card__value">{claim.zone_name}</span>
        </div>
        <div className="claim-card__row">
          <span className="claim-card__label">Type</span>
          <span className="claim-card__value">
            {disruption.icon} {disruption.label}
          </span>
        </div>
        <div className="claim-card__row">
          <span className="claim-card__label">Severity</span>
          <span className={`claim-card__value ${severityClass}`}>
            {severityPercent}%
          </span>
        </div>
        <div className="claim-card__row">
          <span className="claim-card__label">Payout</span>
          <span className="claim-card__value claim-card__payout">
            {claim.payout != null ? `Rs. ${claim.payout.toFixed(0)}` : "--"}
          </span>
        </div>
      </div>

      <div className="claim-card__footer">
        <span className="claim-card__time">
          {new Date(claim.created_at).toLocaleString("en-IN", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
