"""Delivery platform service: simulates Zepto/Blinkit API for rider data."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from src.utils.helpers import generate_id


# ─── Mock data ────────────────────────────────────────────────────────────────

_MOCK_RIDERS: Dict[str, Dict[str, Any]] = {
    "USR-rider001": {
        "name": "Ravi Kumar",
        "platform": "zepto",
        "status": "active",
        "avg_orders_per_hour": 4.2,
        "avg_income_per_order": 45.0,
        "total_deliveries": 1245,
        "rating": 4.7,
        "zone_id": "CHN-TNG",
        "warehouse_id": "WH-TNG-01",
    },
    "USR-rider002": {
        "name": "Priya Sharma",
        "platform": "blinkit",
        "status": "active",
        "avg_orders_per_hour": 3.8,
        "avg_income_per_order": 42.0,
        "total_deliveries": 890,
        "rating": 4.5,
        "zone_id": "CHN-VLC",
        "warehouse_id": "WH-VLC-01",
    },
    "USR-rider003": {
        "name": "Arjun Menon",
        "platform": "zepto",
        "status": "active",
        "avg_orders_per_hour": 5.1,
        "avg_income_per_order": 48.0,
        "total_deliveries": 2100,
        "rating": 4.9,
        "zone_id": "CHN-ANG",
        "warehouse_id": "WH-ANG-01",
    },
}

_MOCK_ZONE_ACTIVITY: Dict[str, Dict[str, Any]] = {
    "CHN-TNG": {"active_riders": 45, "orders_last_hour": 180, "avg_delivery_time_min": 12, "surge_multiplier": 1.0},
    "CHN-VLC": {"active_riders": 32, "orders_last_hour": 95, "avg_delivery_time_min": 18, "surge_multiplier": 1.3},
    "CHN-ANG": {"active_riders": 55, "orders_last_hour": 220, "avg_delivery_time_min": 10, "surge_multiplier": 0.9},
    "CHN-MYL": {"active_riders": 38, "orders_last_hour": 140, "avg_delivery_time_min": 14, "surge_multiplier": 1.1},
    "CHN-ADR": {"active_riders": 28, "orders_last_hour": 110, "avg_delivery_time_min": 16, "surge_multiplier": 1.2},
}


class DeliveryPlatformService:
    """Interface to delivery platform APIs (Zepto / Blinkit).

    In production this would call actual platform APIs via OAuth.
    Currently operates in mock mode, returning realistic synthetic data.
    """

    def __init__(self) -> None:
        logger.info("DeliveryPlatformService initialised (mock mode)")

    async def get_rider_status(self, user_id: str) -> Dict[str, Any]:
        """Fetch the current status of a rider from the platform.

        Args:
            user_id: Internal user identifier.

        Returns:
            Dict with keys: ``status``, ``last_order_time``, ``current_location``,
            ``is_online``, ``shift_started_at``.
        """
        rider = _MOCK_RIDERS.get(user_id)
        if rider is None:
            logger.warning("Rider {} not found in mock data; generating default", user_id)
            rider = self._generate_default_rider(user_id)

        now = datetime.utcnow()
        is_online = random.random() > 0.15  # 85% chance rider is online during checks
        last_order_delta = timedelta(minutes=random.randint(5, 120))

        result = {
            "user_id": user_id,
            "platform": rider["platform"],
            "status": "online" if is_online else "offline",
            "is_online": is_online,
            "last_order_time": (now - last_order_delta).isoformat(),
            "shift_started_at": (now - timedelta(hours=random.randint(1, 8))).isoformat(),
            "current_zone": rider["zone_id"],
            "rating": rider["rating"],
        }
        logger.debug("Rider status for {}: {}", user_id, result["status"])
        return result

    async def get_order_history(
        self,
        user_id: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent order history for a rider.

        Args:
            user_id: Internal user identifier.
            hours: Look-back window in hours.

        Returns:
            List of order dicts with ``order_id``, ``timestamp``, ``amount``, ``status``.
        """
        rider = _MOCK_RIDERS.get(user_id, self._generate_default_rider(user_id))
        avg_per_hour = rider["avg_orders_per_hour"]
        total_orders = int(avg_per_hour * hours * random.uniform(0.7, 1.1))

        now = datetime.utcnow()
        orders: List[Dict[str, Any]] = []
        for i in range(total_orders):
            ts = now - timedelta(minutes=random.randint(1, hours * 60))
            orders.append(
                {
                    "order_id": generate_id("ORD"),
                    "timestamp": ts.isoformat(),
                    "amount": round(random.uniform(80, 500), 2),
                    "delivery_fee": round(rider["avg_income_per_order"] * random.uniform(0.8, 1.2), 2),
                    "status": random.choice(["delivered", "delivered", "delivered", "cancelled"]),
                    "distance_km": round(random.uniform(0.5, 5.0), 1),
                }
            )

        orders.sort(key=lambda o: o["timestamp"], reverse=True)
        logger.debug("Order history for {}: {} orders in last {}h", user_id, len(orders), hours)
        return orders

    async def get_zone_activity(self, zone_id: str) -> Dict[str, Any]:
        """Fetch real-time activity metrics for a delivery zone.

        Args:
            zone_id: Zone identifier (e.g. ``CHN-TNG``).

        Returns:
            Dict with ``active_riders``, ``orders_last_hour``, ``avg_delivery_time_min``,
            ``surge_multiplier``, and ``demand_level``.
        """
        base = _MOCK_ZONE_ACTIVITY.get(
            zone_id,
            {"active_riders": 30, "orders_last_hour": 100, "avg_delivery_time_min": 15, "surge_multiplier": 1.0},
        )

        # Add slight randomness to simulate real-time variation
        result = {
            "zone_id": zone_id,
            "active_riders": max(1, base["active_riders"] + random.randint(-5, 5)),
            "orders_last_hour": max(0, base["orders_last_hour"] + random.randint(-20, 20)),
            "avg_delivery_time_min": round(base["avg_delivery_time_min"] + random.uniform(-2, 2), 1),
            "surge_multiplier": round(base["surge_multiplier"] + random.uniform(-0.1, 0.1), 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Compute demand level
        orders = result["orders_last_hour"]
        result["demand_level"] = "high" if orders > 150 else ("medium" if orders > 80 else "low")

        logger.debug("Zone activity for {}: {} orders/h, {} riders", zone_id, result["orders_last_hour"], result["active_riders"])
        return result

    async def get_rider_earnings(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Estimate a rider's recent earnings for income-loss calculations.

        Args:
            user_id: Internal user identifier.
            days: Look-back window in days.

        Returns:
            Dict with ``avg_daily_income``, ``avg_orders_per_hour``,
            ``avg_income_per_order``, ``active_hours_per_day``.
        """
        rider = _MOCK_RIDERS.get(user_id, self._generate_default_rider(user_id))
        active_hours = round(random.uniform(6, 10), 1)
        avg_daily = round(rider["avg_orders_per_hour"] * active_hours * rider["avg_income_per_order"], 2)

        return {
            "user_id": user_id,
            "period_days": days,
            "avg_daily_income": avg_daily,
            "avg_orders_per_hour": rider["avg_orders_per_hour"],
            "avg_income_per_order": rider["avg_income_per_order"],
            "active_hours_per_day": active_hours,
            "total_deliveries_period": int(rider["avg_orders_per_hour"] * active_hours * days),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_default_rider(user_id: str) -> Dict[str, Any]:
        """Produce a default rider profile for unknown user IDs."""
        return {
            "name": f"Rider {user_id[-4:]}",
            "platform": random.choice(["zepto", "blinkit"]),
            "status": "active",
            "avg_orders_per_hour": round(random.uniform(3.0, 5.5), 1),
            "avg_income_per_order": round(random.uniform(38.0, 52.0), 1),
            "total_deliveries": random.randint(100, 3000),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "zone_id": random.choice(["CHN-TNG", "CHN-VLC", "CHN-ANG"]),
            "warehouse_id": "WH-DEFAULT-01",
        }
