"""Application configuration and settings."""
from pydantic_settings import BaseSettings
from typing import Dict, List


class Settings(BaseSettings):
    """Central configuration loaded from environment variables and .env file."""

    # ─── API Keys ────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    weather_api_key: str = ""
    secret_key: str = "hackathon-secret-key-2024"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 1440  # 24 hours

    # ─── Database ────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./insurance.db"

    # ─── Mock Services ───────────────────────────────────────────────────────
    mock_delivery_api: bool = True
    mock_payment_gateway: bool = True
    mock_weather_api: bool = False

    # ─── Insurance Parameters ────────────────────────────────────────────────
    max_weekly_payout: float = 2000.0
    base_premium_weekly: float = 99.0
    warehouse_radius_km: float = 5.0
    min_activity_threshold: float = 0.3
    fraud_score_threshold: float = 0.7
    min_coverage_amount: float = 500.0
    max_coverage_amount: float = 10000.0

    # ─── Premium Rates ───────────────────────────────────────────────────────
    premium_risk_multipliers: Dict[str, float] = {
        "low": 0.8,
        "medium": 1.0,
        "high": 1.4,
        "critical": 2.0,
    }
    premium_zone_factors: Dict[str, float] = {
        "CHN-TNG": 1.0,
        "CHN-VLC": 1.3,
        "CHN-ANG": 0.85,
        "CHN-MYL": 1.1,
        "CHN-ADR": 1.2,
    }
    history_discount_per_clean_month: float = 0.02  # 2% discount per clean month
    max_history_discount: float = 0.20  # cap at 20%

    # ─── Weather Thresholds ──────────────────────────────────────────────────
    heavy_rain_mm: float = 20.0
    flood_alert_level: int = 2
    pollution_aqi_threshold: int = 300
    wind_speed_threshold: float = 60.0  # km/h

    # ─── Fraud Detection Thresholds ──────────────────────────────────────────
    fraud_velocity_threshold_kmh: float = 120.0  # GPS spoofing: impossible speed
    fraud_max_claims_per_day: int = 3
    fraud_duplicate_window_hours: int = 6
    fraud_cluster_radius_km: float = 0.5
    fraud_anomaly_zscore: float = 2.5

    # ─── Payout Caps ─────────────────────────────────────────────────────────
    payout_cap_per_claim: float = 1500.0
    payout_cap_per_week: float = 2000.0
    payout_cap_per_month: float = 6000.0
    payout_retry_max: int = 3
    payout_retry_wait_seconds: int = 5

    # ─── Zone Configurations ─────────────────────────────────────────────────
    default_zones: List[str] = [
        "CHN-TNG",
        "CHN-VLC",
        "CHN-ANG",
        "CHN-MYL",
        "CHN-ADR",
    ]

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    max_claims_per_week: int = 5
    cooldown_hours: int = 4
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # ─── LLM Config ──────────────────────────────────────────────────────────
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.1

    # ─── Logging ─────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ─── CORS ────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8501"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
