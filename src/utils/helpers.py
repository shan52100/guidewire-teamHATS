"""Utility functions used across the insurance platform."""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Tuple


def generate_id(prefix: str = "INS") -> str:
    """Generate a unique ID with the given prefix.

    Args:
        prefix: Short prefix string (e.g. "CLM", "POL", "USR").

    Returns:
        A string like ``CLM-a1b2c3d4``.
    """
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}-{short_uuid}"


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the great-circle distance between two points using the Haversine formula.

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.

    Returns:
        Distance in kilometres.
    """
    R = 6371.0  # Earth radius in km

    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def severity_to_label(severity: float) -> str:
    """Map a 0.0-1.0 severity float to a human-readable label.

    Args:
        severity: Value between 0.0 and 1.0.

    Returns:
        One of ``"low"``, ``"medium"``, ``"high"``, or ``"critical"``.
    """
    if severity < 0.25:
        return "low"
    elif severity < 0.50:
        return "medium"
    elif severity < 0.75:
        return "high"
    else:
        return "critical"


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format a numeric amount as an Indian-style currency string.

    Args:
        amount: The monetary value.
        currency: ISO-4217 currency code (default ``INR``).

    Returns:
        Formatted string, e.g. ``"INR 1,234.50"``.
    """
    if currency == "INR":
        # Indian numbering: last 3 digits, then groups of 2
        sign = "-" if amount < 0 else ""
        abs_amount = abs(amount)
        integer_part = int(abs_amount)
        decimal_part = f"{abs_amount - integer_part:.2f}"[1:]  # ".50"

        s = str(integer_part)
        if len(s) <= 3:
            formatted = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            groups: list[str] = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            formatted = ",".join(groups) + "," + last3

        return f"{sign}{currency} {formatted}{decimal_part}"

    return f"{currency} {amount:,.2f}"


def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """Check whether latitude/longitude values are within valid ranges.

    Args:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.

    Returns:
        A ``(is_valid, message)`` tuple.
    """
    if not (-90.0 <= latitude <= 90.0):
        return False, f"Latitude {latitude} is out of range [-90, 90]"
    if not (-180.0 <= longitude <= 180.0):
        return False, f"Longitude {longitude} is out of range [-180, 180]"
    if latitude == 0.0 and longitude == 0.0:
        return False, "Coordinates (0, 0) are likely invalid (Null Island)"
    return True, "Coordinates are valid"
