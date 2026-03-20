import React from "react";

/**
 * MetricCard - reusable card showing a single KPI metric.
 *
 * Props:
 *   title    - metric label (e.g. "Total Claims Today")
 *   value    - primary display value
 *   change   - change indicator (e.g. "+12%" or "-3%")
 *   icon     - emoji or icon string
 */
export default function MetricCard({ title, value, change, icon }) {
  const isPositive = change && change.startsWith("+");
  const isNegative = change && change.startsWith("-");

  return (
    <div className="metric-card">
      <div className="metric-card__header">
        <span className="metric-card__icon">{icon}</span>
        <span className="metric-card__title">{title}</span>
      </div>
      <div className="metric-card__value">{value}</div>
      {change && (
        <div
          className={`metric-card__change ${
            isPositive
              ? "metric-card__change--positive"
              : isNegative
              ? "metric-card__change--negative"
              : ""
          }`}
        >
          {change}
        </div>
      )}
    </div>
  );
}
