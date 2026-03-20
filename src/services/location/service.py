"""Location service: distance, zone containment, warehouse proximity, and GPS spoofing detection."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from geopy.distance import geodesic
from loguru import logger
from shapely.geometry import Point

from src.models.schemas import GeoLocation, Warehouse, Zone
from src.utils.helpers import calculate_distance, validate_coordinates


class LocationService:
    """Geospatial utilities for claim validation and fraud detection.

    Uses ``geopy`` for precise geodesic distances and ``shapely`` for
    geometric containment checks.  Includes heuristics for GPS-spoofing
    detection (velocity analysis, trajectory smoothness).
    """

    def __init__(self) -> None:
        self._location_history: Dict[str, List[Tuple[GeoLocation, datetime]]] = {}

    # ── Distance ─────────────────────────────────────────────────────────────

    def calculate_distance_km(self, loc1: GeoLocation, loc2: GeoLocation) -> float:
        """Geodesic distance between two locations in kilometres.

        Args:
            loc1: First location.
            loc2: Second location.

        Returns:
            Distance in km, rounded to 3 decimal places.
        """
        dist = geodesic(
            (loc1.latitude, loc1.longitude),
            (loc2.latitude, loc2.longitude),
        ).kilometers
        return round(dist, 3)

    # ── Zone containment ─────────────────────────────────────────────────────

    def is_in_zone(self, location: GeoLocation, zone: Zone) -> bool:
        """Check whether a point falls within a circular zone.

        Args:
            location: The point to test.
            zone: A :class:`Zone` with a centre and radius.

        Returns:
            ``True`` if the point is inside the zone radius.
        """
        dist = self.calculate_distance_km(location, zone.center)
        inside = dist <= zone.radius_km
        logger.debug(
            "Zone check: ({:.4f},{:.4f}) -> {} ({:.2f} km, radius {:.2f} km) = {}",
            location.latitude,
            location.longitude,
            zone.zone_id,
            dist,
            zone.radius_km,
            inside,
        )
        return inside

    # ── Warehouse proximity ──────────────────────────────────────────────────

    def validate_warehouse_proximity(
        self,
        location: GeoLocation,
        warehouse: Warehouse,
        max_distance_km: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """Check that a location is within operational range of a warehouse.

        Args:
            location: The rider / claim location.
            warehouse: Target warehouse.
            max_distance_km: Override max distance (defaults to ``warehouse.radius_km``).

        Returns:
            ``(is_valid, distance_km)`` tuple.
        """
        max_dist = max_distance_km if max_distance_km is not None else warehouse.radius_km
        dist = self.calculate_distance_km(location, warehouse.location)
        valid = dist <= max_dist
        logger.debug(
            "Warehouse proximity: {} -> {} = {:.2f} km (max {:.2f}) valid={}",
            location.latitude,
            warehouse.warehouse_id,
            dist,
            max_dist,
            valid,
        )
        return valid, dist

    # ── GPS Spoofing Detection ───────────────────────────────────────────────

    def record_location(self, user_id: str, location: GeoLocation) -> None:
        """Record a location sample for later trajectory analysis.

        Args:
            user_id: User whose location is being tracked.
            location: Current location reading.
        """
        ts = location.timestamp or datetime.utcnow()
        history = self._location_history.setdefault(user_id, [])
        history.append((location, ts))
        # Keep a rolling window of the last 100 readings
        if len(history) > 100:
            self._location_history[user_id] = history[-100:]

    def detect_gps_spoofing(
        self,
        user_id: str,
        current_location: GeoLocation,
        max_velocity_kmh: float = 120.0,
    ) -> Tuple[bool, List[str]]:
        """Analyse location history for signs of GPS spoofing.

        Checks performed:
        1. **Velocity check** -- impossible travel speed between consecutive readings.
        2. **Trajectory smoothness** -- erratic jumps that don't follow road patterns.
        3. **Accuracy anomaly** -- suspiciously perfect GPS accuracy values.

        Args:
            user_id: User to check.
            current_location: Latest GPS reading.
            max_velocity_kmh: Speed threshold above which travel is suspicious.

        Returns:
            ``(is_suspicious, reasons)`` tuple.
        """
        reasons: List[str] = []
        history = self._location_history.get(user_id, [])

        # Record current reading
        self.record_location(user_id, current_location)

        if len(history) < 2:
            return False, reasons

        # --- Velocity check ---
        prev_loc, prev_ts = history[-2]
        curr_ts = current_location.timestamp or datetime.utcnow()

        time_delta_h = (curr_ts - prev_ts).total_seconds() / 3600.0
        if time_delta_h > 0:
            dist_km = self.calculate_distance_km(prev_loc, current_location)
            velocity = dist_km / time_delta_h
            if velocity > max_velocity_kmh:
                reasons.append(
                    f"Impossible velocity: {velocity:.1f} km/h "
                    f"(moved {dist_km:.2f} km in {time_delta_h * 60:.1f} min)"
                )
                logger.warning("GPS spoofing suspect (velocity): user={} v={:.1f} km/h", user_id, velocity)

        # --- Trajectory smoothness ---
        if len(history) >= 5:
            recent = history[-5:]
            jumps = 0
            for i in range(1, len(recent)):
                d = self.calculate_distance_km(recent[i - 1][0], recent[i][0])
                if d > 2.0:  # > 2 km jump in a short window
                    jumps += 1
            if jumps >= 3:
                reasons.append(
                    f"Erratic trajectory: {jumps} large jumps in last 5 readings"
                )
                logger.warning("GPS spoofing suspect (trajectory): user={} jumps={}", user_id, jumps)

        # --- Accuracy anomaly ---
        if current_location.accuracy_meters is not None and current_location.accuracy_meters < 1.0:
            reasons.append(
                f"Suspiciously perfect GPS accuracy: {current_location.accuracy_meters}m"
            )

        is_suspicious = len(reasons) > 0
        return is_suspicious, reasons

    def validate_coordinates_check(self, lat: float, lon: float) -> Tuple[bool, str]:
        """Thin wrapper around the utility ``validate_coordinates`` function."""
        return validate_coordinates(lat, lon)
