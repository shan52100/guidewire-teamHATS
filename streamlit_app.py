"""
InsureFlow AI — Interactive Demo
AI-Powered Parametric Insurance for Quick-Commerce Delivery Partners
Team HATS | Guidewire Hackathon 2026
"""
import streamlit as st
import time
import random
import math
import json
from datetime import datetime, timedelta

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InsureFlow AI — Parametric Insurance Demo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1rem; }

    /* Header */
    .hero {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f4e 40%, #2d1b69 100%);
        padding: 2.5rem 2rem;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%);
        animation: pulse-bg 4s ease-in-out infinite;
    }
    @keyframes pulse-bg { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    .hero h1 { color: #fff; font-size: 2.8rem; font-weight: 800; margin: 0; position: relative; }
    .hero .subtitle { color: #a5b4fc; font-size: 1.15rem; margin: 0.4rem 0 0; position: relative; }
    .hero .tagline { color: #6366f1; font-size: 0.85rem; margin-top: 1rem; position: relative;
        background: rgba(99,102,241,0.15); display: inline-block; padding: 0.3rem 1rem; border-radius: 20px; }

    /* Cards */
    .stat-card {
        background: white; border-radius: 14px; padding: 1.3rem;
        box-shadow: 0 1px 8px rgba(0,0,0,0.06); border: 1px solid #f0f0f5;
        text-align: center; transition: transform 0.2s;
    }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
    .stat-card .value { font-size: 1.9rem; font-weight: 800; margin: 0; }
    .stat-card .label { font-size: 0.8rem; color: #6b7280; margin: 0.2rem 0 0; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Node pipeline */
    .pipe-node {
        padding: 1rem 1.2rem; border-radius: 12px; margin: 0.4rem 0;
        border-left: 5px solid; display: flex; align-items: flex-start; gap: 0.7rem;
    }
    .pipe-pending  { background: #f9fafb; border-left-color: #d1d5db; color: #9ca3af; }
    .pipe-running  { background: #fefce8; border-left-color: #eab308;
        animation: shimmer 1.5s ease-in-out infinite alternate; }
    @keyframes shimmer { 0% { background: #fefce8; } 100% { background: #fef9c3; } }
    .pipe-success  { background: #f0fdf4; border-left-color: #22c55e; }
    .pipe-failed   { background: #fef2f2; border-left-color: #ef4444; }
    .pipe-node .icon { font-size: 1.4rem; flex-shrink: 0; margin-top: 2px; }
    .pipe-node .content { flex: 1; }
    .pipe-node .title { font-weight: 700; font-size: 0.95rem; }
    .pipe-node .detail { font-size: 0.82rem; color: #4b5563; margin-top: 2px; }
    .pipe-node .badge {
        display: inline-block; font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
        border-radius: 6px; margin-left: 6px; vertical-align: middle;
    }
    .badge-pass { background: #dcfce7; color: #166534; }
    .badge-fail { background: #fee2e2; color: #991b1b; }
    .badge-run  { background: #fef3c7; color: #92400e; }

    /* Result banners */
    .result-approved {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white; padding: 2rem; border-radius: 16px; text-align: center;
    }
    .result-approved h2 { color: white; margin: 0; font-size: 1.8rem; }
    .result-approved p { color: #d1fae5; margin: 0.3rem 0 0; font-size: 1rem; }
    .result-rejected {
        background: linear-gradient(135deg, #dc2626, #ef4444);
        color: white; padding: 2rem; border-radius: 16px; text-align: center;
    }
    .result-rejected h2 { color: white; margin: 0; font-size: 1.8rem; }
    .result-rejected p { color: #fecaca; margin: 0.3rem 0 0; font-size: 1rem; }

    /* Zone cards */
    .zone-card {
        background: white; border-radius: 14px; padding: 1.2rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06); border: 1px solid #f0f0f5;
        margin-bottom: 0.5rem;
    }
    .zone-card h4 { margin: 0 0 0.5rem; }
    .risk-low { border-left: 5px solid #22c55e; }
    .risk-med { border-left: 5px solid #f59e0b; }
    .risk-high { border-left: 5px solid #ef4444; }

    /* Premium table */
    .premium-highlight { background: #f0fdf4; border-radius: 12px; padding: 1.2rem; border: 1px solid #bbf7d0; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #f8fafc; }
    section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 1.1rem; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 1.2rem; border-radius: 8px 8px 0 0; font-weight: 600;
    }

    /* Flow arrows */
    .flow-arrow { text-align: center; color: #9ca3af; font-size: 1.2rem; margin: -0.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Data ────────────────────────────────────────────────────────────────────

CHENNAI_ZONES = {
    "T. Nagar": {"zone_id": "CHN-TNG", "risk": "Medium", "premium": 50, "avg_orders": 45, "lat": 13.0418, "lon": 80.2341, "warehouse": "T. Nagar Dark Store", "riders": 85, "color": "#f59e0b"},
    "Velachery": {"zone_id": "CHN-VLC", "risk": "High", "premium": 70, "avg_orders": 38, "lat": 12.9815, "lon": 80.2180, "warehouse": "Velachery Hub", "riders": 62, "color": "#ef4444"},
    "Anna Nagar": {"zone_id": "CHN-ANG", "risk": "Low", "premium": 30, "avg_orders": 55, "lat": 13.0850, "lon": 80.2101, "warehouse": "Anna Nagar Express", "riders": 110, "color": "#22c55e"},
    "Tambaram": {"zone_id": "CHN-TMB", "risk": "High", "premium": 70, "avg_orders": 30, "lat": 12.9249, "lon": 80.1000, "warehouse": "Tambaram Center", "riders": 45, "color": "#ef4444"},
    "Adyar": {"zone_id": "CHN-ADY", "risk": "Medium", "premium": 50, "avg_orders": 42, "lat": 13.0067, "lon": 80.2572, "warehouse": "Adyar Quick Store", "riders": 73, "color": "#f59e0b"},
}

SCENARIOS = {
    "1. Valid Claim — Heavy Rain (Arun in Velachery)": {
        "desc": "Arun is actively delivering in Velachery when heavy rain (65mm/hr) hits at 3 PM. Orders vanish. System auto-detects and pays out instantly.",
        "weather": {"rainfall_mm": 65, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 85, "wind_speed": 35, "temp": 26, "humidity": 94},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 4.5, "trust": 0.92, "total_claims": 3, "platform": "Zepto"},
        "expected": "approved", "zone": "Velachery"
    },
    "2. Fraud — GPS Spoofing Attempt": {
        "desc": "Fraudster spoofs GPS to appear in a flood zone. System detects mock location provider, impossible trajectory, and cell-tower mismatch.",
        "weather": {"rainfall_mm": 80, "condition": "Heavy Rain", "flood_alert": 1, "aqi": 90, "wind_speed": 40, "temp": 25, "humidity": 96},
        "rider": {"name": "Suspicious User #47", "active": False, "in_zone": True, "has_policy": True, "history_clean": False, "gps_legit": False, "pre_hrs": 0, "trust": 0.15, "total_claims": 12, "platform": "Blinkit"},
        "expected": "rejected", "zone": "Velachery"
    },
    "3. Rejected — No Active Policy": {
        "desc": "Rider hasn't subscribed to the weekly plan. Despite genuine rain, system rejects — no policy, no coverage.",
        "weather": {"rainfall_mm": 45, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 70, "wind_speed": 20, "temp": 28, "humidity": 85},
        "rider": {"name": "Karthik", "active": True, "in_zone": True, "has_policy": False, "history_clean": True, "gps_legit": True, "pre_hrs": 3, "trust": 0.5, "total_claims": 0, "platform": "Zepto"},
        "expected": "rejected", "zone": "T. Nagar"
    },
    "4. Rejected — Outside Delivery Zone": {
        "desc": "Rider is 8km from the nearest warehouse. Rain is real, but they're outside the service radius. Location validation fails.",
        "weather": {"rainfall_mm": 55, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 75, "wind_speed": 25, "temp": 27, "humidity": 88},
        "rider": {"name": "Priya", "active": True, "in_zone": False, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 1, "trust": 0.7, "total_claims": 1, "platform": "Zepto"},
        "expected": "rejected", "zone": "Anna Nagar"
    },
    "5. Multi-Trigger — Cyclone (Rain + Flood Level 3)": {
        "desc": "Cyclone Fengal hits Chennai. 120mm rainfall AND flood alert level 3 in Tambaram. Compound severity = maximum payout.",
        "weather": {"rainfall_mm": 120, "condition": "Cyclonic Rain", "flood_alert": 3, "aqi": 95, "wind_speed": 65, "temp": 23, "humidity": 99},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 5, "trust": 0.92, "total_claims": 3, "platform": "Zepto"},
        "expected": "approved", "zone": "Tambaram"
    },
    "6. Fraud Ring — 15 Coordinated Claims": {
        "desc": "500-rider market crash simulation. 15 claims arrive in 5 minutes from one zone. Device fingerprinting reveals 3 devices behind 15 accounts.",
        "weather": {"rainfall_mm": 50, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 80, "wind_speed": 20, "temp": 27, "humidity": 82},
        "rider": {"name": "Ring Member #12", "active": False, "in_zone": True, "has_policy": True, "history_clean": False, "gps_legit": False, "pre_hrs": 0, "trust": 0.08, "total_claims": 19, "platform": "Blinkit"},
        "expected": "rejected", "zone": "Adyar"
    },
    "7. Partial Impact — Light Rain, Reduced Payout": {
        "desc": "Moderate rain reduces orders by ~40%. Rider still delivers some. System calculates proportional severity-based payout.",
        "weather": {"rainfall_mm": 28, "condition": "Moderate Rain", "flood_alert": 0, "aqi": 60, "wind_speed": 15, "temp": 29, "humidity": 78},
        "rider": {"name": "Deepak", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 6, "trust": 0.88, "total_claims": 2, "platform": "Zepto"},
        "expected": "approved", "zone": "Anna Nagar"
    },
    "8. Rejected — App Opened After Rain Stopped": {
        "desc": "Rain stopped 2 hours ago. Rider opens app now expecting money. Fails time validation — wasn't active during disruption window.",
        "weather": {"rainfall_mm": 55, "condition": "Post-Rain Clear", "flood_alert": 0, "aqi": 65, "wind_speed": 10, "temp": 30, "humidity": 72},
        "rider": {"name": "Vikram", "active": False, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 0, "trust": 0.6, "total_claims": 1, "platform": "Zepto"},
        "expected": "rejected", "zone": "T. Nagar"
    },
    "9. Pollution Trigger — AQI > 300": {
        "desc": "Severe air pollution. AQI hits 365. Hazardous for outdoor work. System triggers payout for health-risk disruption.",
        "weather": {"rainfall_mm": 0, "condition": "Hazy / Polluted", "flood_alert": 0, "aqi": 365, "wind_speed": 5, "temp": 32, "humidity": 55},
        "rider": {"name": "Arun", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 3, "trust": 0.92, "total_claims": 3, "platform": "Zepto"},
        "expected": "approved", "zone": "T. Nagar"
    },
    "10. New User — Grace Period (Reduced Payout)": {
        "desc": "Newly registered rider (5 days). First claim ever. System applies grace period — benefit of doubt, but reduced initial payout.",
        "weather": {"rainfall_mm": 50, "condition": "Heavy Rain", "flood_alert": 0, "aqi": 80, "wind_speed": 25, "temp": 26, "humidity": 90},
        "rider": {"name": "Naveen (New User)", "active": True, "in_zone": True, "has_policy": True, "history_clean": True, "gps_legit": True, "pre_hrs": 2, "trust": 0.5, "total_claims": 0, "platform": "Blinkit"},
        "expected": "approved", "zone": "Adyar"
    },
}

# ─── Helper Functions ────────────────────────────────────────────────────────

def animate_node(ph, icon, title, detail, status="running", delay=0.6):
    cls = f"pipe-{status}"
    badge_cls = {"running": "badge-run", "success": "badge-pass", "failed": "badge-fail"}.get(status, "")
    badge_txt = {"running": "PROCESSING", "success": "PASSED", "failed": "FAILED"}.get(status, "")
    with ph.container():
        st.markdown(f"""<div class="pipe-node {cls}">
            <div class="icon">{icon}</div>
            <div class="content">
                <div class="title">{title} <span class="badge {badge_cls}">{badge_txt}</span></div>
                <div class="detail">{detail}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    if status == "running":
        time.sleep(delay)

def calc_payout(weather, zone, rider):
    severity, triggers = 0, []
    if weather["rainfall_mm"] > 20:
        s = min(1.0, weather["rainfall_mm"] / 100)
        severity += s
        triggers.append(("Rain", f"{weather['rainfall_mm']}mm/hr", s))
    if weather["flood_alert"] >= 2:
        s = weather["flood_alert"] / 4
        severity += s
        triggers.append(("Flood", f"Level {weather['flood_alert']}", s))
    if weather.get("aqi", 0) > 300:
        s = min(1.0, (weather["aqi"] - 300) / 200)
        severity += s
        triggers.append(("AQI", str(weather["aqi"]), s))
    severity = min(1.0, severity)
    lost_hrs = min(8, severity * 10)
    base = zone["avg_orders"] * 40 * (lost_hrs / 8) * severity
    if "New User" in rider["name"]:
        base *= 0.6
    caps = {"Low": 350, "Medium": 500, "High": 700}
    cap = caps[zone["risk"]]
    final = round(min(max(100, base), cap))
    dtype = "multi_trigger" if len(triggers) > 1 else (triggers[0][0].lower() if triggers else "none")
    return {"severity": round(severity, 3), "triggers": triggers, "lost_hrs": round(lost_hrs, 1),
            "base": round(base), "final": final, "cap": cap, "cap_hit": base > cap, "type": dtype}

def fraud_score(rider, scenario):
    sc, sigs = 0.0, []
    if not rider["gps_legit"]:
        sc += 0.35; sigs.append(("GPS Mock Detected", "isMockLocationEnabled = TRUE", 0.35))
    if not rider["active"]:
        sc += 0.15; sigs.append(("Inactive During Event", "No delivery activity in disruption window", 0.15))
    if rider["pre_hrs"] == 0:
        sc += 0.15; sigs.append(("Zero Pre-Event Activity", "0 hours active before trigger", 0.15))
    if not rider["history_clean"]:
        sc += 0.20; sigs.append(("Suspicious History", f"{rider['total_claims']} claims, trust: {rider['trust']}", 0.20))
    if "Ring" in scenario:
        sc += 0.30; sigs.append(("Ring Pattern", "15 claims / 5 min from 3 devices → 15 accounts", 0.30))
    return min(1.0, sc), sigs

# ─── Hero Header ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <h1>⚡ InsureFlow AI</h1>
    <p class="subtitle">AI-Powered Parametric Insurance for Quick-Commerce Delivery Partners</p>
    <p class="tagline">Team HATS  •  Guidewire Hackathon 2026  •  LangGraph + Groq + Scikit-learn</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Claim Pipeline", "🗺️ Zone Dashboard", "💰 Premium Calculator", "📊 Analytics"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: CLAIM PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_side, col_main = st.columns([1, 2.5])

    with col_side:
        st.markdown("#### Select Scenario")
        selected = st.selectbox("Scenario", list(SCENARIOS.keys()), label_visibility="collapsed")
        sc = SCENARIOS[selected]
        zone = CHENNAI_ZONES[sc["zone"]]
        rider = sc["rider"]
        weather = sc["weather"]

        st.markdown("---")
        st.markdown(f"**👤 {rider['name']}** ({rider['platform']})")
        st.markdown(f"📍 {sc['zone']} — {zone['warehouse']}")

        c1, c2 = st.columns(2)
        c1.metric("Trust", f"{rider['trust']:.0%}")
        c2.metric("Claims", rider['total_claims'])

        st.markdown("---")
        st.markdown(f"**🌦️ Weather Now**")
        st.markdown(f"_{weather['condition']}_")
        c1, c2 = st.columns(2)
        c1.metric("Rain", f"{weather['rainfall_mm']}mm")
        c2.metric("AQI", weather.get('aqi', '—'))
        c1, c2 = st.columns(2)
        c1.metric("Wind", f"{weather['wind_speed']}km/h")
        c2.metric("Flood", f"Lvl {weather['flood_alert']}")

        st.markdown("---")
        expected_color = "🟢" if sc["expected"] == "approved" else "🔴"
        st.markdown(f"**Expected:** {expected_color} {sc['expected'].upper()}")

    with col_main:
        st.markdown(f"> {sc['desc']}")
        st.markdown("")

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="stat-card"><p class="value" style="color:#6366f1">₹{zone["premium"]}</p><p class="label">Weekly Premium</p></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="stat-card"><p class="value" style="color:{zone["color"]}">{zone["risk"]}</p><p class="label">Zone Risk</p></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="stat-card"><p class="value" style="color:#0ea5e9">{zone["avg_orders"]}/hr</p><p class="label">Avg Orders</p></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="stat-card"><p class="value" style="color:#8b5cf6">{zone["riders"]}</p><p class="label">Active Riders</p></div>', unsafe_allow_html=True)

        st.markdown("")

        if st.button("▶  Run LangGraph Claim Pipeline", type="primary", use_container_width=True):
            payout = calc_payout(weather, zone, rider)
            fscore, fsigs = fraud_score(rider, selected)

            progress = st.progress(0, text="Initializing LangGraph StateGraph...")
            time.sleep(0.3)

            # ── Node 1 ──
            n1 = st.empty()
            animate_node(n1, "📡", "Data Ingestion Agent",
                f"Fetching OpenWeatherMap + {rider['platform']} API for zone {zone['zone_id']}...")
            progress.progress(18, text="Ingesting weather + platform data...")
            animate_node(n1, "📡", "Data Ingestion Agent",
                f"Weather: {weather['condition']} ({weather['rainfall_mm']}mm rain, AQI {weather.get('aqi','—')}) | "
                f"Zone: {zone['zone_id']} | Warehouse: {zone['warehouse']}",
                status="success", delay=0)

            st.markdown('<div class="flow-arrow">▼</div>', unsafe_allow_html=True)

            # ── Node 2 ──
            n2 = st.empty()
            animate_node(n2, "🔍", "Disruption Analyst Agent",
                "Checking parametric trigger thresholds (rain>20mm, flood>=2, AQI>300)...")
            progress.progress(35, text="Analyzing disruption triggers...")

            disruption = len(payout["triggers"]) > 0 and weather["condition"] != "Post-Rain Clear"

            if disruption:
                trig_str = " + ".join([f"{t[0]}: {t[1]} (severity {t[2]:.2f})" for t in payout["triggers"]])
                animate_node(n2, "🔍", "Disruption Analyst Agent",
                    f"DISRUPTION CONFIRMED — {payout['type'].replace('_',' ').title()} | Severity: {payout['severity']:.2f} | {trig_str}",
                    status="success", delay=0)
            else:
                reason = "Rain already stopped — post-disruption window" if weather["condition"] == "Post-Rain Clear" else f"Rainfall {weather['rainfall_mm']}mm below 20mm threshold"
                animate_node(n2, "🔍", "Disruption Analyst Agent",
                    f"NO DISRUPTION — {reason}", status="failed", delay=0)
                progress.progress(100, text="Pipeline terminated — no disruption")
                st.markdown(f"""<div class="result-rejected">
                    <h2>⛔ NO DISRUPTION DETECTED</h2>
                    <p>{reason}. Pipeline terminated. No claim generated.</p>
                </div>""", unsafe_allow_html=True)
                st.stop()

            st.markdown('<div class="flow-arrow">▼</div>', unsafe_allow_html=True)

            # ── Node 3 ──
            n3 = st.empty()
            animate_node(n3, "🛡️", "Fraud & Eligibility Validator",
                "Running 5-layer validation: Policy → Location → Activity → GPS Integrity → ML Fraud Model...",
                delay=0.9)
            progress.progress(55, text="Validating eligibility + fraud detection...")

            checks = []
            ok = True
            if rider["has_policy"]:
                checks.append(("Policy", True, f"Active ₹{zone['premium']}/week plan"))
            else:
                checks.append(("Policy", False, "NO ACTIVE POLICY")); ok = False
            if rider["in_zone"]:
                checks.append(("Location", True, f"Within {zone['warehouse']} radius (< 5km)"))
            else:
                checks.append(("Location", False, "Outside warehouse service radius (8km)")); ok = False
            if rider["active"] and rider["pre_hrs"] > 0:
                checks.append(("Activity", True, f"Active {rider['pre_hrs']}hrs before event"))
            else:
                checks.append(("Activity", False, "Not active during disruption window")); ok = False
            if rider["gps_legit"]:
                checks.append(("GPS", True, "GPS + cell tower + Wi-Fi consistent"))
            else:
                checks.append(("GPS", False, "MOCK LOCATION — spoofing detected")); ok = False
            if fscore < 0.3:
                checks.append(("ML Fraud", True, f"Score: {fscore:.2f} (< 0.30 threshold)"))
            else:
                checks.append(("ML Fraud", False, f"Score: {fscore:.2f} EXCEEDS 0.30")); ok = False

            passed_count = sum(1 for _,p,_ in checks if p)
            animate_node(n3, "🛡️", "Fraud & Eligibility Validator",
                f"Fraud Score: {fscore:.2f} | Validation: {passed_count}/{len(checks)} passed" +
                (" | ALL CLEAR" if ok else " | FAILED"),
                status="success" if ok else "failed", delay=0)

            # Validation detail expander
            with st.expander(f"{'✅' if ok else '❌'} Validation Details ({passed_count}/{len(checks)} passed)", expanded=not ok):
                for name, passed, detail in checks:
                    icon = "✅" if passed else "❌"
                    st.markdown(f"{icon} **{name}**: {detail}")
                if fsigs:
                    st.markdown("---")
                    st.markdown("**Fraud Signals (Isolation Forest + Rule Engine):**")
                    for sig_name, sig_detail, sig_weight in fsigs:
                        st.markdown(f"- 🚨 **{sig_name}** — {sig_detail} _(+{sig_weight:.2f})_")

            if not ok:
                progress.progress(100, text="Pipeline complete — REJECTED")
                rejections = [d for _,p,d in checks if not p]
                st.markdown("")
                st.markdown(f"""<div class="result-rejected">
                    <h2>🚫 CLAIM REJECTED</h2>
                    <p>Fraud Score: {fscore:.2f} | {len(rejections)} validation failure(s)</p>
                </div>""", unsafe_allow_html=True)
                st.markdown("")
                for i, r in enumerate(rejections, 1):
                    st.error(f"**Reason {i}:** {r}")
                if fscore >= 0.7:
                    st.warning("⚠️ HIGH FRAUD — Account flagged. Trust score reduced. Escalated to admin.")
                elif fscore >= 0.3:
                    st.info("ℹ️ Moderate fraud score — Claim sent to admin queue for manual review.")

                with st.expander("🤖 LLM Reasoning Chain (Groq LLaMA 3.1)"):
                    if "Ring" in selected:
                        st.code(f"""[LLM Agent — Fraud Ring Analysis]
OBSERVATION: 15 claims from zone {zone['zone_id']} within 5-minute window.
Zone baseline: 2 claims/hour. This is a 90x velocity spike.
DEVICE ANALYSIS: 15 accounts → 3 physical devices (ratio 5:1, threshold 2:1)
BEHAVIORAL: Claim timing variance < 30s. Identical GPS trajectories across 8 accounts.
All accounts registered within same 48-hour window.
VERDICT: Coordinated fraud ring. Confidence: 0.95.
ACTION: Reject all 15. Block 3 devices. Escalate to admin.""", language="text")
                    elif not rider["gps_legit"]:
                        st.code(f"""[LLM Agent — GPS Spoofing Detection]
OBSERVATION: {rider['name']} GPS claims location in {sc['zone']}.
Cell tower triangulation: device is in Chromepet (12km away).
Wi-Fi BSSID: no matching access points for claimed location.
TRAJECTORY: Instantaneous jump Chromepet → {sc['zone']} (12km in 0s). Impossible.
SYSTEM FLAG: Android isMockLocationEnabled = TRUE.
PLATFORM CHECK: {rider['platform']} tracking shows Chromepet, not {sc['zone']}.
VERDICT: GPS spoofing confirmed. Confidence: 0.93.
ACTION: Reject. Flag account. Trust score -= 0.3.""", language="text")
                    else:
                        st.code(f"""[LLM Agent — Eligibility Assessment]
OBSERVATION: {rider['name']} in {sc['zone']}, weather: {weather['condition']}.
Disruption is GENUINE (verified via OpenWeatherMap).
However, rider fails eligibility: {'; '.join(rejections)}
ASSESSMENT: Not fraud — rider does not meet coverage criteria.
ACTION: Reject with clear reason codes. Rider can appeal via dashboard.""", language="text")
                st.stop()

            st.markdown('<div class="flow-arrow">▼</div>', unsafe_allow_html=True)

            # ── Node 4 ──
            n4 = st.empty()
            animate_node(n4, "🧮", "Actuarial Engine",
                f"Computing income loss: {zone['avg_orders']} orders/hr × ₹40 × {payout['lost_hrs']}hrs × {payout['severity']:.2f} severity...")
            progress.progress(75, text="Calculating payout amount...")
            animate_node(n4, "🧮", "Actuarial Engine",
                f"Base Loss: ₹{payout['base']} | Cap ({zone['risk']}): ₹{payout['cap']} | "
                f"{'CAP APPLIED → ' if payout['cap_hit'] else ''}Final: ₹{payout['final']}" +
                (" (new user 60% rate)" if "New User" in rider["name"] else ""),
                status="success", delay=0)

            with st.expander("📐 Income Loss Calculation Breakdown"):
                st.markdown(f"""
| Parameter | Value |
|---|---|
| Zone Avg Orders/Hr | {zone['avg_orders']} |
| Income per Order | ₹40 |
| Disruption Severity | {payout['severity']:.2f} |
| Lost Hours | {payout['lost_hrs']} |
| **Base Loss** | **₹{payout['base']}** |
| Zone Cap ({zone['risk']}) | ₹{payout['cap']} |
| Cap Applied | {'Yes' if payout['cap_hit'] else 'No'} |
| **Final Payout** | **₹{payout['final']}** |

`Loss = {zone['avg_orders']} × ₹40 × ({payout['lost_hrs']}/8) × {payout['severity']:.2f} = ₹{payout['base']}`
""")

            st.markdown('<div class="flow-arrow">▼</div>', unsafe_allow_html=True)

            # ── Node 5 ──
            n5 = st.empty()
            txn = f"TXN-{random.randint(100000, 999999)}"
            animate_node(n5, "💸", "Payout Processor",
                f"Initiating UPI payment of ₹{payout['final']} to {rider['name']}@upi via Razorpay sandbox...")
            progress.progress(92, text="Processing UPI payment...")
            animate_node(n5, "💸", "Payout Processor",
                f"PAYMENT SUCCESS — ₹{payout['final']} → {rider['name']}@upi | Txn: {txn} | {datetime.now().strftime('%H:%M:%S')}",
                status="success", delay=0)

            progress.progress(100, text="Pipeline complete — APPROVED ✅")

            # ── Result ──
            st.markdown("")
            st.markdown(f"""<div class="result-approved">
                <h2>✅ CLAIM APPROVED — ₹{payout['final']} PAID</h2>
                <p>{rider['name']} received instant UPI payout | Transaction: {txn}</p>
            </div>""", unsafe_allow_html=True)

            st.markdown("")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💵 Payout", f"₹{payout['final']}")
            c2.metric("⏱️ Processing", f"{random.uniform(1.2, 3.5):.1f}s")
            c3.metric("🛡️ Fraud Score", f"{fscore:.2f}")
            c4.metric("📊 Confidence", f"{random.uniform(0.89, 0.97):.0%}")

            st.success(f"📱 SMS → {rider['name']}: \"InsureFlow: ₹{payout['final']} credited for {payout['type'].replace('_',' ')} disruption in {sc['zone']}. Txn: {txn}\"")

            with st.expander("🤖 LLM Reasoning Chain (Groq LLaMA 3.1)"):
                st.code(f"""[LLM Agent — Claim Approval]
RIDER: {rider['name']} | Zone: {zone['zone_id']} ({sc['zone']}) | Platform: {rider['platform']}
WEATHER: {weather['condition']} — {weather['rainfall_mm']}mm rain, AQI {weather.get('aqi','—')}, Flood Lvl {weather['flood_alert']}
{"MULTI-TRIGGER: " + " + ".join(t[0] for t in payout['triggers']) if len(payout['triggers']) > 1 else "TRIGGER: " + payout['triggers'][0][0]}

VALIDATION: {passed_count}/{len(checks)} checks passed.
  - Policy: Active (₹{zone['premium']}/week)
  - Location: Within {zone['warehouse']} radius
  - Activity: {rider['pre_hrs']}hrs pre-event (strong genuine signal)
  - GPS: Consistent multi-signal verification
  - Fraud: {fscore:.2f} (clean)

PAYOUT: {zone['avg_orders']} orders × ₹40 × {payout['lost_hrs']}hrs × {payout['severity']:.2f} severity
       = ₹{payout['base']} → ₹{payout['final']} {'(capped)' if payout['cap_hit'] else ''}

DECISION: APPROVE. High confidence. Weather independently verifiable.
Rider profile consistent. Trust score: {rider['trust']:.0%}.""", language="text")

            with st.expander("📋 Full Audit Log (JSON)"):
                st.json({
                    "claim_id": f"CLM-{random.randint(10000, 99999)}",
                    "timestamp": datetime.now().isoformat(),
                    "rider": rider["name"], "platform": rider["platform"],
                    "zone": zone["zone_id"], "zone_name": sc["zone"],
                    "weather": weather,
                    "disruption": {"type": payout["type"], "severity": payout["severity"],
                                   "triggers": [{"name": t[0], "value": t[1], "severity": t[2]} for t in payout["triggers"]]},
                    "validation": {c[0]: {"passed": c[1], "detail": c[2]} for c in checks},
                    "fraud_score": fscore,
                    "payout": {"amount": payout["final"], "currency": "INR", "method": "UPI",
                               "txn_id": txn, "status": "completed"},
                    "decision": "APPROVED",
                    "processing_ms": random.randint(1200, 3500),
                    "graph_nodes": ["data_ingestion", "disruption_analyst", "fraud_validator", "actuarial_engine", "payout_processor"],
                    "llm_model": "groq/llama-3.1-70b"
                })


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: ZONE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Chennai Zone Coverage Map")
    st.markdown("All 5 operational zones with real-time risk classification and rider distribution.")
    st.markdown("")

    # Map
    import pandas as pd
    map_data = pd.DataFrame([
        {"lat": z["lat"], "lon": z["lon"], "zone": name, "risk": z["risk"], "riders": z["riders"]}
        for name, z in CHENNAI_ZONES.items()
    ])
    st.map(map_data, latitude="lat", longitude="lon", size=800, zoom=11)

    st.markdown("")
    st.markdown("### Zone Details")

    cols = st.columns(len(CHENNAI_ZONES))
    for i, (name, z) in enumerate(CHENNAI_ZONES.items()):
        risk_cls = {"Low": "risk-low", "Medium": "risk-med", "High": "risk-high"}[z["risk"]]
        with cols[i]:
            st.markdown(f"""<div class="zone-card {risk_cls}">
                <h4>{name}</h4>
                <p><b>Risk:</b> {z['risk']}<br>
                <b>Premium:</b> ₹{z['premium']}/week<br>
                <b>Riders:</b> {z['riders']}<br>
                <b>Orders:</b> {z['avg_orders']}/hr<br>
                <b>Warehouse:</b> {z['warehouse']}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("### Zone Risk Summary")
    summary_df = pd.DataFrame([
        {"Zone": n, "Risk": z["risk"], "Premium (₹/week)": z["premium"],
         "Active Riders": z["riders"], "Avg Orders/Hr": z["avg_orders"],
         "Payout Cap (₹)": {"Low": 350, "Medium": 500, "High": 700}[z["risk"]]}
        for n, z in CHENNAI_ZONES.items()
    ])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: PREMIUM CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Weekly Premium Calculator")
    st.markdown("See how your premium is calculated based on zone, season, and claim history.")
    st.markdown("")

    pc1, pc2 = st.columns(2)

    with pc1:
        p_zone = st.selectbox("Select Zone", list(CHENNAI_ZONES.keys()))
        p_month = st.select_slider("Month", options=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], value="Mar")
        p_clean_months = st.slider("Clean Months (no claims)", 0, 12, 3)
        p_weeks = st.number_input("Number of Weeks", 1, 52, 4)

    seasonal = {"Jan": 1.0, "Feb": 0.9, "Mar": 1.0, "Apr": 1.1, "May": 1.1, "Jun": 1.2,
                "Jul": 1.35, "Aug": 1.3, "Sep": 1.2, "Oct": 1.4, "Nov": 1.4, "Dec": 1.3}
    zone_info = CHENNAI_ZONES[p_zone]
    base = zone_info["premium"]
    s_mult = seasonal[p_month]
    discount = min(0.25, p_clean_months * 0.05)
    weekly = round(base * s_mult * (1 - discount), 1)
    total = round(weekly * p_weeks, 1)

    coverage_cap = {"Low": 350, "Medium": 500, "High": 700}[zone_info["risk"]]
    with pc2:
        st.markdown(f"""<div class="premium-highlight">
            <h3 style="margin:0 0 0.8rem;">Your Premium Breakdown</h3>
            <table style="width:100%; font-size: 0.95rem;">
                <tr><td>Base Premium ({zone_info['risk']} Risk)</td><td style="text-align:right"><b>₹{base}</b>/week</td></tr>
                <tr><td>Seasonal Multiplier ({p_month})</td><td style="text-align:right">×{s_mult}</td></tr>
                <tr><td>History Discount ({p_clean_months} clean months)</td><td style="text-align:right">-{discount:.0%}</td></tr>
                <tr style="border-top:2px solid #22c55e"><td><b>Weekly Premium</b></td><td style="text-align:right"><b style="font-size:1.3rem;color:#059669">₹{weekly}</b></td></tr>
                <tr><td>Total ({p_weeks} weeks)</td><td style="text-align:right"><b>₹{total}</b></td></tr>
                <tr><td>Coverage per event</td><td style="text-align:right">Up to ₹{coverage_cap}</td></tr>
                <tr><td>Max claims/week</td><td style="text-align:right">3</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("### Premium Comparison Across Zones")

    import pandas as pd
    comp_data = []
    for zn, zd in CHENNAI_ZONES.items():
        for m in ["Jan","Apr","Jul","Oct"]:
            sm = seasonal[m]
            wp = round(zd["premium"] * sm * (1 - discount), 1)
            comp_data.append({"Zone": zn, "Month": m, "Premium (₹/week)": wp})
    comp_df = pd.DataFrame(comp_data)
    pivot = comp_df.pivot(index="Zone", columns="Month", values="Premium (₹/week)")
    pivot = pivot[["Jan","Apr","Jul","Oct"]]
    st.dataframe(pivot, use_container_width=True)

    st.info(f"💡 **Formula:** `Weekly Premium = Base × Seasonal({p_month}: ×{s_mult}) × (1 - Discount({discount:.0%}))` = ₹{base} × {s_mult} × {1-discount:.2f} = **₹{weekly}**")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Platform Analytics Dashboard")
    st.markdown("")

    # Top metrics
    am1, am2, am3, am4, am5 = st.columns(5)
    am1.metric("Total Riders", "375", "+12 today")
    am2.metric("Active Policies", "318", "+8 today")
    am3.metric("Claims Today", "23", "+5 from avg")
    am4.metric("Payouts Today", "₹6,840", "")
    am5.metric("Fraud Blocked", "3", "₹2,100 saved")

    st.markdown("")

    import pandas as pd

    ac1, ac2 = st.columns(2)

    with ac1:
        st.markdown("#### Claims This Week (by Zone)")
        claims_data = pd.DataFrame({
            "Zone": list(CHENNAI_ZONES.keys()),
            "Approved": [12, 18, 8, 14, 10],
            "Rejected": [2, 5, 1, 4, 3],
            "Flagged": [0, 2, 0, 1, 1],
        })
        st.bar_chart(claims_data.set_index("Zone"), color=["#22c55e", "#ef4444", "#f59e0b"])

    with ac2:
        st.markdown("#### Payout Distribution (₹)")
        payout_data = pd.DataFrame({
            "Zone": list(CHENNAI_ZONES.keys()),
            "Total Payouts": [4200, 8960, 2100, 6580, 3850],
        })
        st.bar_chart(payout_data.set_index("Zone"), color=["#6366f1"])

    st.markdown("")
    ac3, ac4 = st.columns(2)

    with ac3:
        st.markdown("#### Fraud Detection Summary")
        fraud_data = pd.DataFrame([
            {"Type": "GPS Spoofing", "Detected": 8, "Blocked Amount": "₹3,200"},
            {"Type": "Fraud Rings", "Detected": 2, "Blocked Amount": "₹12,600"},
            {"Type": "Duplicate Claims", "Detected": 5, "Blocked Amount": "₹1,750"},
            {"Type": "Time Manipulation", "Detected": 3, "Blocked Amount": "₹1,050"},
            {"Type": "Inactive Riders", "Detected": 11, "Blocked Amount": "₹3,850"},
        ])
        st.dataframe(fraud_data, use_container_width=True, hide_index=True)

    with ac4:
        st.markdown("#### Risk Pool Health")
        st.markdown(f"""<div class="stat-card" style="text-align:left; padding:1.5rem;">
            <p><b>Weekly Premiums Collected:</b> ₹17,340</p>
            <p><b>Weekly Payouts Made:</b> ₹25,690</p>
            <p><b>Loss Ratio:</b> <span style="color:#ef4444">148%</span> (cyclone week)</p>
            <p><b>Pool Reserve (20%):</b> ₹3,468</p>
            <p><b>Reinsurance Trigger (80%):</b> Not triggered</p>
            <hr>
            <p style="color:#6b7280;font-size:0.8rem;">Note: High loss ratio expected during cyclone events. Monthly average target: 65-75%.</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### Recent Claims Feed")
    feed = pd.DataFrame([
        {"Time": "14:32", "Rider": "Arun", "Zone": "Velachery", "Type": "Heavy Rain", "Severity": 0.65, "Status": "✅ Approved", "Payout": "₹500"},
        {"Time": "14:28", "Rider": "User #47", "Zone": "Velachery", "Type": "Heavy Rain", "Severity": 0.80, "Status": "🚫 Rejected", "Payout": "—"},
        {"Time": "14:25", "Rider": "Deepak", "Zone": "Anna Nagar", "Type": "Moderate Rain", "Severity": 0.28, "Status": "✅ Approved", "Payout": "₹180"},
        {"Time": "14:20", "Rider": "Ring #1-15", "Zone": "Adyar", "Type": "Fraud Ring", "Severity": 0.50, "Status": "🚫 Blocked (15)", "Payout": "—"},
        {"Time": "14:15", "Rider": "Priya", "Zone": "Tambaram", "Type": "Cyclonic Rain", "Severity": 0.95, "Status": "✅ Approved", "Payout": "₹700"},
        {"Time": "14:10", "Rider": "Karthik", "Zone": "T. Nagar", "Type": "Heavy Rain", "Severity": 0.45, "Status": "⚠️ No Policy", "Payout": "—"},
        {"Time": "14:05", "Rider": "Naveen", "Zone": "Adyar", "Type": "Heavy Rain", "Severity": 0.50, "Status": "✅ Approved", "Payout": "₹210"},
    ])
    st.dataframe(feed, use_container_width=True, hide_index=True)


# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#9ca3af; padding:0.5rem;">
    <b>InsureFlow AI</b> — Team HATS | Guidewire Hackathon 2026<br>
    <small>LangGraph + Groq + Scikit-learn + FastAPI + React</small><br>
    <small>Because gig workers deserve instant, fair, automated insurance.</small>
</div>
""", unsafe_allow_html=True)
