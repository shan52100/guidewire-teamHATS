"""AI Parametric Insurance - Agent modules.

Exports all agent functions for convenient access:

    from src.agents import weather_agent, claims_agent, fraud_agent, ...
"""
from src.agents.weather.agent import weather_agent, fetch_weather_data
from src.agents.claims.agent import claims_agent, validate_claim
from src.agents.fraud.agent import (
    fraud_agent,
    detect_fraud,
    detect_gps_spoofing,
    detect_fraud_ring,
)
from src.agents.payout.agent import (
    payout_agent,
    calculate_income_loss,
    process_payment,
)
from src.agents.risk.agent import (
    risk_agent,
    calculate_premium,
    assess_risk,
)
from src.agents.orchestrator.agent import (
    build_insurance_graph,
    compile_insurance_graph,
    run_insurance_pipeline,
)

__all__ = [
    # Weather
    "weather_agent",
    "fetch_weather_data",
    # Claims
    "claims_agent",
    "validate_claim",
    # Fraud
    "fraud_agent",
    "detect_fraud",
    "detect_gps_spoofing",
    "detect_fraud_ring",
    # Payout
    "payout_agent",
    "calculate_income_loss",
    "process_payment",
    # Risk
    "risk_agent",
    "calculate_premium",
    "assess_risk",
    # Orchestrator
    "build_insurance_graph",
    "compile_insurance_graph",
    "run_insurance_pipeline",
]
