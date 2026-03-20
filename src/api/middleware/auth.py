"""JWT authentication, API-key validation, and per-user rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger

from src.config.settings import settings

# ─── Constants ────────────────────────────────────────────────────────────────

_ALGORITHM = settings.jwt_algorithm
_SECRET = settings.secret_key
_EXPIRY_MINUTES = settings.jwt_expiry_minutes

_bearer_scheme = HTTPBearer(auto_error=False)

# Valid API keys (in production, these would live in a secure vault / DB)
_VALID_API_KEYS: set[str] = {
    "insureflow-demo-key-2024",
    "hackathon-admin-key",
}


# ─── JWT Helpers ──────────────────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload to encode (must include ``sub`` for user ID).
        expires_delta: Custom expiry; defaults to ``settings.jwt_expiry_minutes``.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=_EXPIRY_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    token = jwt.encode(to_encode, _SECRET, algorithm=_ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token.

    Raises:
        HTTPException 401: If the token is invalid or expired.

    Returns:
        Decoded payload dict.
    """
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency: extract and verify the Bearer token from the request.

    Returns:
        The decoded JWT payload.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


# ─── API Key Validation ──────────────────────────────────────────────────────

async def validate_api_key(request: Request) -> str:
    """FastAPI dependency: validate the ``X-API-Key`` header.

    Returns:
        The validated API key string.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
        )
    if api_key not in _VALID_API_KEYS:
        logger.warning("Invalid API key attempted: {}...", api_key[:8])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key


# ─── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Sliding-window rate limiter keyed by user/IP.

    Args:
        max_requests: Maximum requests allowed in the window.
        window_seconds: Window size in seconds (default 60).
    """

    def __init__(
        self,
        max_requests: int = settings.rate_limit_requests_per_minute,
        window_seconds: int = 60,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: Dict[str, list[float]] = defaultdict(list)

    def _get_key(self, request: Request) -> str:
        """Derive a rate-limit key from the request (user ID or client IP)."""
        # Prefer user_id from state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        if user_id:
            return f"user:{user_id}"
        # Fall back to client IP
        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency that enforces rate limits.

        Raises:
            HTTPException 429: If the rate limit is exceeded.
        """
        key = self._get_key(request)
        now = time.time()
        window_start = now - self._window

        # Prune old entries
        timestamps = self._requests[key]
        self._requests[key] = [ts for ts in timestamps if ts > window_start]

        if len(self._requests[key]) >= self._max_requests:
            retry_after = int(self._window - (now - self._requests[key][0]))
            logger.warning("Rate limit exceeded for {}", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {max(1, retry_after)}s.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[key].append(now)


# Shared rate limiter instance
rate_limiter = RateLimiter()
