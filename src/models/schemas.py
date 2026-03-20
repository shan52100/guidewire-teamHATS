"""Pydantic models for the insurance system."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    DELIVERY_PARTNER = "delivery_partner"
    ADMIN = "admin"
    INSURER = "insurer"

class PolicyStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

class ClaimStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    FLAGGED = "flagged"

class DisruptionType(str, Enum):
    HEAVY_RAIN = "heavy_rain"
    FLOOD = "flood"
    POLLUTION = "pollution"
    ZONE_CLOSURE = "zone_closure"
    PLATFORM_OUTAGE = "platform_outage"
    MULTI_TRIGGER = "multi_trigger"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FraudFlag(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FLAGGED = "flagged"
    BLOCKED = "blocked"


# ─── User Models ──────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    name: str
    role: UserRole = UserRole.DELIVERY_PARTNER
    phone: str
    email: Optional[str] = None
    registration_date: datetime
    home_location: "GeoLocation"
    assigned_warehouse_id: Optional[str] = None
    delivery_platform: str = "zepto"  # zepto / blinkit
    risk_score: float = 0.5
    trust_score: float = 0.5
    total_claims: int = 0
    total_payouts: float = 0.0
    is_active: bool = True

class GeoLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: str = "gps"  # gps / network / mock


# ─── Policy Models ────────────────────────────────────────────────────────────

class InsurancePolicy(BaseModel):
    policy_id: str
    user_id: str
    status: PolicyStatus = PolicyStatus.ACTIVE
    premium_amount: float
    coverage_amount: float
    start_date: datetime
    end_date: datetime
    zone_id: str
    warehouse_id: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PremiumCalculation(BaseModel):
    base_premium: float
    risk_multiplier: float
    zone_factor: float
    history_discount: float
    final_premium: float
    breakdown: dict


# ─── Claim Models ─────────────────────────────────────────────────────────────

class Claim(BaseModel):
    claim_id: str
    policy_id: str
    user_id: str
    status: ClaimStatus = ClaimStatus.PENDING
    disruption_type: DisruptionType
    disruption_severity: float  # 0.0 to 1.0
    trigger_timestamp: datetime
    location: GeoLocation
    estimated_loss: float
    approved_payout: float = 0.0
    validation_results: Optional["ValidationResult"] = None
    fraud_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class ValidationResult(BaseModel):
    policy_valid: bool = False
    location_valid: bool = False
    time_valid: bool = False
    activity_valid: bool = False
    warehouse_proximity_valid: bool = False
    zone_activity_valid: bool = False
    fraud_check_passed: bool = False
    duplicate_check_passed: bool = False
    overall_valid: bool = False
    rejection_reasons: List[str] = []
    confidence_score: float = 0.0


# ─── Weather & Disruption Models ─────────────────────────────────────────────

class WeatherData(BaseModel):
    zone_id: str
    timestamp: datetime
    temperature: float
    humidity: float
    rainfall_mm: float
    wind_speed: float
    aqi: Optional[int] = None
    flood_alert_level: int = 0
    visibility_km: float = 10.0
    condition: str = "clear"

class DisruptionEvent(BaseModel):
    event_id: str
    zone_id: str
    disruption_type: DisruptionType
    severity: float  # 0.0 to 1.0
    start_time: datetime
    end_time: Optional[datetime] = None
    affected_warehouses: List[str] = []
    weather_data: Optional[WeatherData] = None
    is_active: bool = True


# ─── Zone & Warehouse Models ─────────────────────────────────────────────────

class Zone(BaseModel):
    zone_id: str
    name: str
    center: GeoLocation
    radius_km: float
    risk_level: RiskLevel = RiskLevel.MEDIUM
    avg_order_density: float  # orders per hour
    is_active: bool = True

class Warehouse(BaseModel):
    warehouse_id: str
    name: str
    zone_id: str
    location: GeoLocation
    radius_km: float = 5.0
    is_operational: bool = True
    avg_orders_per_hour: float = 50.0


# ─── Payout Models ────────────────────────────────────────────────────────────

class PayoutRequest(BaseModel):
    payout_id: str
    claim_id: str
    user_id: str
    amount: float
    status: str = "pending"  # pending / processing / completed / failed / retrying
    payment_method: str = "upi"
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IncomeLossCalculation(BaseModel):
    avg_orders_per_hour: float
    avg_income_per_order: float
    lost_hours: float
    severity_multiplier: float
    base_loss: float
    adjusted_loss: float
    payout_cap_applied: bool = False
    final_payout: float


# ─── Agent State Models ───────────────────────────────────────────────────────

class AgentState(BaseModel):
    """State passed through the LangGraph decision graph."""
    claim: Optional[Claim] = None
    user: Optional[UserProfile] = None
    policy: Optional[InsurancePolicy] = None
    weather: Optional[WeatherData] = None
    disruption: Optional[DisruptionEvent] = None
    zone: Optional[Zone] = None
    warehouse: Optional[Warehouse] = None
    validation: Optional[ValidationResult] = None
    income_loss: Optional[IncomeLossCalculation] = None
    payout: Optional[PayoutRequest] = None
    fraud_score: float = 0.0
    risk_assessment: Optional[dict] = None
    decision: str = "pending"
    reasoning: List[str] = []
    error: Optional[str] = None


# Fix forward references
UserProfile.model_rebuild()
Claim.model_rebuild()
