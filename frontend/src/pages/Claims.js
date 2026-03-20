import React, { useState, useMemo } from "react";
import StatusBadge from "../components/StatusBadge";
import useApi from "../hooks/useApi";
import { DISRUPTION_TYPES } from "../utils/constants";

const FALLBACK_CLAIMS = [
  {
    claim_id: "CLM-20260321-001",
    rider_name: "Rajesh K.",
    zone_name: "T. Nagar",
    disruption_type: "heavy_rain",
    severity: 0.72,
    status: "approved",
    payout: 480,
    created_at: "2026-03-21T09:15:00",
  },
  {
    claim_id: "CLM-20260321-002",
    rider_name: "Priya M.",
    zone_name: "Velachery",
    disruption_type: "flood",
    severity: 0.91,
    status: "paid",
    payout: 850,
    created_at: "2026-03-21T08:42:00",
  },
  {
    claim_id: "CLM-20260321-003",
    rider_name: "Arun S.",
    zone_name: "Anna Nagar",
    disruption_type: "platform_outage",
    severity: 0.45,
    status: "pending",
    payout: null,
    created_at: "2026-03-21T10:30:00",
  },
  {
    claim_id: "CLM-20260321-004",
    rider_name: "Deepa V.",
    zone_name: "Tambaram",
    disruption_type: "flood",
    severity: 0.88,
    status: "flagged",
    payout: null,
    created_at: "2026-03-21T07:55:00",
  },
  {
    claim_id: "CLM-20260321-005",
    rider_name: "Karthik R.",
    zone_name: "Adyar",
    disruption_type: "heavy_rain",
    severity: 0.53,
    status: "approved",
    payout: 320,
    created_at: "2026-03-21T11:10:00",
  },
  {
    claim_id: "CLM-20260321-006",
    rider_name: "Meena L.",
    zone_name: "T. Nagar",
    disruption_type: "pollution",
    severity: 0.65,
    status: "rejected",
    payout: 0,
    created_at: "2026-03-21T06:20:00",
  },
  {
    claim_id: "CLM-20260321-007",
    rider_name: "Suresh B.",
    zone_name: "Velachery",
    disruption_type: "multi_trigger",
    severity: 0.95,
    status: "approved",
    payout: 1100,
    created_at: "2026-03-21T09:48:00",
  },
  {
    claim_id: "CLM-20260321-008",
    rider_name: "Lakshmi N.",
    zone_name: "Tambaram",
    disruption_type: "zone_closure",
    severity: 0.78,
    status: "pending",
    payout: null,
    created_at: "2026-03-21T12:05:00",
  },
];

const STATUS_OPTIONS = [
  "all",
  "pending",
  "validating",
  "approved",
  "rejected",
  "paid",
  "flagged",
];

export default function Claims() {
  const { data: apiClaims } = useApi("/claims", { initialData: null });
  const [statusFilter, setStatusFilter] = useState("all");

  const claims = apiClaims || FALLBACK_CLAIMS;

  const filteredClaims = useMemo(() => {
    if (statusFilter === "all") return claims;
    return claims.filter((c) => c.status === statusFilter);
  }, [claims, statusFilter]);

  return (
    <div className="page">
      <div className="page__header">
        <h1 className="page__title">Claims</h1>
        <div className="page__actions">
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "all"
                  ? "All Statuses"
                  : opt.charAt(0).toUpperCase() + opt.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Rider</th>
              <th>Zone</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Payout</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {filteredClaims.map((claim) => {
              const disruption = DISRUPTION_TYPES[claim.disruption_type] || {
                label: claim.disruption_type,
                icon: "?",
              };
              const severityPct = Math.round((claim.severity || 0) * 100);
              return (
                <tr key={claim.claim_id}>
                  <td className="cell--mono">{claim.claim_id}</td>
                  <td>{claim.rider_name}</td>
                  <td>{claim.zone_name}</td>
                  <td>
                    {disruption.icon} {disruption.label}
                  </td>
                  <td>
                    <div className="severity-bar-container">
                      <div
                        className={`severity-bar ${
                          severityPct >= 75
                            ? "severity-bar--high"
                            : severityPct >= 40
                            ? "severity-bar--medium"
                            : "severity-bar--low"
                        }`}
                        style={{ width: `${severityPct}%` }}
                      />
                      <span className="severity-label">{severityPct}%</span>
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={claim.status} size="sm" />
                  </td>
                  <td className="cell--mono">
                    {claim.payout != null ? `Rs. ${claim.payout}` : "--"}
                  </td>
                  <td className="cell--muted">
                    {new Date(claim.created_at).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filteredClaims.length === 0 && (
          <div className="empty-state">No claims match the selected filter.</div>
        )}
      </div>
    </div>
  );
}
