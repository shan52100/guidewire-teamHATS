<p align="center">
  <img src="https://img.shields.io/badge/Guidewire-Hackathon%202026-blue?style=for-the-badge" alt="Guidewire Hackathon"/>
  <img src="https://img.shields.io/badge/Team-HATS-orange?style=for-the-badge" alt="Team HATS"/>
  <img src="https://img.shields.io/badge/AI-Parametric%20Insurance-green?style=for-the-badge" alt="AI Parametric Insurance"/>
  <img src="https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Orchestration-purple?style=for-the-badge" alt="LangGraph"/>
</p>

<h1 align="center">InsureFlow AI - Parametric Insurance for Quick Commerce</h1>
<h3 align="center">AI-Powered Parametric Insurance Platform for Quick-Commerce Delivery Partners</h3>
<p align="center"><i>Automated disruption detection, real-time fraud prevention, and instant payouts — zero manual claims.</i></p>

---

## Table of Contents

- [Demo Video](#-demo-video)
- [Problem Statement](#-problem-statement)
- [Persona & Target Users](#-persona--target-users)
- [Use Case Diagram](#-use-case-diagram)
- [System Architecture](#-system-architecture)
- [LangGraph Agent Orchestration](#-langgraph-agent-orchestration)
- [Weekly Premium Model](#-weekly-premium-model---parametric-pricing)
- [Parametric Triggers](#-parametric-triggers)
- [AI/ML Integration in Workflow](#-aiml-integration-in-workflow)
- [Intelligent Fraud Detection & Adversarial Defense](#-intelligent-fraud-detection--adversarial-defense)
- [Adversarial Defense & Anti-Spoofing Strategy](#-adversarial-defense--anti-spoofing-strategy)
- [Platform Decision: Web + Mobile](#-platform-decision-web--mobile)
- [Tech Stack](#-tech-stack)
- [Development Plan](#-development-plan)
- [Scenario Coverage](#-scenario-coverage)
- [Demo Video](#-2-minute-demo-video)
- [Getting Started](#-getting-started)
- [Team](#-team-hats)

---

## Demo Video

<div align="center">

https://github.com/shan52100/guidewire-teamHATS/raw/main/InShot_20260320_232335057.mp4

</div>

> **Strategy:** Build a trust-first parametric insurance system where the default is to pay honest riders fast, and fraud detection works in the background to catch bad actors without creating friction.

---

## Problem Statement

Quick-commerce delivery partners (Zepto, Blinkit, Swiggy Instamart) face **real-time income loss** due to:

| Disruption | Impact |
|---|---|
| Heavy Rain / Floods | Orders drop 40-70%, delivery impossible |
| Air Pollution (AQI > 300) | Health risk, reduced operations |
| Zone Closures / Curfews | Complete income halt |
| Platform Outages | No orders despite availability |

**There is no existing automated system** to compensate delivery partners instantly. Traditional insurance requires manual claim filing, days of processing, and is not designed for gig-economy micro-disruptions.

**InsureFlow AI** solves this with a fully automated **parametric insurance system** — claims are triggered by real-world data, not paperwork.

---

## Persona & Target Users

### Primary Persona: Delivery Partner ("Rider")

```
Name:       Arun (based on our real teammate)
Age:        22
Role:       Part-time Zepto Delivery Partner, Chennai (T. Nagar / Velachery Zone)
Income:     ₹800-1200/day (15-20 deliveries)
Pain Point: Lost ₹5,000+ in a single week during Chennai floods (Dec 2024)
            — no compensation, no fallback income, rent still due
Need:       Affordable weekly insurance that pays out INSTANTLY
            when disruptions hit, without filing claims
```

### Secondary Personas

| Persona | Role | Interaction |
|---|---|---|
| **Platform Admin** | Zepto/Blinkit Ops Manager | Views dashboard, monitors fraud flags, overrides decisions |
| **Insurer** | Insurance Underwriter | Reviews risk models, adjusts premium parameters, audits payouts |
| **Zone Manager** | Warehouse Operations Lead | Validates zone activity data, confirms warehouse status |

### User Journey

```
 Arun subscribes to weekly plan (₹50/week — Moderate Zone)
          │
          ▼
 System monitors Chennai weather + zone data 24/7
          │
          ▼
 Heavy rain detected in Arun's zone (Velachery) at 3 PM
          │
          ▼
 AI validates: active policy ✓ | in-zone ✓ | was active ✓ | not fraud ✓
          │
          ▼
 Payout of ₹350 auto-credited to Arun's UPI in < 60 seconds
          │
          ▼
 Arun gets SMS: "InsureFlow: ₹350 credited for rain disruption"
```

---

## Use Case Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        InsureFlow AI - Use Cases                            │
│                                                                             │
│  ┌──────────────┐                                    ┌──────────────────┐   │
│  │   Delivery    │───▶ Subscribe to Weekly Plan       │   Platform       │   │
│  │   Partner     │───▶ View Active Policy             │   Admin          │   │
│  │   (Rider)     │───▶ Check Claim Status             │                  │   │
│  │              │───▶ View Payout History             │───▶ View Dashboard│  │
│  │              │───▶ Update Location/Profile         │───▶ Review Flags  │  │
│  └──────────────┘                                    │───▶ Manual Override│  │
│                                                      │───▶ Export Reports │  │
│         ┌──────────────────────────┐                 └──────────────────┘   │
│         │      SYSTEM (Auto)       │                                        │
│         │                          │                 ┌──────────────────┐   │
│         │  ○ Monitor Weather APIs  │                 │   Insurer        │   │
│         │  ○ Detect Disruptions    │                 │                  │   │
│         │  ○ Validate Claims       │                 │───▶ Set Premiums  │  │
│         │  ○ Detect Fraud          │                 │───▶ Adjust Risk   │  │
│         │  ○ Calculate Payout      │                 │───▶ Audit Payouts │  │
│         │  ○ Process Payment       │                 │───▶ View Analytics│  │
│         │  ○ Send Notifications    │                 └──────────────────┘   │
│         └──────────────────────────┘                                        │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    External Systems                                │     │
│  │  [Weather API]  [Delivery Platform API]  [Payment Gateway]        │     │
│  │  [SMS/Push Notifications]  [GPS/Location Services]                │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            InsureFlow AI - Architecture                          │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗    │
│  ║                        EXTERNAL DATA SOURCES                             ║    │
│  ║  ┌─────────────┐  ┌──────────────────┐  ┌────────────┐  ┌───────────┐  ║    │
│  ║  │ Weather API  │  │ Delivery Platform│  │ Traffic    │  │ Govt/     │  ║    │
│  ║  │ (OpenWeather)│  │ API (Zepto/      │  │ Data API   │  │ Alert     │  ║    │
│  ║  │              │  │ Blinkit)         │  │            │  │ Systems   │  ║    │
│  ║  └──────┬───────┘  └────────┬─────────┘  └─────┬──────┘  └─────┬─────┘  ║    │
│  ╚═════════╪═══════════════════╪═══════════════════╪═══════════════╪═══════╝    │
│            │                   │                   │               │              │
│            ▼                   ▼                   ▼               ▼              │
│  ╔═════════════════════════════════════════════════════════════════════════╗      │
│  ║                     LANGGRAPH AGENT ORCHESTRATION                      ║      │
│  ║                                                                        ║      │
│  ║  ┌──────────────┐    ┌───────────────┐    ┌──────────────────┐        ║      │
│  ║  │  Node 1:     │    │  Node 2:      │    │  Node 3:         │        ║      │
│  ║  │  DATA        │───▶│  DISRUPTION   │───▶│  FRAUD &         │        ║      │
│  ║  │  INGESTION   │    │  ANALYST      │    │  ELIGIBILITY     │        ║      │
│  ║  │              │    │               │    │  VALIDATOR       │        ║      │
│  ║  └──────────────┘    └───────┬───────┘    └────────┬─────────┘        ║      │
│  ║                              │                     │                   ║      │
│  ║                    No Disruption             Fraud Detected            ║      │
│  ║                              │                     │                   ║      │
│  ║                              ▼                     ▼                   ║      │
│  ║                     ┌──────────────┐      ┌──────────────┐            ║      │
│  ║                     │  TERMINAL:   │      │  TERMINAL:   │            ║      │
│  ║                     │  NO ACTION   │      │  REJECT      │            ║      │
│  ║                     └──────────────┘      └──────────────┘            ║      │
│  ║                                                                        ║      │
│  ║  ┌──────────────────┐    ┌──────────────────┐                         ║      │
│  ║  │  Node 4:         │    │  Node 5:         │                         ║      │
│  ║  │  ACTUARIAL       │───▶│  PAYOUT          │──▶ Payment Gateway     ║      │
│  ║  │  ENGINE          │    │  PROCESSOR       │                         ║      │
│  ║  └──────────────────┘    └──────────────────┘                         ║      │
│  ╚═══════════════════════════════════════════════════════════════════════╝      │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════╗      │
│  ║                          BACKEND (FastAPI)                            ║      │
│  ║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    ║      │
│  ║  │ Auth &   │  │ Policy   │  │ Claims   │  │ Admin & Analytics│    ║      │
│  ║  │ Users API│  │ Mgmt API │  │ API      │  │ API              │    ║      │
│  ║  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    ║      │
│  ╚═══════════════════════════════════════════════════════════════════════╝      │
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════╗      │
│  ║                        FRONTEND (React Dashboard)                     ║      │
│  ║  ┌───────────────┐  ┌────────────────┐  ┌──────────────────────┐    ║      │
│  ║  │ Rider App     │  │ Admin Panel    │  │ Insurer Analytics    │    ║      │
│  ║  │ (Mobile PWA)  │  │ (Web Dashboard)│  │ (Web Dashboard)      │    ║      │
│  ║  └───────────────┘  └────────────────┘  └──────────────────────┘    ║      │
│  ╚═══════════════════════════════════════════════════════════════════════╝      │
│                                                                                  │
│  ╔═════════════════════════════════╗  ╔═══════════════════════════════════╗    │
│  ║  DATABASE                       ║  ║  MONITORING & LOGGING             ║    │
│  ║  SQLite (Dev) / PostgreSQL(Prod)║  ║  Loguru + APScheduler + Plotly    ║    │
│  ╚═════════════════════════════════╝  ╚═══════════════════════════════════╝    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Weather API ──┐
              ├──▶ Data Ingestion ──▶ Trigger Detection ──┬──▶ Validation ──▶ Payout Calc ──▶ Payment
Platform API ─┘         │                                  │        │
                        │                          No Trigger       │Fraud
                        ▼                                  │        │
                  State: Ingested                          ▼        ▼
                     Data                             No Action   Reject ──▶ Admin Dashboard
```

---

## LangGraph Agent Orchestration

Our system uses **LangGraph StateGraph** for multi-agent orchestration. Each node is a specialized AI agent that processes the insurance claim through a directed graph.

### Graph Definition

```python
from langgraph.graph import StateGraph, END

# Define the claim processing graph
workflow = StateGraph(AgentState)

# Add nodes (each is an AI agent)
workflow.add_node("data_ingestion", data_ingestion_agent)
workflow.add_node("disruption_analyst", disruption_detection_agent)
workflow.add_node("fraud_validator", fraud_and_eligibility_agent)
workflow.add_node("actuarial_engine", payout_calculation_agent)
workflow.add_node("payout_processor", payout_processing_agent)
workflow.add_node("reject_claim", rejection_handler)

# Define edges with conditional routing
workflow.set_entry_point("data_ingestion")
workflow.add_edge("data_ingestion", "disruption_analyst")
workflow.add_conditional_edges("disruption_analyst", check_disruption,
    {"disruption_detected": "fraud_validator", "no_disruption": END})
workflow.add_conditional_edges("fraud_validator", check_validity,
    {"valid": "actuarial_engine", "fraud_detected": "reject_claim"})
workflow.add_edge("actuarial_engine", "payout_processor")
workflow.add_edge("payout_processor", END)
workflow.add_edge("reject_claim", END)

graph = workflow.compile()
```

### Agent Descriptions

| Agent Node | Role | AI/ML Used |
|---|---|---|
| **Data Ingestion** | Fetches weather, platform, traffic data in real-time | API aggregation + data normalization |
| **Disruption Analyst** | Detects if a parametric trigger has occurred | LLM reasoning + threshold analysis |
| **Fraud & Eligibility** | Multi-layer validation + fraud scoring | Anomaly detection ML model + rule engine |
| **Actuarial Engine** | Calculates income loss and payout amount | Statistical model + severity weighting |
| **Payout Processor** | Executes payment via gateway | Retry logic + idempotency checks |

### State Management

```python
class AgentState(BaseModel):
    claim: Optional[Claim]              # Current claim being processed
    user: Optional[UserProfile]         # Rider profile + history
    policy: Optional[InsurancePolicy]   # Active weekly policy
    weather: Optional[WeatherData]      # Real-time weather data
    disruption: Optional[DisruptionEvent] # Detected disruption
    validation: Optional[ValidationResult] # Multi-layer validation result
    income_loss: Optional[IncomeLossCalculation] # Calculated loss
    payout: Optional[PayoutRequest]     # Final payout details
    fraud_score: float = 0.0            # ML-generated fraud probability
    decision: str = "pending"           # Final decision
    reasoning: List[str] = []           # Audit trail of decisions
```

---

## Weekly Premium Model - Parametric Pricing

### How the Weekly Premium Works

Unlike traditional insurance with monthly/yearly premiums and manual claims, InsureFlow uses a **weekly micro-premium model** designed for gig workers:

### Zone-Based Pricing Tiers

| Zone Type | Risk Level | Weekly Premium | Coverage Limit | Payout Range |
|---|---|---|---|---|
| **Safe Zone** | Low | **₹30/week** | Up to ₹1,500/week | ₹100 - ₹350/event |
| **Moderate Zone** | Medium | **₹50/week** | Up to ₹2,500/week | ₹150 - ₹500/event |
| **Flood-Prone Zone** | High | **₹70/week** | Up to ₹4,000/week | ₹200 - ₹700/event |

```
┌──────────────────────────────────────────────────────────────┐
│                  WEEKLY PREMIUM STRUCTURE                     │
│                                                              │
│  Zone Premium:        ₹30 (Safe) / ₹50 (Moderate) / ₹70   │
│                       (Flood-Prone)                          │
│  + History Discount:  -5% per clean month (max -25%)         │
│  + Seasonal Adjust:   ×1.3 (monsoon) / ×0.9 (winter)       │
│  ─────────────────────────────────────────────────           │
│  Final Premium:       ₹30 - ₹91/week                        │
│                                                              │
│  Max claims/week:     3                                      │
│  Payout:              Severity-based within zone limits      │
└──────────────────────────────────────────────────────────────┘
```

### Premium Calculation Formula

```
Final Premium = Zone_Base_Premium × Seasonal_Multiplier × (1 - History_Discount)

Where:
  Zone_Base_Premium    = ₹30 (Safe) | ₹50 (Moderate) | ₹70 (Flood-Prone)
  Seasonal_Multiplier  = f(month, regional_weather_patterns) → ×1.3 monsoon / ×0.9 winter
  History_Discount     = min(0.25, clean_months × 0.05)
```

### Why Weekly, Not Monthly?

| Factor | Weekly | Monthly |
|---|---|---|
| **Affordability** | ₹29-149/week is accessible to gig workers earning ₹800-1200/day | ₹200-600/month feels like a large upfront cost |
| **Flexibility** | Skip weeks when not active, no lock-in | Paying for inactive periods |
| **Risk Window** | Shorter exposure period = more accurate pricing | Weather/risk changes significantly within a month |
| **Cash Flow** | Matches gig worker weekly earning cycles | Misaligned with daily/weekly pay patterns |
| **Engagement** | Weekly renewal = regular touchpoint | Set-and-forget, less engagement |

### Parametric Nature

**Parametric** means payouts are triggered by **measurable parameters** (not damage assessment):

```
Traditional Insurance:          Parametric Insurance:
  1. Event occurs                 1. Event occurs
  2. User files claim             2. Sensor/API detects parameter threshold
  3. Adjuster investigates        3. AI validates automatically
  4. Weeks of processing          4. Payout in < 60 seconds
  5. Payout (maybe)               5. Guaranteed payout if threshold met
```

---

## Parametric Triggers

### Trigger Definitions

| Trigger | Data Source | Threshold | Severity Scale |
|---|---|---|---|
| **Heavy Rain** | OpenWeatherMap API | Rainfall > 20mm/hr | Low(20-40mm) / Med(40-80mm) / High(>80mm) |
| **Flood Alert** | Govt Flood API / Weather API | Flood alert level ≥ 2 | Level 2 (moderate) / Level 3 (severe) |
| **Air Pollution** | AQI API | AQI > 300 | 300-400 (severe) / 400+ (hazardous) |
| **Zone Closure** | Platform API / Govt alerts | Zone marked restricted | Binary: closed or open |
| **Platform Outage** | Platform health endpoint | Downtime > 30 min | Duration-based scaling |
| **Multi-Trigger** | Combined sources | 2+ triggers simultaneously | Compounded severity |

### Trigger Detection Logic

```python
def detect_trigger(weather_data: WeatherData, zone_data: Zone) -> DisruptionEvent:
    """LangGraph Node: Disruption Analyst"""
    triggers = []

    if weather_data.rainfall_mm > 20:
        severity = min(1.0, weather_data.rainfall_mm / 100)
        triggers.append(("heavy_rain", severity))

    if weather_data.flood_alert_level >= 2:
        severity = weather_data.flood_alert_level / 4
        triggers.append(("flood", severity))

    if weather_data.aqi and weather_data.aqi > 300:
        severity = min(1.0, (weather_data.aqi - 300) / 200)
        triggers.append(("pollution", severity))

    if len(triggers) >= 2:
        return DisruptionEvent(type="multi_trigger",
                               severity=min(1.0, sum(s for _, s in triggers)))
    elif triggers:
        return DisruptionEvent(type=triggers[0][0], severity=triggers[0][1])
    return None  # No disruption
```

### Why These Triggers?

Each trigger is chosen because it is:
1. **Objectively measurable** — data comes from third-party APIs, not user-reported
2. **Directly correlated to income loss** — rain = fewer orders = less income
3. **Independently verifiable** — admin can cross-check with public weather records
4. **Threshold-based** — eliminates ambiguity and subjective interpretation

---

## AI/ML Integration in Workflow

### Where AI/ML Fits in the Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                    AI/ML INTEGRATION MAP                             │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 1. RISK SCORING │  Scikit-learn Random Forest                    │
│  │    (Enrollment)  │  → Predicts user risk based on zone,          │
│  │                  │    history, platform, seasonal patterns        │
│  └─────────────────┘                                                │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 2. TRIGGER      │  LLM (Groq/LLaMA) + Rule Engine               │
│  │    DETECTION     │  → Analyzes multi-source data to confirm      │
│  │                  │    disruption with reasoning chain             │
│  └─────────────────┘                                                │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 3. FRAUD        │  Isolation Forest + Behavioral Analysis        │
│  │    DETECTION     │  → Anomaly detection on claim patterns,       │
│  │                  │    GPS spoofing detection, velocity checks     │
│  └─────────────────┘                                                │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 4. PAYOUT       │  Statistical Regression Model                  │
│  │    CALCULATION   │  → Income loss estimation based on            │
│  │                  │    historical earnings, zone density,          │
│  │                  │    disruption severity                         │
│  └─────────────────┘                                                │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 5. PREMIUM      │  Dynamic Pricing Algorithm                     │
│  │    OPTIMIZATION  │  → Adjusts weekly premiums based on           │
│  │                  │    claims ratio, zone risk evolution,          │
│  │                  │    user behavior scoring                       │
│  └─────────────────┘                                                │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ 6. LANGGRAPH    │  Multi-Agent Orchestration                     │
│  │    ORCHESTRATOR  │  → LLM-powered decision routing,             │
│  │                  │    reasoning chains, state management          │
│  └─────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────┘
```

### ML Models Used

| Model | Algorithm | Purpose | Input Features |
|---|---|---|---|
| **Risk Scorer** | Random Forest Classifier | Predict user risk level at enrollment | Zone history, platform, registration age, location |
| **Fraud Detector** | Isolation Forest | Detect anomalous claim patterns | Claim frequency, GPS consistency, time patterns, amount patterns |
| **Income Estimator** | Gradient Boosting Regressor | Predict income loss from disruption | Zone density, time of day, severity, historical orders |
| **Premium Optimizer** | Multi-armed Bandit | Optimize premium pricing dynamically | Claims ratio, zone evolution, user retention |
| **LLM Reasoner** | Groq LLaMA 3.1 via LangChain | Natural language reasoning for edge cases | Full claim context, validation results |

---

## Intelligent Fraud Detection & Adversarial Defense

### Multi-Layer Fraud Detection

```
Layer 1: RULE-BASED CHECKS
  ├── Policy active? (instant reject if not)
  ├── User in declared zone? (GPS vs warehouse radius)
  ├── Claim within disruption window? (±30 min tolerance)
  ├── Duplicate claim check (same user + same event)
  └── Weekly claim limit check (max 3/week)

Layer 2: ML-BASED ANOMALY DETECTION
  ├── Isolation Forest on claim patterns
  ├── Velocity check (claims per hour across users)
  ├── GPS trajectory analysis (stationary vs moving)
  ├── Cross-user correlation (ring detection)
  └── Behavioral deviation score

Layer 3: LLM-POWERED REASONING
  ├── Natural language analysis of edge cases
  ├── Context-aware decision making
  ├── Explanation generation for audit trail
  └── Admin-reviewable reasoning chains
```

### Validation Pipeline

```python
class ValidationResult(BaseModel):
    policy_valid: bool         # Active weekly policy exists
    location_valid: bool       # User within warehouse service radius
    time_valid: bool           # User was active during disruption window
    activity_valid: bool       # User had recent delivery activity
    warehouse_proximity: bool  # Warehouse was operational
    zone_activity_valid: bool  # Zone had normal activity before disruption
    fraud_check_passed: bool   # ML fraud score below threshold
    duplicate_check: bool      # No duplicate claim for same event
    overall_valid: bool        # ALL checks must pass
    rejection_reasons: List[str]  # Audit trail
    confidence_score: float    # 0.0 to 1.0
```

---

## Adversarial Defense & Anti-Spoofing Strategy

### The Threat Landscape

In a scenario with **500 delivery partners**, **fake GPS**, and a **coordinated fraud ring**, simple GPS verification is not enough. Here's our multi-layered defense:

### 1. GPS Spoofing Detection

**The Problem:** Fraudsters use GPS spoofing apps to fake their location inside a delivery zone.

**Our Defense:**

| Signal | What We Check | How It Catches Fakers |
|---|---|---|
| **GPS Consistency Score** | Compare GPS location with cell tower triangulation and Wi-Fi BSSID | Spoofed GPS won't match network-level location |
| **Location Source Validation** | Flag `source: "mock"` in GPS data; check Android `isMockLocationEnabled` | Direct detection of mock location providers |
| **Movement Trajectory Analysis** | Real riders show continuous movement patterns; spoofers show teleportation | Impossible jumps (e.g., 5km in 10 seconds) flagged |
| **Platform API Cross-Reference** | Verify location against delivery platform's own rider tracking | If Zepto shows rider at Location A but claim says Location B → fraud |

```
Honest Rider GPS:    A → B → C → D → E  (smooth trajectory, consistent speed)
Spoofer GPS:         A → → → → → X       (teleport to zone, then static)
```

### 2. Coordinated Fraud Ring Detection

**The Problem:** A group files simultaneous fake claims across multiple accounts to drain the liquidity pool.

**Our Defense:**

| Signal | Detection Method | Why It Works |
|---|---|---|
| **Temporal Clustering** | Flag when >N claims arrive within T minutes from same zone | Organic claims are distributed; coordinated attacks cluster |
| **Device Fingerprinting** | Track device ID, IP address, app version | Multiple accounts from same device = fraud ring |
| **Behavioral Similarity** | Cluster analysis on claim timing, amounts, GPS patterns | Ring members show eerily similar behavior patterns |
| **Social Graph Analysis** | Map connections: shared devices, same Wi-Fi, sequential registration | Fraud rings leave network traces |
| **Velocity Anomaly** | Zone-level claim rate vs historical baseline | 30 claims in 10 min from a zone that averages 2/hour → alert |

```python
def detect_fraud_ring(claims_batch: List[Claim]) -> FraudAlert:
    """Cross-claim correlation analysis"""
    # Temporal clustering: too many claims in short window
    time_window = timedelta(minutes=15)
    zone_claims = group_by_zone(claims_batch, time_window)

    for zone, claims in zone_claims.items():
        if len(claims) > zone.historical_avg * 3:
            # Anomalous spike — investigate further
            device_overlap = check_device_fingerprints(claims)
            behavioral_sim = compute_behavioral_similarity(claims)
            if device_overlap > 0.3 or behavioral_sim > 0.8:
                return FraudAlert(type="RING_DETECTED", confidence=0.95)
    return None
```

### 3. Distinguishing Genuine vs. Fraudulent Claims

**The Core Question:** How do you spot the faker without punishing the genuinely stranded worker?

**Our Three-Tier Approach:**

#### Tier 1: Objective Ground Truth (Cannot Be Faked)
| Data Point | Source | Why Trustworthy |
|---|---|---|
| Weather at zone | OpenWeatherMap API (3rd party) | Independently verifiable, not user-reported |
| Warehouse operational status | Platform API (Zepto/Blinkit) | Platform has no incentive to lie |
| Historical order volume | Platform analytics | Baseline establishes expected disruption impact |
| AQI reading | Government CPCB API | Public, auditable data |

#### Tier 2: Behavioral Fingerprint (Hard to Fake Consistently)
| Signal | Honest Rider | Fraudster |
|---|---|---|
| **Pre-disruption activity** | Was actively delivering orders before rain started | No delivery history in the hours before claim |
| **Location continuity** | GPS shows them in zone for hours | Appears in zone only at claim time |
| **Claim timing** | Claims during or shortly after disruption | Claims hours after disruption ended |
| **Historical pattern** | Claims correlate with actual weather events in their zone | Claims with every minor weather event, across multiple zones |
| **Earnings consistency** | Claimed loss aligns with their typical daily earnings | Claimed loss is suspiciously high or uniform |

#### Tier 3: Statistical Anomaly Detection (Catches What Rules Miss)

```python
from sklearn.ensemble import IsolationForest

# Features for each claim
features = [
    'claim_frequency_30d',        # How often this user claims
    'avg_time_to_claim',          # How quickly they claim after event
    'gps_consistency_score',      # GPS vs network location match
    'pre_event_activity_hours',   # Hours active before disruption
    'zone_hop_count_7d',          # How many zones they claim from
    'device_account_ratio',       # Accounts per device
    'payout_to_premium_ratio',    # ROI on their premiums
    'behavioral_cluster_id',      # Which behavior cluster they belong to
]

fraud_model = IsolationForest(contamination=0.05)
# Score: -1 = anomaly (likely fraud), 1 = normal (likely genuine)
```

### 4. Anti-Spoofing Without Punishing Honest Users

**Key Principle:** Every rejection gets a **reason code** and an **appeal path**.

```
┌────────────────────────────────────────────────────────────────┐
│                   DECISION MATRIX                              │
│                                                                │
│  Fraud Score < 0.3  → AUTO-APPROVE (90% of claims)           │
│  Fraud Score 0.3-0.7 → HUMAN REVIEW (admin dashboard)        │
│  Fraud Score > 0.7  → AUTO-REJECT with reason + appeal       │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  SAFETY NETS FOR HONEST RIDERS:                      │     │
│  │                                                      │     │
│  │  ✓ Benefit of doubt on first claim (lower threshold) │     │
│  │  ✓ Appeal mechanism with admin manual override       │     │
│  │  ✓ Transparent rejection reasons in rider app        │     │
│  │  ✓ Trust score builds over time (more claims =       │     │
│  │    higher trust if consistently legitimate)           │     │
│  │  ✓ Grace period for new users (first 2 weeks)       │     │
│  │  ✓ Zone-level validation before user-level           │     │
│  │    (if weather data confirms disruption, lean toward  │     │
│  │    approval even if individual signals are noisy)     │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
```

### 5. Liquidity Pool Protection

Against a coordinated attack that tries to drain the pool:

| Defense | Mechanism |
|---|---|
| **Rate Limiting** | Max 3 payouts/user/week, max ₹2000/user/week |
| **Zone-Level Circuit Breaker** | If zone payouts exceed 3× daily average, pause and escalate to admin |
| **Pool Reserve** | 20% of premiums held in reserve, not available for immediate payout |
| **Progressive Payouts** | Large clusters trigger delayed payout (2hr hold) for human review |
| **Reinsurance Trigger** | If total payouts exceed 80% of pool in 24hrs, halt auto-payouts |

### Summary: Defense-in-Depth

```
Layer 1: Data Integrity      → Third-party weather/platform APIs (unfakeable)
Layer 2: Location Validation  → GPS + cell tower + Wi-Fi + platform cross-check
Layer 3: Behavioral Analysis  → Pre-event activity, trajectory, timing patterns
Layer 4: ML Anomaly Detection → Isolation Forest catches novel fraud patterns
Layer 5: Ring Detection       → Cross-user correlation, device fingerprinting
Layer 6: LLM Reasoning        → Edge case analysis with explainable decisions
Layer 7: Human Oversight      → Admin dashboard for flagged cases
Layer 8: Financial Controls   → Rate limits, circuit breakers, pool reserves
```

---

## Platform Decision: Web + Mobile

### Why Both?

| Platform | User | Justification |
|---|---|---|
| **Mobile PWA** | Delivery Partners | Riders are always on mobile; PWA works offline, no app store needed, lightweight (<2MB) |
| **Web Dashboard** | Admins & Insurers | Complex analytics, fraud review, bulk operations need large screens |

### Mobile (Progressive Web App) for Riders

- **Offline-first**: Caches policy status, shows last payout even without connectivity
- **Push notifications**: Instant payout alerts, policy renewal reminders
- **Lightweight**: No app store installation barrier, works on low-end Android devices
- **Location-aware**: Background GPS for activity validation (with consent)
- **Multi-language**: Hindi, English, regional languages for tier-2/3 city riders

### Web Dashboard for Admins/Insurers

- **Real-time monitoring**: Live map of active zones, disruption events, claim flow
- **Fraud review queue**: Flagged claims with full context, one-click approve/reject
- **Analytics**: Premium vs payout ratio, zone risk heatmaps, fraud trend analysis
- **Bulk operations**: Mass policy generation, zone configuration, premium adjustments
- **Audit trail**: Complete decision history with LLM reasoning chains

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Core language with type hints |
| **FastAPI** | High-performance async REST API |
| **LangGraph** | Multi-agent graph orchestration for claim processing |
| **LangChain + Groq** | LLM integration (LLaMA 3.1 for reasoning) |
| **Scikit-learn** | ML models (Isolation Forest, Random Forest, Gradient Boosting) |
| **SQLAlchemy + Alembic** | ORM + database migrations |
| **APScheduler** | Periodic weather monitoring cron jobs |
| **Pydantic** | Data validation and serialization |
| **Tenacity** | Retry logic for payment processing |
| **Loguru** | Structured logging for audit trails |
| **Geopy + Shapely** | Geospatial calculations (zone radius, distance) |

### Frontend

| Technology | Purpose |
|---|---|
| **React 18** | Component-based UI |
| **Plotly.js** | Interactive charts for analytics dashboard |
| **Leaflet/Mapbox** | Zone visualization and live maps |
| **PWA (Service Workers)** | Offline support for rider mobile app |

### Infrastructure

| Technology | Purpose |
|---|---|
| **SQLite** | Development database |
| **PostgreSQL** | Production database |
| **OpenWeatherMap API** | Real-time weather data |
| **UPI/Razorpay (sandbox)** | Payment processing |

### Project Structure

```
guidewire-insur/
├── src/
│   ├── agents/            # LangGraph agent nodes
│   │   ├── claims/        # Claim processing agent
│   │   ├── fraud/         # Fraud detection agent
│   │   ├── orchestrator/  # Main graph orchestrator
│   │   ├── payout/        # Payout calculation agent
│   │   ├── risk/          # Risk assessment agent
│   │   └── weather/       # Weather data ingestion agent
│   ├── api/               # FastAPI routes + middleware
│   │   ├── middleware/     # Auth, rate limiting
│   │   └── routes/        # REST endpoints
│   ├── config/            # Settings and environment
│   ├── graphs/            # LangGraph definitions
│   │   ├── decision/      # Decision routing logic
│   │   ├── fraud_detection/ # Fraud detection graph
│   │   └── validation/    # Multi-layer validation graph
│   ├── models/            # Pydantic schemas + DB models
│   ├── services/          # Business logic services
│   │   ├── delivery/      # Platform API integration
│   │   ├── location/      # Geospatial services
│   │   ├── payment/       # Payment gateway integration
│   │   └── weather/       # Weather API service
│   └── utils/             # Shared utilities
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── pages/         # Page components
│   │   └── utils/         # Frontend utilities
│   └── public/            # Static assets
├── tests/                 # Pytest test suite
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── CLAUDE.md             # AI assistant instructions
```

---

## Development Plan

### Phase 1: Foundation (Day 1)
- [x] Project structure and schemas (Pydantic models)
- [x] FastAPI backend skeleton with auth middleware
- [x] Database models (SQLAlchemy + SQLite)
- [x] Weather API integration (OpenWeatherMap)
- [x] Basic React dashboard setup

### Phase 2: Core Engine (Day 2)
- [x] LangGraph StateGraph implementation
- [x] Data Ingestion agent node
- [x] Disruption Detection agent node
- [x] Fraud & Eligibility Validation agent node
- [x] Actuarial Engine (payout calculation)
- [x] Weekly premium pricing model

### Phase 3: Intelligence Layer (Day 3)
- [x] ML fraud detection (Isolation Forest)
- [x] Risk scoring model (Random Forest)
- [x] LLM reasoning integration (Groq/LangChain)
- [x] Multi-layer validation pipeline
- [x] GPS spoofing detection logic

### Phase 4: Integration & Polish (Day 4)
- [x] End-to-end claim processing flow
- [x] Admin dashboard with fraud review queue
- [x] Payment processing (mock/sandbox)
- [x] Comprehensive test scenarios
- [x] Demo video recording

---

## Scenario Coverage

Our system handles all 20 defined scenarios:

| # | Scenario | Outcome | Validation Layers Involved |
|---|---|---|---|
| 1 | Valid claim (heavy rain) | **Approved** | Policy ✓ Location ✓ Time ✓ Activity ✓ |
| 2 | User opens app after disruption | **Rejected** | Time validation fails |
| 3 | User outside delivery zone | **Rejected** | Location validation fails |
| 4 | No active policy | **Rejected** | Policy validation fails |
| 5 | Low activity zone | **Reduced payout** | Zone activity → reduced severity |
| 6 | Frequent claims (fraud) | **Flagged/Rejected** | ML fraud score exceeds threshold |
| 7 | Fake location (GPS spoof) | **Rejected** | GPS consistency check fails |
| 8 | Warehouse inactive | **Rejected** | Warehouse proximity validation fails |
| 9 | Partial impact | **Reduced payout** | Severity-based proportional calculation |
| 10 | Multiple users same zone | **All approved** | Zone-wide trigger, individual validation |
| 11 | High risk zone user | **Approved, higher premium** | Risk factor → premium adjustment |
| 12 | Safe zone user | **Approved, lower premium** | Lower risk → lower premium |
| 13 | System failure retry | **Auto-retry** | Tenacity retry with exponential backoff |
| 14 | Admin manual override | **Override applied** | Admin dashboard escalation |
| 15 | Multi-trigger event | **Higher payout** | Compounded severity calculation |
| 16 | User partially active | **Proportional payout** | Activity hours × loss rate |
| 17 | Zone closure (social disruption) | **Approved** | Govt alert trigger |
| 18 | App downtime | **Approved** | Platform health API trigger |
| 19 | Maximum limit reached | **Rejected** | Weekly cap enforcement |
| 20 | New user (no history) | **Approved (reduced)** | Grace period, lower initial payout |

---

## 2-Minute Demo Video

### [Watch the Demo Video](InShot_20260320_232335057.mp4)

### Video Structure

| Timestamp | Content |
|---|---|
| **0:00 - 0:20** | Problem statement: Why delivery partners need parametric insurance |
| **0:20 - 0:40** | Architecture overview: LangGraph agent orchestration flow |
| **0:40 - 1:10** | Live demo: Trigger detection → Validation → Auto-payout |
| **1:10 - 1:30** | Fraud detection: GPS spoofing caught, fraud ring detected |
| **1:30 - 1:50** | Admin dashboard: Real-time monitoring, manual override |
| **1:50 - 2:00** | Impact: Faster payouts, reduced fraud, scalable architecture |

### Strategy & Plan of Execution

**Strategy:** Build a trust-first parametric insurance system where the *default is to pay honest riders fast*, and fraud detection works in the background to catch bad actors without creating friction for legitimate users.

**Execution Plan:**
1. **Data-first approach** — Start with reliable external data sources (weather, platform APIs) that establish ground truth
2. **Layer defenses** — Each validation layer adds confidence; no single layer is a single point of failure
3. **AI for edge cases** — Rules handle 90% of cases; ML catches anomalies; LLM reasons about the remaining edge cases
4. **Human in the loop** — Admin override for flagged cases preserves fairness
5. **Continuous learning** — Every approved/rejected claim improves the fraud model

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/shan52100/guidewire-teamHATS.git
cd guidewire-teamHATS

# Install backend dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys:
#   GROQ_API_KEY=your_groq_key
#   WEATHER_API_KEY=your_openweathermap_key

# Start backend
python -m uvicorn src.api.main:app --reload

# In a new terminal, start frontend
cd frontend && npm install && npm start
```

### Running Tests

```bash
python -m pytest tests/ -v --cov=src
```

---

## Team HATS

Built with passion for the **Guidewire Hackathon 2026**.

| Member | Role |
|---|---|
| **H** | Backend & AI/ML Pipeline |
| **A** | LangGraph Agent Orchestration |
| **T** | Frontend & Dashboard |
| **S** | Integration & Testing |

---

<p align="center">
  <b>InsureFlow AI</b> — Because gig workers deserve instant, fair, automated insurance.
</p>
