import React from "react";
import { STATUS_COLORS } from "../utils/constants";

/**
 * StatusBadge - displays a color-coded status label.
 *
 * Props:
 *   status  - one of: approved, paid, pending, validating, rejected, flagged, blocked
 *   size    - "sm" | "md" (default "md")
 */
export default function StatusBadge({ status, size = "md" }) {
  const color = STATUS_COLORS[status] || "#6b7280";
  const label = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span
      className={`status-badge status-badge--${size}`}
      style={{
        backgroundColor: `${color}18`,
        color: color,
        borderColor: `${color}40`,
      }}
    >
      <span className="status-badge__dot" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
