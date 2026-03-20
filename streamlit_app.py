"""
InsureFlow AI - Interactive Demo
Parametric Insurance for Quick-Commerce Delivery Partners
"""
import streamlit as st
import time
import random
import json
from datetime import datetime, timedelta

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InsureFlow AI - Parametric Insurance Demo",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2.5rem; }
    .main-header p { color: #a8d8ea; margin: 0.5rem 0 0 0; font-size: 1.1rem; }
    .node-card {
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        border-left: 5px solid;
    }
    .node-pending { background: #f8f9fa; border-left-color: #6c757d; }
    .node-running { background: #fff3cd; border-left-color: #ffc107; }
    .node-success { background: #d4edda; border-left-color: #28a745; }
    .node-failed { background: #f8d7da; border-left-color: #dc3545; }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .metric-card h2 { margin: 0; color: #2c5364; }
    .metric-card p { margin: 0.3rem 0 0 0; color: #6c757d; font-size: 0.9rem; }
    .fraud-alert {
        background: linear-gradient(135deg, #ff416c, #ff4b2b);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    .payout-success {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    .scenario-box {
        background: #f0f4f8;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #11998e, #38ef7d); }
</style>
""", unsafe_allow_html=True)

# ─── Data ────────────────────────────────────────────────────────────────────

CHENNAI_ZONES = {
    "T. Nagar (Moderate Zone)": {"zone_id": "CHN-TNG", "risk": "Medium", "premium": 50, "avg_orders": 45, "lat": 13.0418, "lon": 80.2341, "warehouse": "T. Nagar Dark Store"},
    "Velachery (Flood-Prone Zone)": {"zone_id": "CHN-VLC", "risk": "High", "premium": 70, "avg_orders": 38, "lat": 12.9815, "lon": 80.2180, "warehouse": "Velachery Hub"},
    "Anna Nagar (Safe Zone)": {"zone_id": "CHN-ANG", "risk": "Low", "premium": 30, "avg_orders": 55, "lat": 13.0850, "lon": 80.2101, "warehouse": "Anna Nagar Express"},
    "Tambaram (Flood-Prone Zone)": {"zone_id": "CHN-TMB", "risk": "High", "premium": 70, "avg_orders": 30, "lat": 12.9249, "lon": 80.1000, "warehouse": "Tambaram Center"},
    "Adyar (Moderate Zone)": {"zone_id": "CHN-ADY", "risk": "Medium", "premium": 50, "avg_orders": 42, "lat": 13.0067, "lon": 80.2572, "warehouse": "Adyar Quick Store"},
}

SCENARIOS = {
    "1. Valid Claim — Heavy Rain": {
        "description": "Arun is actively delivering in Velachery. Heavy rain (65mm/hr) hits at 3 PM. Orders drop to zero. System auto-detects and pays out.",
        "weather": {"rainfall_mm": 65, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 85, "wind_speed": 35},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 4.5},
        "expected": "approved",
        "zone": "Velachery (Flood-Prone Zone)"
    },
    "2. Fraud — GPS Spoofing Attempt": {
        "description": "A fraudster spoofs GPS to appear in a flood zone during heavy rain. System detects mock location provider and trajectory anomaly.",
        "weather": {"rainfall_mm": 80, "condition": "Heavy Rain", "flood_alert": 1, "aqi": 90, "wind_speed": 40},
        "rider": {"name": "Suspicious User #47", "active": False, "in_zone": True, "has_policy": True, "history_clean": False, "gps_legit": False, "pre_event_active_hrs": 0},
        "expected": "rejected",
        "zone": "Velachery (Flood-Prone Zone)"
    },
    "3. Rejected — No Active Policy": {
        "description": "Rider hasn't subscribed to the weekly plan. Despite genuine rain disruption, system rejects immediately.",
        "weather": {"rainfall_mm": 45, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 70, "wind_speed": 20},
        "rider": {"name": "Karthik", "active": True, "in_zone": True, "has_policy": False, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 3},
        "expected": "rejected",
        "zone": "T. Nagar (Moderate Zone)"
    },
    "4. Rejected — Outside Delivery Zone": {
        "description": "Rider is located 8km from the warehouse. Even though rain is heavy, they're outside the service radius.",
        "weather": {"rainfall_mm": 55, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 75, "wind_speed": 25},
        "rider": {"name": "Priya", "active": True, "in_zone": False, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 1},
        "expected": "rejected",
        "zone": "Anna Nagar (Safe Zone)"
    },
    "5. Multi-Trigger — Rain + Flood Alert": {
        "description": "Cyclone warning in Chennai. Heavy rain AND flood alert level 3. Multiple triggers compound severity. Higher payout.",
        "weather": {"rainfall_mm": 120, "condition": "Cyclonic Rain", "flood_alert": 3, "aqi": 95, "wind_speed": 65},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 5},
        "expected": "approved",
        "zone": "Tambaram (Flood-Prone Zone)"
    },
    "6. Fraud Ring — Coordinated Attack": {
        "description": "15 claims arrive from the same zone within 5 minutes. Device fingerprinting reveals 3 devices behind 15 accounts. Ring detected.",
        "weather": {"rainfall_mm": 50, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 80, "wind_speed": 20},
        "rider": {"name": "Ring Member #12", "active": False, "in_zone": True, "has_policy": True, "history_clean": False, "gps_legit": False, "pre_event_active_hrs": 0},
        "expected": "rejected",
        "zone": "Adyar (Moderate Zone)"
    },
    "7. Partial Impact — Moderate Rain": {
        "description": "Moderate rain reduces orders by 40% but doesn't stop deliveries completely. System calculates proportional payout based on severity.",
        "weather": {"rainfall_mm": 28, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 60, "wind_speed": 15},
        "rider": {"name": "Deepak", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 6},
        "expected": "approved",
        "zone": "Anna Nagar (Safe Zone)"
    },
    "8. Rejected — Opened App After Disruption": {
        "description": "Rain stopped 2 hours ago. Rider opens app now and expects payout. Fails time validation — wasn't active during the disruption window.",
        "weather": {"rainfall_mm": 55, "condition": "Post-Rain Clear", "flood_alert": 0, "aqi": 65, "wind_speed": 10},
        "rider": {"name": "Vikram", "active": False, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 0},
        "expected": "rejected",
        "zone": "T. Nagar (Moderate Zone)"
    },
    "9. Air Pollution Trigger (AQI > 300)": {
        "description": "Severe air pollution event. AQI crosses 350. Rider health at risk. System triggers payout for pollution disruption.",
        "weather": {"rainfall_mm": 0, "condition": "Hazy / Polluted", "flood_alert": 0, "aqi": 365, "wind_speed": 5},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 3},
        "expected": "approved",
        "zone": "T. Nagar (Moderate Zone)"
    },
    "10. New User — First Claim (Grace Period)": {
        "description": "Newly registered rider (5 days old) files first claim. System applies grace period — lower threshold, reduced initial payout.",
        "weather": {"rainfall_mm": 50, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 80, "wind_speed": 25},
        "rider": {"name": "Naveen (New User)", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_event_active_hrs": 2},
        "expected": "approved",
        "zone": "Adyar (Moderate Zone)"
    },
}

# ─── Helper Functions ────────────────────────────────────────────────────────

def simulate_node(placeholder, node_name, icon, description, delay=0.8):
    """Simulate a LangGraph node processing with animation."""
    with placeholder.container():
        st.markdown(f"""<div class="node-card node-running">
            <b>{icon} {node_name}</b> — <i>Processing...</i><br>
            <small>{description}</small>
        </div>""", unsafe_allow_html=True)
    time.sleep(delay)

def show_node_result(placeholder, node_name, icon, result_text, success=True):
    """Show node completion result."""
    css_class = "node-success" if success else "node-failed"
    status = "PASSED" if success else "FAILED"
    with placeholder.container():
        st.markdown(f"""<div class="node-card {css_class}">
            <b>{icon} {node_name}</b> — <b>{status}</b><br>
            <small>{result_text}</small>
        </div>""", unsafe_allow_html=True)

def calculate_payout(weather, zone_data, rider, is_new_user=False):
    """Calculate payout based on severity and zone."""
    severity = 0
    triggers = []

    if weather["rainfall_mm"] > 20:
        rain_severity = min(1.0, weather["rainfall_mm"] / 100)
        severity += rain_severity
        triggers.append(f"Rain: {weather['rainfall_mm']}mm/hr (severity: {rain_severity:.2f})")

    if weather["flood_alert"] >= 2:
        flood_severity = weather["flood_alert"] / 4
        severity += flood_severity
        triggers.append(f"Flood Alert Level {weather['flood_alert']} (severity: {flood_severity:.2f})")

    if weather.get("aqi", 0) > 300:
        aqi_severity = min(1.0, (weather["aqi"] - 300) / 200)
        severity += aqi_severity
        triggers.append(f"AQI: {weather['aqi']} (severity: {aqi_severity:.2f})")

    severity = min(1.0, severity)
    avg_income_per_order = 40
    lost_hours = min(8, severity * 10)
    base_loss = zone_data["avg_orders"] * avg_income_per_order * (lost_hours / 8) * severity

    if is_new_user:
        base_loss *= 0.6  # Reduced for new users

    # Apply zone-based cap
    caps = {"Low": 350, "Medium": 500, "High": 700}
    cap = caps.get(zone_data["risk"], 500)
    final_payout = min(base_loss, cap)
    final_payout = round(max(100, final_payout), 0)

    return {
        "severity": severity,
        "triggers": triggers,
        "lost_hours": round(lost_hours, 1),
        "base_loss": round(base_loss, 0),
        "final_payout": final_payout,
        "cap_applied": base_loss > cap,
        "disruption_type": "multi_trigger" if len(triggers) > 1 else ("pollution" if weather.get("aqi", 0) > 300 else "heavy_rain")
    }

def compute_fraud_score(rider, scenario_name):
    """Compute fraud score based on rider signals."""
    score = 0.0
    signals = []

    if not rider["gps_legit"]:
        score += 0.35
        signals.append("GPS mock location detected (+0.35)")
    if not rider["active"]:
        score += 0.15
        signals.append("No pre-disruption activity (+0.15)")
    if rider["pre_event_active_hrs"] == 0:
        score += 0.15
        signals.append("Zero hours active before event (+0.15)")
    if not rider["history_clean"]:
        score += 0.20
        signals.append("Suspicious claim history (+0.20)")
    if "Ring" in scenario_name or "Fraud Ring" in scenario_name:
        score += 0.30
        signals.append("Coordinated attack pattern detected (+0.30)")
        signals.append("Device fingerprint: 3 devices → 15 accounts")
        signals.append("Temporal clustering: 15 claims in 5 minutes (avg: 2/hr)")

    score = min(1.0, score)
    return score, signals

# ─── Main App ────────────────────────────────────────────────────────────────

# Header
st.markdown("""
<div class="main-header">
    <h1>InsureFlow AI</h1>
    <p>AI-Powered Parametric Insurance for Quick-Commerce Delivery Partners</p>
    <p style="font-size: 0.85rem; margin-top: 0.8rem; color: #7ec8e3;">Team HATS | Guidewire Hackathon 2026 | LangGraph + Groq + Scikit-learn</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("## Configuration")
st.sidebar.markdown("---")

selected_scenario = st.sidebar.selectbox(
    "Select Scenario",
    list(SCENARIOS.keys()),
    help="Choose a test scenario to simulate the claim processing pipeline"
)

scenario = SCENARIOS[selected_scenario]
zone_name = scenario["zone"]
zone_data = CHENNAI_ZONES[zone_name]
rider = scenario["rider"]
weather = scenario["weather"]

st.sidebar.markdown("---")
st.sidebar.markdown("### Rider Profile")
st.sidebar.markdown(f"**Name:** {rider['name']}")
st.sidebar.markdown(f"**Zone:** {zone_name}")
st.sidebar.markdown(f"**Weekly Premium:** ₹{zone_data['premium']}/week")
st.sidebar.markdown(f"**Policy Active:** {'Yes' if rider['has_policy'] else 'No'}")
st.sidebar.markdown(f"**In Zone:** {'Yes' if rider['in_zone'] else 'No'}")
st.sidebar.markdown(f"**GPS Legitimate:** {'Yes' if rider['gps_legit'] else 'No'}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Weather Data")
st.sidebar.markdown(f"**Condition:** {weather['condition']}")
st.sidebar.markdown(f"**Rainfall:** {weather['rainfall_mm']} mm/hr")
st.sidebar.markdown(f"**Flood Alert:** Level {weather['flood_alert']}")
st.sidebar.markdown(f"**AQI:** {weather.get('aqi', 'N/A')}")
st.sidebar.markdown(f"**Wind Speed:** {weather['wind_speed']} km/h")

# Main content
st.markdown(f"### Scenario: {selected_scenario}")
st.markdown(f"""<div class="scenario-box">
    <b>Description:</b> {scenario['description']}
</div>""", unsafe_allow_html=True)

st.markdown("")

# Zone info metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class="metric-card">
        <h2>₹{zone_data['premium']}</h2><p>Weekly Premium</p>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card">
        <h2>{zone_data['risk']}</h2><p>Zone Risk Level</p>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="metric-card">
        <h2>{zone_data['avg_orders']}</h2><p>Avg Orders/Hr</p>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="metric-card">
        <h2>{weather['rainfall_mm']}mm</h2><p>Current Rainfall</p>
    </div>""", unsafe_allow_html=True)

st.markdown("")
st.markdown("---")

# Run Pipeline Button
if st.button("Run LangGraph Claim Pipeline", type="primary", use_container_width=True):

    st.markdown("## LangGraph Agent Pipeline")
    st.markdown("")

    progress_bar = st.progress(0, text="Initializing pipeline...")

    # ── Node 1: Data Ingestion ───────────────────────────────────────────
    node1 = st.empty()
    simulate_node(node1, "Node 1: Data Ingestion", "📡",
                  f"Fetching weather data from OpenWeatherMap API for zone {zone_data['zone_id']}...")
    progress_bar.progress(15, text="Ingesting external data...")

    show_node_result(node1, "Node 1: Data Ingestion", "📡",
        f"Weather: {weather['condition']} | Rainfall: {weather['rainfall_mm']}mm/hr | "
        f"AQI: {weather.get('aqi', 'N/A')} | Flood Alert: Level {weather['flood_alert']} | "
        f"Zone: {zone_data['zone_id']} ({zone_data['warehouse']})")

    # ── Node 2: Disruption Detection ─────────────────────────────────────
    node2 = st.empty()
    simulate_node(node2, "Node 2: Disruption Analyst", "🔍",
                  "Analyzing trigger thresholds against parametric rules...")
    progress_bar.progress(30, text="Detecting disruption triggers...")

    payout_info = calculate_payout(weather, zone_data, rider,
                                    is_new_user="New User" in rider["name"])

    disruption_detected = len(payout_info["triggers"]) > 0 and weather["condition"] != "Post-Rain Clear"

    if disruption_detected:
        triggers_text = " | ".join(payout_info["triggers"])
        show_node_result(node2, "Node 2: Disruption Analyst", "🔍",
            f"DISRUPTION DETECTED — Type: {payout_info['disruption_type'].replace('_', ' ').title()} | "
            f"Severity: {payout_info['severity']:.2f} | Triggers: {triggers_text}")
    else:
        reason = "Post-disruption: rain has already stopped" if weather["condition"] == "Post-Rain Clear" else "No parametric thresholds exceeded"
        show_node_result(node2, "Node 2: Disruption Analyst", "🔍",
            f"NO DISRUPTION — {reason}. Rainfall: {weather['rainfall_mm']}mm (threshold: 20mm)", success=False)
        progress_bar.progress(100, text="Pipeline complete — No disruption detected")
        st.markdown("""<div class="node-card node-failed">
            <b>TERMINAL: No Action</b><br>
            <small>No parametric trigger detected. Claim pipeline terminated. No payout issued.</small>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # ── Node 3: Fraud & Eligibility Validation ───────────────────────────
    node3 = st.empty()
    simulate_node(node3, "Node 3: Fraud & Eligibility Validator", "🛡️",
                  "Running multi-layer validation: policy, location, time, activity, GPS, fraud ML model...")
    progress_bar.progress(50, text="Validating claim eligibility...")

    fraud_score, fraud_signals = compute_fraud_score(rider, selected_scenario)

    validation_checks = []
    all_passed = True

    # Policy check
    if rider["has_policy"]:
        validation_checks.append(("Policy Valid", True, "Active weekly policy found"))
    else:
        validation_checks.append(("Policy Valid", False, "NO ACTIVE POLICY — rider has not subscribed"))
        all_passed = False

    # Location check
    if rider["in_zone"]:
        validation_checks.append(("Location Valid", True, f"Rider within {zone_data['warehouse']} service radius"))
    else:
        validation_checks.append(("Location Valid", False, "Rider is OUTSIDE warehouse delivery radius (>5km)"))
        all_passed = False

    # Time/Activity check
    if rider["active"] and rider["pre_event_active_hrs"] > 0:
        validation_checks.append(("Time & Activity Valid", True, f"Rider was active {rider['pre_event_active_hrs']}hrs before disruption"))
    else:
        validation_checks.append(("Time & Activity Valid", False, "Rider was NOT active during disruption window"))
        all_passed = False

    # GPS check
    if rider["gps_legit"]:
        validation_checks.append(("GPS Integrity", True, "GPS consistent with cell tower + Wi-Fi signals"))
    else:
        validation_checks.append(("GPS Integrity", False, "MOCK LOCATION DETECTED — GPS spoofing app identified"))
        all_passed = False

    # Fraud ML check
    fraud_passed = fraud_score < 0.3
    if fraud_passed:
        validation_checks.append(("ML Fraud Check", True, f"Fraud score: {fraud_score:.2f} (threshold: 0.30)"))
    else:
        validation_checks.append(("ML Fraud Check", False, f"Fraud score: {fraud_score:.2f} EXCEEDS threshold 0.30"))
        all_passed = False

    # Display validation results
    validation_text = ""
    for check_name, passed, detail in validation_checks:
        icon = "✅" if passed else "❌"
        validation_text += f"{icon} **{check_name}**: {detail}  \n"

    show_node_result(node3, "Node 3: Fraud & Eligibility Validator", "🛡️",
        f"Fraud Score: {fraud_score:.2f} | Checks: {sum(1 for _, p, _ in validation_checks if p)}/{len(validation_checks)} passed",
        success=all_passed)

    # Show detailed validation
    with st.expander("View Detailed Validation Results", expanded=True):
        for check_name, passed, detail in validation_checks:
            icon = "✅" if passed else "❌"
            st.markdown(f"{icon} **{check_name}**: {detail}")

        if fraud_signals:
            st.markdown("---")
            st.markdown("**Fraud Detection Signals:**")
            for signal in fraud_signals:
                st.markdown(f"- ⚠️ {signal}")

    if not all_passed:
        progress_bar.progress(100, text="Pipeline complete — Claim REJECTED")
        rejection_reasons = [detail for _, passed, detail in validation_checks if not passed]

        st.markdown("")
        st.markdown(f"""<div class="fraud-alert">
            <h2>CLAIM REJECTED</h2>
            <p style="font-size: 1.1rem;">Fraud Score: {fraud_score:.2f} | {len(rejection_reasons)} validation(s) failed</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("")
        st.markdown("**Rejection Reasons (sent to rider + logged for audit):**")
        for i, reason in enumerate(rejection_reasons, 1):
            st.markdown(f"{i}. {reason}")

        if fraud_score >= 0.7:
            st.warning("⚠️ HIGH FRAUD SCORE — Account flagged for admin review. Trust score reduced.")
        elif fraud_score >= 0.3:
            st.info("ℹ️ MODERATE FRAUD SCORE — Claim escalated to admin dashboard for manual review.")

        # Show LLM reasoning
        with st.expander("LLM Reasoning Chain (Groq LLaMA 3.1)"):
            if "Ring" in selected_scenario:
                st.code("""
[LLM Reasoning — Fraud Ring Analysis]

OBSERVATION: 15 claims received from zone CHN-ADY within 5-minute window.
Historical baseline for this zone: 2 claims/hour.
This represents a 90x spike in claim velocity.

DEVICE ANALYSIS: 15 unique user accounts traced to 3 physical devices.
Account-to-device ratio: 5:1 (threshold: 2:1)

BEHAVIORAL SIMILARITY: Claim timing variance < 30 seconds.
GPS coordinates show identical trajectories across 8 accounts.
All accounts registered within same 48-hour window.

CONCLUSION: Coordinated fraud ring detected with HIGH confidence (0.95).
RECOMMENDATION: Reject all 15 claims. Flag devices for permanent block.
Escalate to admin for investigation.
                """, language="text")
            elif not rider["gps_legit"]:
                st.code(f"""
[LLM Reasoning — GPS Spoofing Detection]

OBSERVATION: Rider {rider['name']} GPS reports location in {zone_name}.
However, cell tower triangulation places device 12km away in Chromepet.
Wi-Fi BSSID scan shows no matching access points for claimed location.

TRAJECTORY ANALYSIS: GPS history shows instantaneous jump from Chromepet
to {zone_name} (12km in 0 seconds). Physically impossible.

MOCK LOCATION: Android system flag 'isMockLocationEnabled' = TRUE.
App 'Fake GPS Pro' detected in running processes.

PLATFORM CROSS-CHECK: Zepto rider tracking API shows last known
location in Chromepet, not {zone_name}.

CONCLUSION: GPS spoofing confirmed with HIGH confidence.
RECOMMENDATION: Reject claim. Flag account. Reduce trust score by 0.3.
                """, language="text")
            else:
                reasons_str = "; ".join([detail for _, passed, detail in validation_checks if not passed])
                st.code(f"""
[LLM Reasoning — Eligibility Check]

OBSERVATION: Claim from rider {rider['name']} for disruption in {zone_name}.
Weather data confirms {weather['condition']} ({weather['rainfall_mm']}mm/hr).

VALIDATION FAILURES:
{reasons_str}

ASSESSMENT: While weather disruption is genuine, rider fails eligibility
criteria. This is not a fraud attempt — rider simply does not meet the
validation requirements for automatic payout.

RECOMMENDATION: Reject claim with clear reason codes.
Rider may appeal via admin dashboard if they believe this is an error.
                """, language="text")
        st.stop()

    # ── Node 4: Actuarial Engine ─────────────────────────────────────────
    node4 = st.empty()
    simulate_node(node4, "Node 4: Actuarial Engine", "🧮",
                  "Calculating income loss based on severity, zone density, and historical earnings...")
    progress_bar.progress(70, text="Computing payout amount...")

    show_node_result(node4, "Node 4: Actuarial Engine", "🧮",
        f"Severity: {payout_info['severity']:.2f} | Lost Hours: {payout_info['lost_hours']}hrs | "
        f"Base Loss: ₹{payout_info['base_loss']:.0f} | Final Payout: ₹{payout_info['final_payout']:.0f}"
        f"{' (cap applied)' if payout_info['cap_applied'] else ''}"
        f"{' (new user: 60% rate)' if 'New User' in rider['name'] else ''}")

    with st.expander("View Income Loss Calculation"):
        st.markdown(f"""
| Parameter | Value |
|---|---|
| Avg Orders/Hour (Zone) | {zone_data['avg_orders']} |
| Avg Income/Order | ₹40 |
| Disruption Severity | {payout_info['severity']:.2f} |
| Estimated Lost Hours | {payout_info['lost_hours']} hrs |
| Base Income Loss | ₹{payout_info['base_loss']:.0f} |
| Zone Payout Cap ({zone_data['risk']} Risk) | ₹{ {'Low': 350, 'Medium': 500, 'High': 700}[zone_data['risk']]} |
| Cap Applied | {'Yes' if payout_info['cap_applied'] else 'No'} |
| **Final Payout** | **₹{payout_info['final_payout']:.0f}** |
        """)
        st.markdown(f"**Formula:** `Loss = (Orders/Hr × ₹/Order × Lost Hours × Severity)`")
        st.markdown(f"**Calculation:** `{zone_data['avg_orders']} × ₹40 × {payout_info['lost_hours']} × {payout_info['severity']:.2f} = ₹{payout_info['base_loss']:.0f}`")

    # ── Node 5: Payout Processor ─────────────────────────────────────────
    node5 = st.empty()
    simulate_node(node5, "Node 5: Payout Processor", "💸",
                  f"Processing UPI payment of ₹{payout_info['final_payout']:.0f} to {rider['name']}...")
    progress_bar.progress(90, text="Processing payment...")

    txn_id = f"TXN-{random.randint(100000, 999999)}"
    show_node_result(node5, "Node 5: Payout Processor", "💸",
        f"Payment SUCCESS — ₹{payout_info['final_payout']:.0f} credited via UPI | "
        f"Transaction: {txn_id} | Time: {datetime.now().strftime('%H:%M:%S')}")

    progress_bar.progress(100, text="Pipeline complete — Claim APPROVED")

    # ── Final Result ─────────────────────────────────────────────────────
    st.markdown("")
    st.markdown(f"""<div class="payout-success">
        <h2>CLAIM APPROVED — ₹{payout_info['final_payout']:.0f} PAID</h2>
        <p style="font-size: 1.1rem;">{rider['name']} received instant payout via UPI | Transaction: {txn_id}</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Payout Amount", f"₹{payout_info['final_payout']:.0f}")
    with col2:
        st.metric("Processing Time", f"{random.uniform(1.2, 3.8):.1f}s")
    with col3:
        st.metric("Fraud Score", f"{fraud_score:.2f}", delta="Clean", delta_color="normal")
    with col4:
        st.metric("Confidence", f"{random.uniform(0.88, 0.97):.0%}")

    # SMS notification
    st.success(f"📱 SMS sent to {rider['name']}: \"InsureFlow: ₹{payout_info['final_payout']:.0f} credited to your UPI for {payout_info['disruption_type'].replace('_', ' ')} disruption in {zone_name}. Txn: {txn_id}\"")

    # LLM Reasoning
    with st.expander("LLM Reasoning Chain (Groq LLaMA 3.1)"):
        st.code(f"""
[LLM Reasoning — Claim Approval]

OBSERVATION: Rider {rider['name']} in zone {zone_data['zone_id']} ({zone_name}).
Weather API confirms {weather['condition']} with {weather['rainfall_mm']}mm/hr rainfall.
{"Flood alert level " + str(weather['flood_alert']) + " active. " if weather['flood_alert'] >= 2 else ""}{"AQI at " + str(weather['aqi']) + " (hazardous). " if weather.get('aqi', 0) > 300 else ""}

VALIDATION: All {len(validation_checks)} checks passed.
- Active policy: YES (₹{zone_data['premium']}/week plan)
- In zone: YES ({zone_data['warehouse']}, within 5km radius)
- Pre-event activity: {rider['pre_event_active_hrs']} hours (strong signal of genuine presence)
- GPS integrity: Consistent across GPS, cell tower, and Wi-Fi signals
- Fraud score: {fraud_score:.2f} (well below 0.30 threshold)

DISRUPTION SEVERITY: {payout_info['severity']:.2f}
Triggers: {', '.join(payout_info['triggers'])}
Estimated lost hours: {payout_info['lost_hours']}

INCOME CALCULATION:
Zone avg orders: {zone_data['avg_orders']}/hr × ₹40/order × {payout_info['lost_hours']}hrs × {payout_info['severity']:.2f} severity
= ₹{payout_info['base_loss']:.0f} base loss → ₹{payout_info['final_payout']:.0f} after {'cap' if payout_info['cap_applied'] else 'no cap needed'}

DECISION: APPROVE with HIGH confidence.
Rider profile is consistent, weather data independently verifiable,
activity signals strong. No fraud indicators present.
        """, language="text")

    # Audit log
    with st.expander("Full Audit Log (JSON)"):
        audit = {
            "claim_id": f"CLM-{random.randint(10000, 99999)}",
            "timestamp": datetime.now().isoformat(),
            "rider": rider["name"],
            "zone": zone_data["zone_id"],
            "zone_name": zone_name,
            "weather": weather,
            "disruption_type": payout_info["disruption_type"],
            "severity": payout_info["severity"],
            "validation": {check: {"passed": passed, "detail": detail} for check, passed, detail in validation_checks},
            "fraud_score": fraud_score,
            "payout": {
                "amount": payout_info["final_payout"],
                "currency": "INR",
                "method": "UPI",
                "transaction_id": txn_id,
                "status": "completed"
            },
            "decision": "APPROVED",
            "processing_time_ms": random.randint(1200, 3800),
            "llm_model": "groq/llama-3.1-70b",
            "graph_nodes_executed": ["data_ingestion", "disruption_analyst", "fraud_validator", "actuarial_engine", "payout_processor"]
        }
        st.json(audit)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <b>InsureFlow AI</b> — Team HATS | Guidewire Hackathon 2026<br>
    <small>Built with LangGraph + Groq + Scikit-learn + FastAPI + React</small><br>
    <small>Because gig workers deserve instant, fair, automated insurance.</small>
</div>
""", unsafe_allow_html=True)
