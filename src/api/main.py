"""FastAPI application entry-point.

Start with:
    python -m uvicorn src.api.main:app --reload
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.config.settings import settings

# ─── Logging configuration ───────────────────────────────────────────────────

# Remove default loguru sink and add a formatted one
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    logger.info("InsureFlow AI starting up...")
    logger.info("Environment: mock_weather={}, mock_delivery={}, mock_payment={}",
                settings.mock_weather_api, settings.mock_delivery_api, settings.mock_payment_gateway)
    logger.info("Rate limit: {} req/min | Fraud threshold: {}",
                settings.rate_limit_requests_per_minute, settings.fraud_score_threshold)
    yield
    logger.info("InsureFlow AI shutting down...")


# ─── App factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="InsureFlow AI",
    description=(
        "AI-powered parametric insurance platform for quick-commerce delivery partners. "
        "Uses LangGraph + multi-agent orchestration for automated claim processing, "
        "fraud detection, and instant payouts."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Mount routers ────────────────────────────────────────────────────────────

from src.api.routes.claims import router as claims_router  # noqa: E402
from src.api.routes.policies import router as policies_router  # noqa: E402
from src.api.routes.users import router as users_router  # noqa: E402
from src.api.routes.admin import router as admin_router  # noqa: E402

app.include_router(claims_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


# ─── Root endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint returning API information."""
    return {
        "name": "InsureFlow AI",
        "version": "1.0.0",
        "description": "AI Parametric Insurance for Quick-Commerce Delivery Partners",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": "/api/v1",
        "endpoints": {
            "users": "/api/v1/users",
            "policies": "/api/v1/policies",
            "claims": "/api/v1/claims",
            "admin": "/api/v1/admin",
        },
    }


@app.get("/health", tags=["Root"])
async def health_check() -> dict:
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "InsureFlow AI",
        "version": "1.0.0",
        "mock_mode": {
            "weather": settings.mock_weather_api,
            "delivery": settings.mock_delivery_api,
            "payment": settings.mock_payment_gateway,
        },
    }
