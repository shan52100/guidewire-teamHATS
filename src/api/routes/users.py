"""Users API routes: register, retrieve, update location."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from src.api.middleware.auth import create_access_token, rate_limiter, verify_token
from src.models.schemas import GeoLocation, UserProfile, UserRole
from src.utils.helpers import generate_id, validate_coordinates

router = APIRouter(prefix="/users", tags=["Users"])

# ─── In-memory user store (demo) ─────────────────────────────────────────────
_users_db: Dict[str, UserProfile] = {}


# ─── Request / Response models ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload to register a new delivery partner."""
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    email: Optional[str] = None
    latitude: float
    longitude: float
    delivery_platform: str = Field(default="zepto", pattern=r"^(zepto|blinkit)$")
    assigned_warehouse_id: Optional[str] = None


class RegisterResponse(BaseModel):
    user: UserProfile
    access_token: str
    message: str


class LocationUpdateRequest(BaseModel):
    """Payload to update a user's GPS location."""
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    source: str = Field(default="gps", pattern=r"^(gps|network|mock)$")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new delivery partner",
    dependencies=[Depends(rate_limiter)],
)
async def register_user(req: RegisterRequest) -> RegisterResponse:
    """Register a new delivery partner and return an access token."""
    # Validate coordinates
    valid, msg = validate_coordinates(req.latitude, req.longitude)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # Check for duplicate phone
    for existing in _users_db.values():
        if existing.phone == req.phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phone number {req.phone} already registered",
            )

    user_id = generate_id("USR")
    now = datetime.utcnow()

    user = UserProfile(
        user_id=user_id,
        name=req.name,
        phone=req.phone,
        email=req.email,
        role=UserRole.DELIVERY_PARTNER,
        registration_date=now,
        home_location=GeoLocation(
            latitude=req.latitude,
            longitude=req.longitude,
            timestamp=now,
        ),
        delivery_platform=req.delivery_platform,
        assigned_warehouse_id=req.assigned_warehouse_id,
    )

    _users_db[user_id] = user

    # Issue JWT
    token = create_access_token(
        data={"sub": user_id, "role": user.role.value, "name": user.name}
    )

    logger.info("User registered: {} ({}) on {}", user_id, req.name, req.delivery_platform)

    return RegisterResponse(
        user=user,
        access_token=token,
        message=f"Welcome, {req.name}! Your rider ID is {user_id}.",
    )


@router.get(
    "/{user_id}",
    response_model=UserProfile,
    summary="Get user profile",
)
async def get_user(
    user_id: str,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> UserProfile:
    """Retrieve a user profile by ID."""
    user = _users_db.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


@router.put(
    "/{user_id}/location",
    response_model=UserProfile,
    summary="Update rider GPS location",
    dependencies=[Depends(rate_limiter)],
)
async def update_location(
    user_id: str,
    req: LocationUpdateRequest,
    token_data: Dict[str, Any] = Depends(verify_token),
) -> UserProfile:
    """Update a rider's current GPS location (for tracking and claim validation)."""
    user = _users_db.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    valid, msg = validate_coordinates(req.latitude, req.longitude)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    user.home_location = GeoLocation(
        latitude=req.latitude,
        longitude=req.longitude,
        accuracy_meters=req.accuracy_meters,
        timestamp=datetime.utcnow(),
        source=req.source,
    )

    _users_db[user_id] = user
    logger.debug("Location updated for user {}: ({}, {})", user_id, req.latitude, req.longitude)

    return user
