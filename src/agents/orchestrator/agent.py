"""Main LangGraph orchestrator.

Builds and compiles the StateGraph that chains together all insurance agents:

    data_ingestion → disruption_analyst → fraud_validator → actuarial_engine → payout_processor

Conditional edges:
    - No disruption detected after data_ingestion      → END
    - Fraud detected after fraud_validator              → reject_claim → END
    - Claim rejected during disruption_analyst          → END
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from src.agents.weather.agent import weather_agent
from src.agents.claims.agent import claims_agent
from src.agents.fraud.agent import fraud_agent
from src.agents.risk.agent import risk_agent
from src.agents.payout.agent import payout_agent
from src.models.schemas import (
    AgentState,
    Claim,
    ClaimStatus,
    DisruptionEvent,
    GeoLocation,
    IncomeLossCalculation,
    InsurancePolicy,
    PayoutRequest,
    UserProfile,
    ValidationResult,
    Warehouse,
    WeatherData,
    Zone,
)


# ── State type for LangGraph ────────────────────────────────────────────────
# LangGraph works with TypedDict (or dict); we mirror AgentState fields.

class InsuranceGraphState(TypedDict, total=False):
    claim: Claim | None
    user: UserProfile | None
    policy: InsurancePolicy | None
    weather: WeatherData | None
    disruption: DisruptionEvent | None
    zone: Zone | None
    warehouse: Warehouse | None
    validation: ValidationResult | None
    income_loss: IncomeLossCalculation | None
    payout: PayoutRequest | None
    fraud_score: float
    risk_assessment: dict | None
    decision: str
    reasoning: list[str]
    error: str | None
    # Optional ancillary data passed through
    trajectory: list[GeoLocation] | None
    recent_claims: list[dict[str, Any]] | None


# ── Rejection sink node ─────────────────────────────────────────────────────

async def reject_claim(state: dict[str, Any]) -> dict[str, Any]:
    """Terminal node that formally rejects the claim and logs the reason."""
    logger.warning("Reject node: claim rejected")
    reasoning = state.get("reasoning", []).copy()
    claim: Claim | None = state.get("claim")

    if claim is not None:
        claim.status = ClaimStatus.REJECTED
        claim.resolved_at = datetime.now(tz=timezone.utc)

    reasoning.append("Claim formally rejected by orchestrator")

    return {
        **state,
        "claim": claim,
        "decision": "rejected",
        "reasoning": reasoning,
    }


# ── Routing functions ────────────────────────────────────────────────────────

def _route_after_ingestion(state: dict[str, Any]) -> str:
    """After data_ingestion: continue only if a disruption was detected."""
    disruption = state.get("disruption")
    error = state.get("error")

    if error:
        logger.warning(f"Routing to END due to ingestion error: {error}")
        return END

    if disruption is None:
        logger.info("No disruption detected – routing to END")
        return END

    return "disruption_analyst"


def _route_after_claims(state: dict[str, Any]) -> str:
    """After disruption_analyst: reject invalid claims early."""
    decision = state.get("decision", "continue")

    if decision == "rejected":
        logger.info("Claim rejected during validation – routing to END")
        return END

    return "fraud_validator"


def _route_after_fraud(state: dict[str, Any]) -> str:
    """After fraud_validator: reject fraudulent claims."""
    decision = state.get("decision", "continue")

    if decision == "fraud_detected":
        logger.warning("Fraud detected – routing to reject_claim")
        return "reject_claim"

    return "actuarial_engine"


def _route_after_risk(state: dict[str, Any]) -> str:
    """After actuarial_engine: always proceed to payout."""
    return "payout_processor"


# ── Graph builder ────────────────────────────────────────────────────────────

def build_insurance_graph() -> StateGraph:
    """Construct and return the compiled LangGraph StateGraph.

    Graph topology::

        data_ingestion
            │
            ├─ no disruption → END
            │
            ▼
        disruption_analyst
            │
            ├─ rejected → END
            │
            ▼
        fraud_validator
            │
            ├─ fraud_detected → reject_claim → END
            │
            ▼
        actuarial_engine
            │
            ▼
        payout_processor
            │
            ▼
           END
    """
    graph = StateGraph(InsuranceGraphState)

    # ── Add nodes ────────────────────────────────────────────────────────
    graph.add_node("data_ingestion", weather_agent)
    graph.add_node("disruption_analyst", claims_agent)
    graph.add_node("fraud_validator", fraud_agent)
    graph.add_node("actuarial_engine", risk_agent)
    graph.add_node("payout_processor", payout_agent)
    graph.add_node("reject_claim", reject_claim)

    # ── Set entry point ──────────────────────────────────────────────────
    graph.set_entry_point("data_ingestion")

    # ── Conditional edges ────────────────────────────────────────────────
    graph.add_conditional_edges(
        "data_ingestion",
        _route_after_ingestion,
        {
            "disruption_analyst": "disruption_analyst",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "disruption_analyst",
        _route_after_claims,
        {
            "fraud_validator": "fraud_validator",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "fraud_validator",
        _route_after_fraud,
        {
            "reject_claim": "reject_claim",
            "actuarial_engine": "actuarial_engine",
        },
    )

    graph.add_edge("actuarial_engine", "payout_processor")
    graph.add_edge("payout_processor", END)
    graph.add_edge("reject_claim", END)

    return graph


def compile_insurance_graph():
    """Build and compile the graph, returning a runnable."""
    graph = build_insurance_graph()
    return graph.compile()


# ── Pipeline runner ──────────────────────────────────────────────────────────

async def run_insurance_pipeline(
    claim: Claim,
    user: UserProfile,
    policy: InsurancePolicy | None = None,
    zone: Zone | None = None,
    warehouse: Warehouse | None = None,
    trajectory: list[GeoLocation] | None = None,
    recent_claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """High-level entry point: run a claim through the full insurance pipeline.

    Returns the final state dict with decision, reasoning, payout info, etc.
    """
    logger.info(f"Pipeline: starting for claim {claim.claim_id}, user {user.user_id}")

    initial_state: dict[str, Any] = {
        "claim": claim,
        "user": user,
        "policy": policy,
        "zone": zone,
        "warehouse": warehouse,
        "weather": None,
        "disruption": None,
        "validation": None,
        "income_loss": None,
        "payout": None,
        "fraud_score": 0.0,
        "risk_assessment": None,
        "decision": "pending",
        "reasoning": [],
        "error": None,
        "trajectory": trajectory,
        "recent_claims": recent_claims,
    }

    compiled = compile_insurance_graph()
    final_state = await compiled.ainvoke(initial_state)

    decision = final_state.get("decision", "unknown")
    logger.info(
        f"Pipeline: completed for claim {claim.claim_id} → decision={decision}"
    )
    logger.info(f"Pipeline reasoning: {final_state.get('reasoning', [])}")

    return final_state
