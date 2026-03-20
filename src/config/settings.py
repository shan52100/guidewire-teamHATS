"""Application configuration and settings."""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Keys
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    secret_key: str = os.getenv("SECRET_KEY", "hackathon-secret-key-2024")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./insurance.db")

    # Mock Services
    mock_delivery_api: bool = True
    mock_payment_gateway: bool = True

    # Insurance Parameters
    max_weekly_payout: float = 2000.0
    base_premium_weekly: float = 99.0
    warehouse_radius_km: float = 5.0
    min_activity_threshold: float = 0.3
    fraud_score_threshold: float = 0.7

    # Weather Thresholds
    heavy_rain_mm: float = 20.0
    flood_alert_level: int = 3
    pollution_aqi_threshold: int = 300

    # Rate Limiting
    max_claims_per_week: int = 5
    cooldown_hours: int = 4

    # LLM Config
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.1

    class Config:
        env_file = ".env"


settings = Settings()
