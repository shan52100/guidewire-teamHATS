export const API_URL = "http://localhost:8000/api/v1";

export const STATUS_COLORS = {
  approved: "#10b981",
  paid: "#10b981",
  pending: "#f59e0b",
  validating: "#f59e0b",
  rejected: "#ef4444",
  flagged: "#f97316",
  blocked: "#dc2626",
};

export const ZONE_RISK_COLORS = {
  low: "#10b981",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
};

export const DISRUPTION_TYPES = {
  heavy_rain: { label: "Heavy Rain", icon: "🌧" },
  flood: { label: "Flood", icon: "🌊" },
  pollution: { label: "Pollution", icon: "🏭" },
  zone_closure: { label: "Zone Closure", icon: "🚧" },
  platform_outage: { label: "Platform Outage", icon: "⚡" },
  multi_trigger: { label: "Multi-Trigger", icon: "⚠" },
};

export const CHENNAI_ZONES = [
  {
    zone_id: "zone_tnagar",
    name: "T. Nagar",
    risk_level: "medium",
    avg_orders: 85,
    premium: 50,
    active_riders: 142,
    lat: 13.0418,
    lng: 80.2341,
  },
  {
    zone_id: "zone_velachery",
    name: "Velachery",
    risk_level: "high",
    avg_orders: 62,
    premium: 70,
    active_riders: 98,
    lat: 12.9815,
    lng: 80.2180,
  },
  {
    zone_id: "zone_annanagar",
    name: "Anna Nagar",
    risk_level: "low",
    avg_orders: 110,
    premium: 30,
    active_riders: 175,
    lat: 13.0850,
    lng: 80.2101,
  },
  {
    zone_id: "zone_tambaram",
    name: "Tambaram",
    risk_level: "high",
    avg_orders: 45,
    premium: 70,
    active_riders: 67,
    lat: 12.9249,
    lng: 80.1000,
  },
  {
    zone_id: "zone_adyar",
    name: "Adyar",
    risk_level: "medium",
    avg_orders: 78,
    premium: 50,
    active_riders: 130,
    lat: 13.0012,
    lng: 80.2565,
  },
];
