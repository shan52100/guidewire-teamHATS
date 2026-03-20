import React from "react";
import { CHENNAI_ZONES, ZONE_RISK_COLORS } from "../utils/constants";

export default function ZoneMap() {
  return (
    <div className="page">
      <div className="page__header">
        <h1 className="page__title">Zone Overview</h1>
        <p className="page__subtitle">
          Chennai delivery zones with real-time risk assessment and rider
          activity
        </p>
      </div>

      <div className="zone-legend">
        {Object.entries(ZONE_RISK_COLORS).map(([level, color]) => (
          <span key={level} className="zone-legend__item">
            <span
              className="zone-legend__dot"
              style={{ backgroundColor: color }}
            />
            {level.charAt(0).toUpperCase() + level.slice(1)} Risk
          </span>
        ))}
      </div>

      <div className="zone-grid">
        {CHENNAI_ZONES.map((zone) => {
          const riskColor = ZONE_RISK_COLORS[zone.risk_level] || "#6b7280";

          return (
            <div
              key={zone.zone_id}
              className="zone-card"
              style={{ borderTopColor: riskColor }}
            >
              <div className="zone-card__header">
                <h3 className="zone-card__name">{zone.name}</h3>
                <span
                  className="zone-card__risk"
                  style={{
                    backgroundColor: `${riskColor}18`,
                    color: riskColor,
                  }}
                >
                  {zone.risk_level.toUpperCase()}
                </span>
              </div>

              <div className="zone-card__stats">
                <div className="zone-card__stat">
                  <span className="zone-card__stat-value">
                    {zone.avg_orders}
                  </span>
                  <span className="zone-card__stat-label">Avg Orders/hr</span>
                </div>
                <div className="zone-card__stat">
                  <span className="zone-card__stat-value">
                    Rs. {zone.premium}
                  </span>
                  <span className="zone-card__stat-label">Weekly Premium</span>
                </div>
                <div className="zone-card__stat">
                  <span className="zone-card__stat-value">
                    {zone.active_riders}
                  </span>
                  <span className="zone-card__stat-label">Active Riders</span>
                </div>
              </div>

              <div className="zone-card__coords">
                {zone.lat.toFixed(4)}N, {zone.lng.toFixed(4)}E
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
