import React, { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import MetricCard from "../components/MetricCard";
import useApi from "../hooks/useApi";
import { ZONE_RISK_COLORS } from "../utils/constants";

// Realistic fallback data for demo / offline mode
const FALLBACK_CLAIMS_OVER_TIME = [
  { date: "Mar 15", claims: 18, payouts: 12400 },
  { date: "Mar 16", claims: 24, payouts: 16800 },
  { date: "Mar 17", claims: 31, payouts: 21500 },
  { date: "Mar 18", claims: 15, payouts: 10200 },
  { date: "Mar 19", claims: 42, payouts: 29800 },
  { date: "Mar 20", claims: 37, payouts: 25900 },
  { date: "Mar 21", claims: 28, payouts: 19600 },
];

const FALLBACK_ZONE_RISK = [
  { name: "Low Risk", value: 1, risk: "low" },
  { name: "Medium Risk", value: 2, risk: "medium" },
  { name: "High Risk", value: 2, risk: "high" },
];

export default function Dashboard() {
  const { data: stats } = useApi("/dashboard/stats", {
    initialData: null,
  });

  const [claimsData] = useState(FALLBACK_CLAIMS_OVER_TIME);
  const [zoneRiskData] = useState(FALLBACK_ZONE_RISK);

  const metrics = useMemo(
    () => ({
      totalClaimsToday: stats?.total_claims_today ?? 28,
      activePolicies: stats?.active_policies ?? 612,
      totalPayouts: stats?.total_payouts ?? "Rs. 1,94,600",
      fraudFlags: stats?.fraud_flags ?? 4,
    }),
    [stats]
  );

  return (
    <div className="page">
      <div className="page__header">
        <h1 className="page__title">Dashboard</h1>
        <p className="page__subtitle">
          Real-time overview of parametric insurance operations across Chennai
        </p>
      </div>

      <div className="metrics-grid">
        <MetricCard
          title="Claims Today"
          value={metrics.totalClaimsToday}
          change="+12%"
          icon="📋"
        />
        <MetricCard
          title="Active Policies"
          value={metrics.activePolicies}
          change="+3%"
          icon="🛡"
        />
        <MetricCard
          title="Total Payouts"
          value={metrics.totalPayouts}
          change="+8%"
          icon="💰"
        />
        <MetricCard
          title="Fraud Flags"
          value={metrics.fraudFlags}
          change="-2"
          icon="🚩"
        />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h2 className="chart-card__title">Claims Over Time</h2>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={claimsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                }}
              />
              <Bar
                dataKey="claims"
                fill="#6366f1"
                radius={[4, 4, 0, 0]}
                name="Claims"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h2 className="chart-card__title">Zone Risk Distribution</h2>
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={zoneRiskData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                dataKey="value"
                nameKey="name"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {zoneRiskData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={ZONE_RISK_COLORS[entry.risk] || "#6b7280"}
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
