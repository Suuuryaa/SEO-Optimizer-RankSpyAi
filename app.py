import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime, date
import os

from seo_utils import *
from scoring import calculate_seo_score, get_score_band
from comparison_utils import compare_metric
from leaderboard_utils import analyze_venue
from summary_utils import get_executive_summary, generate_ai_executive_summary
from pagespeed_utils import get_pagespeed_data
from competitor_utils import (
    build_full_serp_table,
    filter_direct_competitors,
    get_top_n_external_direct_competitors,
    get_primary_result
)
from benchmark_utils import build_benchmark_summary
from insight_utils import generate_strategic_insights
from keyword_opportunity_utils import find_keyword_opportunities
from location_utils import get_location_from_url, format_location_display
from geo_utils import check_ai_crawlers, score_citability, check_llmstxt, check_eeat, calculate_geo_score


# ==================== API KEY CONFIGURATION ====================
import json
import hashlib

_default_pagespeed = ""
_default_serper = ""
_default_gemini = ""

try:
    _default_pagespeed = st.secrets["PAGESPEED_API_KEY"]
    _default_serper = st.secrets["SERPER_API_KEY"]
    _default_gemini = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError, AttributeError):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        _default_pagespeed = os.getenv("PAGESPEED_API_KEY", "")
        _default_serper = os.getenv("SERPER_API_KEY", "")
        _default_gemini = os.getenv("GEMINI_API_KEY", "")
    except:
        pass

# ==================== IP-BASED RATE LIMITING ====================
IP_LIMIT = 2
_IP_STORE = os.path.join(os.path.dirname(__file__), "ip_counts.json")

def _get_client_ip():
    try:
        headers = st.context.headers
        ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "local"))
        return ip.split(",")[0].strip()
    except Exception:
        return "local"

def _hash_ip(ip):
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

def _load_ip_counts():
    if os.path.exists(_IP_STORE):
        try:
            with open(_IP_STORE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_ip_counts(counts):
    try:
        with open(_IP_STORE, "w") as f:
            json.dump(counts, f)
    except Exception:
        pass

def _get_ip_uses(ip_hash):
    return _load_ip_counts().get(ip_hash, 0)

def _increment_ip_uses(ip_hash):
    counts = _load_ip_counts()
    counts[ip_hash] = counts.get(ip_hash, 0) + 1
    _save_ip_counts(counts)
    return counts[ip_hash]

_client_ip = _get_client_ip()
_ip_hash = _hash_ip(_client_ip)

# ==================== ADMIN MODE ====================
_admin_password = ""
try:
    _admin_password = st.secrets["ADMIN_PASSWORD"]
except Exception:
    pass

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False

# Session state for user-provided keys
if "user_serper_key" not in st.session_state:
    st.session_state.user_serper_key = ""
if "user_gemini_key" not in st.session_state:
    st.session_state.user_gemini_key = ""
if "user_pagespeed_key" not in st.session_state:
    st.session_state.user_pagespeed_key = ""
if "user_scraperapi_key" not in st.session_state:
    st.session_state.user_scraperapi_key = ""

def _using_own_keys():
    return bool(st.session_state.user_serper_key and st.session_state.user_gemini_key)

def _active_keys():
    """Return (serp, gemini, pagespeed, scraperapi) keys to use."""
    if st.session_state.is_admin:
        return (_default_serper, _default_gemini, _default_pagespeed, "")
    if _using_own_keys():
        return (
            st.session_state.user_serper_key,
            st.session_state.user_gemini_key,
            st.session_state.user_pagespeed_key or _default_pagespeed,
            st.session_state.user_scraperapi_key,
        )
    return (_default_serper, _default_gemini, _default_pagespeed, "")

def _check_limit():
    """Return (allowed, remaining). Admins and own-key users always allowed."""
    if st.session_state.is_admin or _using_own_keys():
        return True, 999
    used = _get_ip_uses(_ip_hash)
    remaining = max(0, IP_LIMIT - used)
    return remaining > 0, remaining

# Active keys for this session
serp_key, gemini_api_key, pagespeed_api_key, _scraperapi_key = _active_keys()

# Inject ScraperAPI key into environment so seo_utils picks it up
if _scraperapi_key:
    os.environ["SCRAPER_API_KEY"] = _scraperapi_key


# ==================== UI HELPER FUNCTIONS ====================

def create_score_gauge(score, title="SEO Score"):
    """Create circular gauge visualization like professional SEO tools"""
    
    # Determine color and rating based on score
    if score >= 80:
        color = "#00C853"  # Green
        rating = "Excellent"
    elif score >= 70:
        color = "#4CAF50"  # Light Green
        rating = "Good"
    elif score >= 60:
        color = "#FFA726"  # Orange
        rating = "Fair"
    elif score >= 50:
        color = "#FF7043"  # Deep Orange
        rating = "Needs Work"
    else:
        color = "#EF5350"  # Red
        rating = "Poor"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {
            'text': f"<b>{title}</b><br><span style='font-size:0.7em; color:gray'>{rating}</span>",
            'font': {'size': 20}
        },
        number = {'font': {'size': 48, 'color': color}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 2, 'tickcolor': "lightgray"},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 3,
            'bordercolor': "lightgray",
            'steps': [
                {'range': [0, 50], 'color': '#FFEBEE'},
                {'range': [50, 70], 'color': '#FFF3E0'},
                {'range': [70, 100], 'color': '#E8F5E9'}
            ],
            'threshold': {
                'line': {'color': "darkgray", 'width': 3},
                'thickness': 0.8,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=80, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "white"}
    )
    
    return fig


def status_indicator(passed, label):
    """Create visual status indicator"""
    if passed:
        return f"<div style='padding: 5px; margin: 3px 0;'>✅ <span style='color: #00C853; font-weight: 500;'>{label}</span></div>"
    else:
        return f"<div style='padding: 5px; margin: 3px 0;'>❌ <span style='color: #EF5350; font-weight: 500;'>{label}</span></div>"


def priority_badge(priority):
    """Create priority badge with color"""
    badges = {
        "🔴 CRITICAL": "background-color: #EF5350; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold;",
        "🟠 HIGH": "background-color: #FF7043; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold;",
        "🟡 MEDIUM": "background-color: #FFA726; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold;",
        "✅ EXCELLENT": "background-color: #00C853; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold;"
    }
    
    style = badges.get(priority, "background-color: gray; color: white; padding: 3px 10px; border-radius: 12px;")
    return f"<span style='{style}'>{priority}</span>"


def create_radar_chart(categories, values, title="SEO Factors"):
    """Radar/spider chart for multi-factor SEO breakdown."""
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(102,126,234,0.25)',
        line=dict(color='#667eea', width=2),
        marker=dict(size=6, color='#667eea'),
        name='Score'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9), gridcolor='rgba(255,255,255,0.1)'),
            angularaxis=dict(tickfont=dict(size=11, color='white'), gridcolor='rgba(255,255,255,0.1)'),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=False,
        title=dict(text=title, font=dict(size=14, color='white'), x=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=320,
        margin=dict(l=40, r=40, t=50, b=20),
    )
    return fig


def create_donut_chart(labels, values, colors, title="", center_text=""):
    """Clean donut chart like the dashboard screenshots."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(colors=colors, line=dict(color='rgba(0,0,0,0)', width=0)),
        textinfo='none',
        hovertemplate='%{label}: %{value}<extra></extra>'
    ))
    fig.add_annotation(
        text=center_text, x=0.5, y=0.5, font=dict(size=18, color='white', family='Arial Black'),
        showarrow=False, align='center'
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color='white'), x=0.5),
        showlegend=True,
        legend=dict(font=dict(size=10, color='white'), orientation='v', x=1.02, y=0.5),
        paper_bgcolor='rgba(0,0,0,0)',
        height=280,
        margin=dict(l=10, r=120, t=40, b=10),
    )
    return fig


def create_horizontal_bar(labels, values, colors=None, title=""):
    """Horizontal bar chart for factor scoring."""
    if colors is None:
        colors = ['#667eea' if v >= 70 else '#FFA726' if v >= 50 else '#EF5350' for v in values]
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v}" for v in values],
        textposition='outside',
        textfont=dict(color='white', size=11)
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color='white'), x=0),
        xaxis=dict(range=[0, 115], showgrid=True, gridcolor='rgba(255,255,255,0.08)', tickfont=dict(color='white')),
        yaxis=dict(tickfont=dict(size=11, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=max(220, len(labels) * 42),
        margin=dict(l=10, r=60, t=40, b=20),
        bargap=0.35,
    )
    return fig


def kpi_card_html(label, value, color="#667eea", icon="📊", delta=None):
    delta_html = f"<div class='kpi-delta' style='color:{color}'>{delta}</div>" if delta else ""
    return f"""
    <div class='kpi-card'>
        <div style='font-size:1.5rem'>{icon}</div>
        <div class='kpi-value' style='color:{color}'>{value}</div>
        <div class='kpi-label'>{label}</div>
        {delta_html}
    </div>"""


def build_recommended_fixes(
    title_has_keyword,
    meta_has_keyword,
    h1_has_keyword,
    kc,
    title_len,
    meta_len,
    missing_alt_count,
    pagespeed_data,
    https_enabled=True,
    mobile_viewport=True,
    has_schema=False
):
    """Build prioritized recommendations list"""
    fixes = []

    if not title_has_keyword:
        fixes.append({
            "Priority": "🔴 CRITICAL",
            "Issue": "Target keyword missing from title",
            "Recommended Fix": "Add the target keyword naturally to the page title.",
            "Impact": "High - Title is the most important on-page SEO factor"
        })

    if not meta_has_keyword:
        fixes.append({
            "Priority": "🟠 HIGH",
            "Issue": "Target keyword missing from meta description",
            "Recommended Fix": "Rewrite meta description to include keyword and compelling CTA.",
            "Impact": "Medium - Improves click-through rate from search results"
        })

    if not h1_has_keyword:
        fixes.append({
            "Priority": "🔴 CRITICAL",
            "Issue": "Target keyword missing from H1",
            "Recommended Fix": "Add target keyword or close variation to main H1 heading.",
            "Impact": "High - H1 signals primary topic to search engines"
        })

    if kc == 0:
        fixes.append({
            "Priority": "🔴 CRITICAL",
            "Issue": "Exact keyword not present in page content",
            "Recommended Fix": "Use target keyword naturally in intro, headings, and body copy.",
            "Impact": "Critical - No relevance signals for target keyword"
        })
    elif kc < 3:
        fixes.append({
            "Priority": "🟡 MEDIUM",
            "Issue": "Low keyword usage in content",
            "Recommended Fix": "Increase keyword usage naturally (target: 5+ occurrences).",
            "Impact": "Medium - Strengthens topical relevance"
        })

    if title_len < 30 or title_len > 60:
        fixes.append({
            "Priority": "🟡 MEDIUM",
            "Issue": f"Title length not optimal ({title_len} characters)",
            "Recommended Fix": "Keep title between 30-60 characters for best display.",
            "Impact": "Low - May be truncated in search results"
        })

    if meta_len < 120 or meta_len > 160:
        fixes.append({
            "Priority": "🟡 MEDIUM",
            "Issue": f"Meta description length not optimal ({meta_len} characters)",
            "Recommended Fix": "Keep meta description between 120-160 characters.",
            "Impact": "Low - May be truncated or rewritten by Google"
        })

    if missing_alt_count > 0:
        fixes.append({
            "Priority": "🟡 MEDIUM",
            "Issue": f"{missing_alt_count} images missing ALT text",
            "Recommended Fix": "Add descriptive ALT text to improve accessibility and image SEO.",
            "Impact": "Medium - Accessibility issue and missed opportunity"
        })
    
    if not https_enabled:
        fixes.append({
            "Priority": "🔴 CRITICAL",
            "Issue": "Site not using HTTPS",
            "Recommended Fix": "Enable HTTPS/SSL certificate immediately.",
            "Impact": "Critical - Security ranking factor"
        })
    
    if not mobile_viewport:
        fixes.append({
            "Priority": "🔴 CRITICAL",
            "Issue": "No mobile viewport configuration",
            "Recommended Fix": "Add viewport meta tag for mobile-first indexing.",
            "Impact": "Critical - Required for mobile search"
        })
    
    if not has_schema:
        fixes.append({
            "Priority": "🟡 MEDIUM",
            "Issue": "No structured data detected",
            "Recommended Fix": "Add schema markup for rich snippets (LocalBusiness, Organization, etc.).",
            "Impact": "Medium - Enables rich search results"
        })

    if pagespeed_data:
        perf = pagespeed_data.get("performance_score")
        if perf is not None and perf < 0.7:
            fixes.append({
                "Priority": "🟠 HIGH",
                "Issue": "Weak mobile performance score",
                "Recommended Fix": "Optimize load speed, reduce blocking resources, compress images.",
                "Impact": "High - Core Web Vitals affect rankings"
            })

        cls = pagespeed_data.get("cumulative_layout_shift")
        if cls and cls != "None":
            fixes.append({
                "Priority": "🟡 MEDIUM",
                "Issue": "Layout stability may need improvement",
                "Recommended Fix": "Reserve space for images/embeds to reduce layout shifts.",
                "Impact": "Medium - Part of Core Web Vitals"
            })

    if not fixes:
        fixes.append({
            "Priority": "✅ EXCELLENT",
            "Issue": "No major issues detected",
            "Recommended Fix": "Maintain current optimization and monitor competitors regularly.",
            "Impact": "Keep tracking performance"
        })

    return fixes


# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="SEO Intelligence Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== PREMIUM CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

/* ═══════════════════════════════════════════════
   ANIMATIONS — DigitalStrike + Webflow combined
═══════════════════════════════════════════════ */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInLeft {
    from { opacity: 0; transform: translateX(-30px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes fadeInRight {
    from { opacity: 0; transform: translateX(30px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes shimmer {
    0%   { transform: translateX(-150%) skewX(-20deg); }
    100% { transform: translateX(300%) skewX(-20deg); }
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-8px); }
}
@keyframes gradient-shift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes pulse-ring {
    0%   { transform: scale(1);   opacity: 1; }
    100% { transform: scale(2.2); opacity: 0; }
}
@keyframes grid-move {
    0%   { transform: translateY(0); }
    100% { transform: translateY(60px); }
}
@keyframes orb1 {
    0%, 100% { transform: translate(0,0); }
    50%       { transform: translate(60px,-40px); }
}
@keyframes orb2 {
    0%, 100% { transform: translate(0,0); }
    50%       { transform: translate(-50px,30px); }
}
@keyframes ticker {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
@keyframes border-run {
    0%   { background-position: 0% 50%; }
    100% { background-position: 400% 50%; }
}

/* ═══════════════════════════════════════════════
   BASE — Pure black like DigitalStrike
═══════════════════════════════════════════════ */
* { font-family: 'Outfit', sans-serif !important; }
.main > div { padding-top: 0 !important; }
.block-container {
    padding: 0 2.5rem 4rem !important;
    max-width: 100% !important;
    margin: 0 !important;
}

/* Full black base + moving grid lines (Webflow aesthetic) */
.stApp { background: #000000 !important; }
.stApp > div { position: relative; }

/* Animated dot-grid background */
.stApp::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
        radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px);
    background-size: 40px 40px;
    animation: grid-move 8s linear infinite;
    pointer-events: none; z-index: 0; opacity: 0.4;
}

/* Floating colour orbs */
.stApp::after {
    content: '';
    position: fixed; top: -200px; right: -200px;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(176,32,37,0.12) 0%, transparent 60%);
    border-radius: 50%;
    animation: orb1 20s ease-in-out infinite;
    pointer-events: none; z-index: 0;
}

/* ═══════════════════════════════════════════════
   HERO — Full-width DigitalStrike style
═══════════════════════════════════════════════ */
.hero-header {
    background: linear-gradient(160deg, #0a0000 0%, #1a0000 40%, #0d0a00 100%);
    border: none;
    border-bottom: 1px solid rgba(176,32,37,0.2);
    border-radius: 0;
    padding: 4rem 2.5rem 3rem;
    margin: 0 -2.5rem 2rem;
    position: relative; overflow: hidden;
    animation: fadeInUp 0.8s ease-out both;
}
/* Red orb top-left */
.hero-header::before {
    content: '';
    position: absolute; top: -100px; left: -100px;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(176,32,37,0.18) 0%, transparent 60%);
    border-radius: 50%;
    animation: orb1 15s ease-in-out infinite;
}
/* Teal orb bottom-right */
.hero-header::after {
    content: '';
    position: absolute; bottom: -80px; right: 10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(126,199,163,0.08) 0%, transparent 60%);
    border-radius: 50%;
    animation: orb2 18s ease-in-out infinite;
}
.hero-eyebrow {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: #B02025;
    margin-bottom: 1.2rem; animation: fadeInLeft 0.6s 0.1s ease-out both;
}
.hero-title {
    font-size: clamp(2.8rem, 5vw, 4.5rem);
    font-weight: 900; line-height: 1;
    letter-spacing: -2px;
    color: #ffffff;
    margin: 0 0 0.4rem;
    animation: fadeInLeft 0.7s 0.2s ease-out both;
}
.hero-title-accent {
    background: linear-gradient(90deg, #B02025, #FF4444, #FF6B35, #B02025);
    background-size: 300%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 4s ease infinite;
}
.hero-sub {
    font-size: 1.15rem; color: rgba(255,255,255,0.5);
    font-weight: 400; line-height: 1.6;
    max-width: 560px; margin: 1rem 0 0;
    animation: fadeInLeft 0.7s 0.35s ease-out both;
}
.hero-badges {
    display: flex; gap: 0.5rem; margin-top: 2rem; flex-wrap: wrap;
    animation: fadeInUp 0.7s 0.5s ease-out both;
}
.hero-badge {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.55);
    padding: 6px 16px; border-radius: 50px;
    font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase;
    transition: all 0.25s;
}
.hero-badge:hover {
    background: rgba(176,32,37,0.15);
    border-color: rgba(176,32,37,0.4);
    color: #ff6b6b;
    transform: translateY(-2px);
}

/* ═══════════════════════════════════════════════
   INPUT CARD
═══════════════════════════════════════════════ */
.input-card {
    background: #0a0a0a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 2rem 2rem 1.5rem;
    margin-bottom: 1.5rem;
    position: relative; overflow: hidden;
    animation: fadeInUp 0.6s 0.3s ease-out both;
}
/* Animated top border */
.input-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #B02025, #FF4444, #7EC7A3, #B02025);
    background-size: 400%;
    animation: border-run 4s linear infinite;
}
.input-card-title {
    font-size: 0.65rem; font-weight: 800;
    color: rgba(255,255,255,0.35);
    text-transform: uppercase; letter-spacing: 0.18em; margin-bottom: 1.2rem;
}

/* ═══════════════════════════════════════════════
   INPUTS — Clean dark Webflow style
═══════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #111111 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-size: 0.95rem !important;
    font-family: 'Outfit', sans-serif !important;
    transition: all 0.25s ease !important;
    padding: 0.75rem 1rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #B02025 !important;
    box-shadow: 0 0 0 3px rgba(176,32,37,0.12) !important;
    background: #151515 !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: rgba(255,255,255,0.25) !important;
}
.stTextInput label, .stTextArea label {
    font-size: 0.8rem !important; font-weight: 600 !important;
    color: rgba(255,255,255,0.5) !important;
    letter-spacing: 0.05em !important; text-transform: uppercase !important;
}

/* ═══════════════════════════════════════════════
   BUTTONS — DigitalStrike pill style
═══════════════════════════════════════════════ */
.stButton > button {
    width: 100% !important;
    border-radius: 50px !important;
    height: 3.5em !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    transition: all 0.3s ease !important;
    border: none !important;
    position: relative !important;
    overflow: hidden !important;
}
/* shimmer sweep */
.stButton > button::after {
    content: '' !important;
    position: absolute !important; top: 0 !important; left: -100% !important;
    width: 50% !important; height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent) !important;
    animation: shimmer 3s infinite !important;
}
/* PRIMARY — bold red like DigitalStrike CTA */
.stButton > button[kind="primary"] {
    background: #B02025 !important;
    color: #ffffff !important;
    box-shadow: 0 4px 30px rgba(176,32,37,0.45) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #581013 !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 40px rgba(176,32,37,0.6), 0 0 0 1px rgba(255,255,255,0.1) !important;
}
/* SECONDARY — ghost white Webflow style */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1.5px solid rgba(255,255,255,0.2) !important;
    color: rgba(255,255,255,0.8) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.4) !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 20px rgba(255,255,255,0.08) !important;
}

/* ═══════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: #0a0a0a;
    border-radius: 0; padding: 0;
    border: none; border-bottom: 1px solid rgba(255,255,255,0.08) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important; padding: 14px 24px !important;
    font-weight: 600 !important; font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
    color: rgba(255,255,255,0.4) !important;
    background: transparent !important; border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #B02025 !important;
    background: transparent !important;
}

/* ═══════════════════════════════════════════════
   KPI CARDS — Webflow clean float
═══════════════════════════════════════════════ */
.kpi-card {
    background: #0a0a0a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 1.5rem 1rem;
    text-align: center; transition: all 0.3s ease;
    position: relative; overflow: hidden;
    animation: float 7s ease-in-out infinite;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #B02025, #FF6B35, #7EC7A3);
}
.kpi-card:hover {
    transform: translateY(-6px) !important;
    border-color: rgba(176,32,37,0.3) !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5), 0 0 0 1px rgba(176,32,37,0.1);
}
.kpi-value {
    font-size: 2.4rem; font-weight: 900; color: #fff;
    margin: 0.4rem 0; line-height: 1; letter-spacing: -1px;
}
.kpi-label {
    font-size: 0.65rem; color: rgba(255,255,255,0.4);
    text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700;
}
.kpi-delta { font-size: 0.8rem; font-weight: 600; margin-top: 0.3rem; }

/* ═══════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════ */
.section-header {
    font-size: 0.65rem; font-weight: 800; letter-spacing: 0.18em;
    text-transform: uppercase; color: #B02025;
    margin-bottom: 1rem; padding-bottom: 0.6rem;
    border-bottom: 1px solid rgba(176,32,37,0.15);
}

/* ═══════════════════════════════════════════════
   METRICS — Webflow card style
═══════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important; padding: 1rem 1.2rem !important;
    transition: all 0.3s !important;
    animation: fadeInUp 0.5s ease-out both !important;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(176,32,37,0.3) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4) !important;
    transform: translateY(-2px);
}
[data-testid="metric-container"] label { color: rgba(255,255,255,0.45) !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #ffffff !important; font-weight: 800 !important;
}

/* ═══════════════════════════════════════════════
   DATAFRAME
═══════════════════════════════════════════════ */
.stDataFrame {
    border-radius: 12px !important; overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    animation: fadeInUp 0.5s ease-out both;
}
.stDataFrame thead th {
    background: #111111 !important;
    font-weight: 700 !important; font-size: 0.72rem !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    color: rgba(255,255,255,0.5) !important; border-bottom: 1px solid rgba(176,32,37,0.3) !important;
}
.stDataFrame tbody tr:hover td { background: rgba(176,32,37,0.05) !important; }

/* ═══════════════════════════════════════════════
   PROGRESS BAR
═══════════════════════════════════════════════ */
.stProgress > div > div > div {
    border-radius: 50px !important;
    background: linear-gradient(90deg, #B02025, #FF4444, #7EC7A3) !important;
    background-size: 200% !important;
    animation: gradient-shift 2s ease infinite !important;
}
.stProgress > div > div {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 50px !important;
}

/* ═══════════════════════════════════════════════
   ALERTS
═══════════════════════════════════════════════ */
.stAlert { border-radius: 10px !important; border-left-width: 3px !important; }

/* ═══════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: #050505 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}

/* ═══════════════════════════════════════════════
   DIVIDER
═══════════════════════════════════════════════ */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 2rem 0 !important; }

/* ═══════════════════════════════════════════════
   DEMO BADGE
═══════════════════════════════════════════════ */
.demo-badge {
    display: inline-flex; align-items: center; gap: 10px;
    background: #0a0a0a;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 50px; padding: 0.6rem 1.2rem;
    font-size: 0.82rem; color: rgba(255,255,255,0.55); font-weight: 500;
}
.demo-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #7EC7A3;
    box-shadow: 0 0 8px #7EC7A3;
    position: relative;
}
.demo-dot::after {
    content: '';
    position: absolute; inset: -3px;
    border-radius: 50%; border: 1px solid #7EC7A3;
    animation: pulse-ring 1.5s ease-out infinite;
}

/* ═══════════════════════════════════════════════
   SPINNER & SCROLLBAR
═══════════════════════════════════════════════ */
.stSpinner > div { border-top-color: #B02025 !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #B02025; border-radius: 50px; }
::-webkit-scrollbar-thumb:hover { background: #FF4444; }

/* ═══════════════════════════════════════════════
   EXPANDER — fix arrow overlap bug
═══════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] details summary p {
    font-weight: 600 !important;
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.88rem !important;
}
[data-testid="stExpander"] details summary svg {
    fill: rgba(255,255,255,0.4) !important;
}

/* ═══════════════════════════════════════════════
   SELECTBOX
═══════════════════════════════════════════════ */
.stSelectbox > div > div {
    background: #111111 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
}

/* Fade-in for main content */
.stMainBlockContainer { animation: fadeInUp 0.6s ease-out both; }

/* ── Remove Streamlit default top padding ── */
header[data-testid="stHeader"] { display: none !important; }
#root > div:nth-child(1) > div > div > div > div > section > div { padding-top: 0 !important; }

/* ── Tighten vertical gaps ── */
.stTextInput { margin-bottom: 0.3rem !important; }
div[data-testid="column"] { padding: 0 0.4rem !important; }

/* ── Compare toggle button — small inline style ── */
button[kind="secondary"][data-testid="baseButton-secondary"]:has-text("COMPARE") {
    width: auto !important;
}
div[data-testid="stButton"]:has(button[key="toggle_compare"]) button {
    width: auto !important;
    font-size: 0.72rem !important;
    height: 2.4em !important;
    padding: 0 1.2rem !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    letter-spacing: 0.1em !important;
    color: rgba(255,255,255,0.4) !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ==================== HERO HEADER ====================

st.markdown("""
<div class="hero-header">
    <div class="hero-eyebrow">AI-Powered SEO Intelligence</div>
    <div class="hero-title">BOLD STRATEGY.<br><span class="hero-title-accent">STRIKING RESULTS.</span></div>
    <p class="hero-sub">Analyze, benchmark, and outrank your competitors — powered by AI, driven by data.</p>
    <div class="hero-badges">
        <span class="hero-badge">Real-Time Intelligence</span>
        <span class="hero-badge">Competitive Benchmarking</span>
        <span class="hero-badge">Technical SEO Audit</span>
        <span class="hero-badge">AI-Powered Insights</span>
        <span class="hero-badge">Enterprise-Grade Analysis</span>
        <span class="hero-badge">Strategic Action Plans</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== ADMIN CORNER BUTTON ====================
st.markdown("""
<style>
.admin-corner {
    position: fixed; bottom: 18px; right: 18px; z-index: 9999;
    opacity: 0.18; transition: opacity 0.3s;
}
.admin-corner:hover { opacity: 0.7; }
</style>
""", unsafe_allow_html=True)

# Tiny corner button — one button, toggles between 🔒 and 🔓
_acol1, _acol2 = st.columns([20, 1])
with _acol2:
    _btn_icon = "🔓" if st.session_state.is_admin else "🔒"
    if st.button(_btn_icon, key="admin_btn", help="Admin"):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
            st.rerun()
        else:
            st.session_state.show_admin_login = not st.session_state.show_admin_login

if st.session_state.show_admin_login and not st.session_state.is_admin:
    with st.container():
        st.markdown("""
<div style="background:#0d0d0d;border:1px solid rgba(255,215,0,0.15);border-radius:12px;
            padding:1rem 1.4rem;margin-bottom:0.5rem;max-width:320px;">
    <div style="font-size:0.6rem;font-weight:800;color:rgba(255,215,0,0.5);
                letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.5rem;">Admin Access</div>
""", unsafe_allow_html=True)
        _pwd = st.text_input("Password", type="password", key="admin_pwd_input", label_visibility="collapsed")
        if _pwd:
            if _admin_password and _pwd == _admin_password:
                st.session_state.is_admin = True
                st.session_state.show_admin_login = False
                st.rerun()
            else:
                st.markdown('<div style="font-size:0.75rem;color:#FF5252;">Incorrect password.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== INPUT SECTION ====================

def _render_badge(placeholder):
    if st.session_state.is_admin:
        badge_text = '<strong style="color:#FFD600;">Admin</strong>'
        dot_color = "#FFD600"
    elif _using_own_keys():
        badge_text = '<strong style="color:#7EC7A3;">Unlimited</strong>'
        dot_color = "#7EC7A3"
    else:
        used = _get_ip_uses(_ip_hash)
        rem = max(0, IP_LIMIT - used)
        bar_color = "#00C853" if rem == IP_LIMIT else "#FFA726" if rem > 0 else "#EF5350"
        badge_text = f'<strong style="color:{bar_color}">{rem}</strong> / {IP_LIMIT} tries left'
        dot_color = bar_color
    placeholder.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
    <span style="font-size:0.65rem;font-weight:800;color:#B02025;letter-spacing:0.18em;text-transform:uppercase;">🔍 Analysis Setup</span>
    <div class="demo-badge">
        <div class="demo-dot" style="background:{dot_color};box-shadow:0 0 8px {dot_color};"></div>
        Demo &nbsp;·&nbsp; {badge_text}
    </div>
</div>
""", unsafe_allow_html=True)

_badge_placeholder = st.empty()
_render_badge(_badge_placeholder)

url = st.text_input("🌐 Website URL", placeholder="https://example.com")
keyword = st.text_input("🔑 Target Keyword", placeholder="e.g. running shoes, web design agency")

# ── Advanced: Compare Specific URLs (custom collapsible — avoids Streamlit _arrow_right bug) ──
if "show_compare_urls" not in st.session_state:
    st.session_state.show_compare_urls = False

toggle_label = "— COMPARE SPECIFIC URLS" if st.session_state.show_compare_urls else "+ COMPARE SPECIFIC URLS  (optional)"
if st.button(toggle_label, key="toggle_compare", type="secondary"):
    st.session_state.show_compare_urls = not st.session_state.show_compare_urls

venue_urls_text = ""
compare_url = ""

if st.session_state.show_compare_urls:
    venue_urls_text = st.text_area(
        "COMPETITOR URLS — one per line",
        height=100,
        placeholder="https://competitor1.com\nhttps://competitor2.com\nhttps://competitor3.com",
    )
    compare_url = st.text_input("Or compare against a single URL", placeholder="https://competitor.com")

st.markdown("<br>", unsafe_allow_html=True)

# ── Use Your Own API Keys (collapsible) ──────────────────────────────────────
if "show_own_keys" not in st.session_state:
    st.session_state.show_own_keys = False

_own_keys_label = "— BRING YOUR OWN API KEYS" if st.session_state.show_own_keys else "+ BRING YOUR OWN API KEYS  —  UNLOCK UNLIMITED ACCESS"
if st.button(_own_keys_label, key="toggle_own_keys", type="secondary"):
    st.session_state.show_own_keys = not st.session_state.show_own_keys

if st.session_state.show_own_keys:
    _allowed, _remaining = _check_limit()
    if not _allowed:
        st.markdown("""
<div style="background:rgba(176,32,37,0.08);border:1px solid rgba(176,32,37,0.25);
            border-radius:10px;padding:0.8rem 1.2rem;font-size:0.82rem;
            color:rgba(255,255,255,0.6);margin-bottom:0.6rem;">
    You've used your <strong style="color:#FF5252;">2 free tries</strong>.
    Add your own API keys below to continue with unlimited access.
</div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="font-size:0.7rem;color:rgba(255,255,255,0.35);margin-bottom:0.8rem;line-height:1.6;">
    Enter your own API keys for <strong style="color:rgba(255,255,255,0.55);">unlimited</strong> usage.
    Keys are stored only in your browser session and never saved to any server.
</div>""", unsafe_allow_html=True)

    _k1, _k2 = st.columns(2)
    with _k1:
        _s = st.text_input("Serper API Key  ✱ required", type="password",
                           value=st.session_state.user_serper_key,
                           placeholder="Get free at serper.dev")
        if _s != st.session_state.user_serper_key:
            st.session_state.user_serper_key = _s
    with _k2:
        _g = st.text_input("Gemini API Key  ✱ required", type="password",
                           value=st.session_state.user_gemini_key,
                           placeholder="Get free at aistudio.google.com")
        if _g != st.session_state.user_gemini_key:
            st.session_state.user_gemini_key = _g

    _k3, _k4 = st.columns(2)
    with _k3:
        _p = st.text_input("PageSpeed API Key  (optional — Core Web Vitals only)", type="password",
                           value=st.session_state.user_pagespeed_key,
                           placeholder="console.cloud.google.com")
        if _p != st.session_state.user_pagespeed_key:
            st.session_state.user_pagespeed_key = _p
    with _k4:
        _sc = st.text_input("ScraperAPI Key  (optional)", type="password",
                            value=st.session_state.user_scraperapi_key,
                            placeholder="scraperapi.com — free trial available")
        if _sc != st.session_state.user_scraperapi_key:
            st.session_state.user_scraperapi_key = _sc

    st.markdown("""
<div style="font-size:0.72rem;color:rgba(255,255,255,0.28);margin-top:0.3rem;line-height:1.5;">
    💡 <strong style="color:rgba(255,255,255,0.4);">ScraperAPI</strong> is optional but recommended —
    it helps bypass bot-blocking on large corporate sites (free 14-day trial at scraperapi.com).
</div>""", unsafe_allow_html=True)

    if _using_own_keys():
        # Refresh active keys immediately
        serp_key, gemini_api_key, pagespeed_api_key, _scraperapi_key = _active_keys()
        if _scraperapi_key:
            os.environ["SCRAPER_API_KEY"] = _scraperapi_key
        st.success("✅ Using your own API keys — unlimited access enabled.")

st.markdown("<br>", unsafe_allow_html=True)

# ==================== ACTION BUTTONS ====================

col_btn1, col_btn2, col_spacer = st.columns([2, 2, 3])

with col_btn1:
    analyze_clicked = st.button("🔍 Analyze SEO", use_container_width=True, type="primary")

with col_btn2:
    competitors_clicked = st.button("🎯 Find Competitors", use_container_width=True, type="secondary")

# ==================== ANALYZE SECTION ====================

if analyze_clicked:
    _allowed, _remaining = _check_limit()
    if not _allowed:
        st.markdown("""
<div style="background:rgba(176,32,37,0.1);border:1px solid rgba(176,32,37,0.3);
            border-radius:12px;padding:1.2rem 1.6rem;">
    <div style="font-size:0.75rem;font-weight:800;color:#FF5252;letter-spacing:0.1em;
                text-transform:uppercase;margin-bottom:0.4rem;">Free Try Limit Reached</div>
    <div style="font-size:0.88rem;color:rgba(255,255,255,0.6);">
        You've used your <strong>2 complimentary analyses</strong> from this IP address.<br>
        Click <strong style="color:#7EC7A3;">+ USE YOUR OWN API KEYS</strong> above to continue with unlimited access using your own free API keys.
    </div>
</div>""", unsafe_allow_html=True)
        st.stop()
    
    if url and keyword:
        try:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("📄 Fetching page content...")
            progress_bar.progress(20)
            time.sleep(0.3)
            
            st.session_state.keyword = keyword
            st.session_state.url = url

            soup, raw_html = get_page_soup(url)

            status_text.text("🔍 Extracting SEO elements...")
            progress_bar.progress(40)
            time.sleep(0.3)

            title = get_title(soup)
            meta = get_meta_description(soup)
            h1 = get_h1_tags(soup)
            text = get_text_content(soup)

            wc = count_words(text)
            kc = count_keyword(text, keyword)
            kd = keyword_density(text, keyword)

            token_counts, partial_match_total = count_partial_keyword_matches(text, keyword)
            token_coverage = keyword_token_coverage(text, keyword)

            internal, external = get_links(soup, url)
            missing_alt = get_images_missing_alt(soup)

            title_has_keyword = keyword_in_title(title, keyword)
            meta_has_keyword = keyword_in_meta(meta, keyword)
            h1_has_keyword = keyword_in_h1(h1, keyword)

            title_len = title_length(title)
            meta_len = meta_description_length(meta)
            
            # Technical SEO checks
            status_text.text("⚙️ Running technical SEO audit...")
            progress_bar.progress(60)
            time.sleep(0.3)
            
            tech_seo = check_technical_seo(url, soup)
            has_schema = has_schema_markup(soup)

            status_text.text("📊 Calculating SEO score...")
            progress_bar.progress(80)
            time.sleep(0.3)

            score, recs = calculate_seo_score(
                title,
                meta,
                h1,
                kc,
                wc,
                len(missing_alt),
                title_has_keyword,
                meta_has_keyword,
                h1_has_keyword,
                title_len,
                meta_len,
                internal_links_count=len(internal),
                external_links_count=len(external),
                has_schema=has_schema,
                https_enabled=tech_seo.get('https_enabled', False),
                mobile_viewport=tech_seo.get('mobile_viewport', False)
            )

            summary = get_executive_summary(
                score=score,
                keyword_count=kc,
                missing_alt_count=len(missing_alt),
                word_count=wc
            )

            pagespeed_data = None
            if pagespeed_api_key:
                try:
                    status_text.text("⚡ Fetching PageSpeed data...")
                    progress_bar.progress(90)
                    pagespeed_data = get_pagespeed_data(url, pagespeed_api_key, strategy="mobile")
                except Exception:
                    pass  # PageSpeed is optional; skip silently on timeout/error

            recommended_fixes = build_recommended_fixes(
                title_has_keyword=title_has_keyword,
                meta_has_keyword=meta_has_keyword,
                h1_has_keyword=h1_has_keyword,
                kc=kc,
                title_len=title_len,
                meta_len=meta_len,
                missing_alt_count=len(missing_alt),
                pagespeed_data=pagespeed_data,
                https_enabled=tech_seo.get('https_enabled', False),
                mobile_viewport=tech_seo.get('mobile_viewport', False),
                has_schema=has_schema
            )

            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()

            # Increment IP usage counter
            if not _using_own_keys():
                _increment_ip_uses(_ip_hash)
            _render_badge(_badge_placeholder)

            # ==================== DISPLAY RESULTS ====================
            
            st.success("✅ Analysis Complete!")
            st.markdown("---")

            # Tabs for organized display
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🔧 Technical SEO", "📝 Content Analysis", "🎯 Recommendations", "🤖 GEO Score"])

            with tab1:
                # Score Gauge + Key Metrics
                col_gauge, col_metrics = st.columns([2, 3])
                
                with col_gauge:
                    st.plotly_chart(create_score_gauge(score), use_container_width=True)
                    st.markdown(f"**Score Band:** {get_score_band(score)}")

                with col_metrics:
                    # ── KPI cards row ────────────────────────────────────
                    st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)
                    kc1, kc2, kc3 = st.columns(3)
                    kc1.markdown(kpi_card_html("Word Count", f"{wc:,}", "#667eea", "📝"), unsafe_allow_html=True)
                    kc2.markdown(kpi_card_html("Keyword Hits", kc, "#00C853" if kc >= 3 else "#EF5350", "🔑"), unsafe_allow_html=True)
                    kc3.markdown(kpi_card_html("Keyword Density", f"{kd}%", "#FFA726", "📊"), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    kc4, kc5, kc6 = st.columns(3)
                    kc4.markdown(kpi_card_html("Internal Links", len(internal), "#26C6DA", "🔗"), unsafe_allow_html=True)
                    kc5.markdown(kpi_card_html("External Links", len(external), "#AB47BC", "🌐"), unsafe_allow_html=True)
                    kc6.markdown(kpi_card_html("Missing ALTs", len(missing_alt), "#EF5350" if missing_alt else "#00C853", "🖼️"), unsafe_allow_html=True)

                # ── Row 2: Radar + SEO factors bar + Link donut ──────────
                st.markdown("---")
                r2a, r2b, r2c = st.columns([1.1, 1.1, 0.9])

                with r2a:
                    # Radar chart: on-page SEO factors
                    radar_cats = ["Title", "Meta", "H1", "Keyword\nDensity", "Word\nCount", "Links", "Schema"]
                    radar_vals = [
                        100 if title_has_keyword else 30,
                        100 if meta_has_keyword else 30,
                        100 if h1_has_keyword else 30,
                        min(100, int(kd * 20)) if kd else 0,
                        min(100, int(wc / 15)),
                        min(100, len(internal) * 5 + len(external) * 3),
                        100 if has_schema else 0,
                    ]
                    st.plotly_chart(create_radar_chart(radar_cats, radar_vals, "On-Page SEO Factors"), use_container_width=True)

                with r2b:
                    # Horizontal bar: factor scores
                    bar_labels = ["Title Tag", "Meta Desc", "H1 Tag", "Keyword Use", "Content Depth", "Alt Text", "Schema"]
                    bar_vals = [
                        100 if title_has_keyword else (50 if title_len > 10 else 20),
                        100 if meta_has_keyword else (50 if meta_len > 50 else 20),
                        100 if h1_has_keyword else (40 if h1 else 0),
                        min(100, kc * 15),
                        min(100, int(wc / 10)),
                        max(0, 100 - len(missing_alt) * 10),
                        100 if has_schema else 0,
                    ]
                    st.plotly_chart(create_horizontal_bar(bar_labels, bar_vals, title="Factor Scores"), use_container_width=True)

                with r2c:
                    # Donut: link composition
                    total_links = len(internal) + len(external) or 1
                    st.plotly_chart(create_donut_chart(
                        labels=["Internal", "External"],
                        values=[len(internal), max(len(external), 1)],
                        colors=["#667eea", "#26C6DA"],
                        title="Link Distribution",
                        center_text=f"{total_links}<br>links"
                    ), use_container_width=True)

                # ── Row 3: Keyword status donut + executive summary ───────
                st.markdown("---")
                r3a, r3b = st.columns([1, 2])

                with r3a:
                    kw_present = sum([title_has_keyword, meta_has_keyword, h1_has_keyword, kc > 0])
                    st.plotly_chart(create_donut_chart(
                        labels=["Title", "Meta", "H1", "Body"],
                        values=[1 if title_has_keyword else 0, 1 if meta_has_keyword else 0,
                                1 if h1_has_keyword else 0, 1 if kc > 0 else 0],
                        colors=["#00C853", "#FFA726", "#667eea", "#26C6DA"],
                        title="Keyword Placement",
                        center_text=f"{kw_present}/4<br><span style='font-size:11px'>covered</span>"
                    ), use_container_width=True)

                with r3b:
                    st.markdown("<div class='section-header'>Executive Summary</div>", unsafe_allow_html=True)
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        st.info(f"**Status** — {summary['Overall Status']}")
                        st.success(f"**Strength** — {summary['Strongest Area']}")
                    with sc2:
                        st.warning(f"**Top Issue** — {summary['Top Issue']}")
                        st.error(f"**Priority** — {summary['Priority Action']}")

            with tab2:
                st.markdown("### 🔧 Technical SEO Audit")

                # Technical score bar chart
                tech_factors = {
                    "HTTPS": tech_seo.get('https_enabled', False),
                    "Canonical URL": tech_seo.get('has_canonical', False),
                    "Indexable": not tech_seo.get('robots_noindex', True),
                    "Mobile Viewport": tech_seo.get('mobile_viewport', False),
                    "Language Tag": tech_seo.get('has_lang', False),
                    "Single H1": tech_seo.get('proper_h1_usage', False),
                    "Open Graph": tech_seo.get('has_og_title', False),
                    "Twitter Card": tech_seo.get('has_twitter_card', False),
                    "Schema Markup": has_schema,
                }
                t_labels = list(tech_factors.keys())
                t_vals = [100 if v else 0 for v in tech_factors.values()]
                t_colors = ["#00C853" if v else "#EF5350" for v in tech_factors.values()]
                st.plotly_chart(create_horizontal_bar(t_labels, t_vals, t_colors, "Technical Audit Score (100 = Pass, 0 = Fail)"), use_container_width=True)

                tech_col1, tech_col2 = st.columns(2)
                
                with tech_col1:
                    st.markdown("#### Security & Protocol")
                    st.markdown(status_indicator(tech_seo.get('https_enabled', False), "HTTPS Enabled"), unsafe_allow_html=True)
                    st.markdown(status_indicator(tech_seo.get('has_canonical', False), "Canonical URL"), unsafe_allow_html=True)
                    st.markdown(status_indicator(not tech_seo.get('robots_noindex', True), "Indexable (No noindex)"), unsafe_allow_html=True)
                    
                    st.markdown("#### Structured Data")
                    st.markdown(status_indicator(has_schema, "Schema Markup"), unsafe_allow_html=True)
                    if has_schema:
                        schemas = detect_schema_markup(soup)
                        if schemas['json_ld']:
                            st.info(f"**JSON-LD Types:** {', '.join(schemas['json_ld'])}")
                
                with tech_col2:
                    st.markdown("#### Mobile & Accessibility")
                    st.markdown(status_indicator(tech_seo.get('mobile_viewport', False), "Mobile Viewport"), unsafe_allow_html=True)
                    st.markdown(status_indicator(tech_seo.get('has_lang', False), "Language Attribute"), unsafe_allow_html=True)
                    st.markdown(status_indicator(tech_seo.get('proper_h1_usage', False), "Single H1 Tag"), unsafe_allow_html=True)
                    
                    st.markdown("#### Social Media")
                    st.markdown(status_indicator(tech_seo.get('has_og_title', False), "Open Graph Title"), unsafe_allow_html=True)
                    st.markdown(status_indicator(tech_seo.get('has_twitter_card', False), "Twitter Card"), unsafe_allow_html=True)

            with tab3:
                st.markdown("### 📝 Content Analysis")
                
                content_col1, content_col2 = st.columns(2)
                
                with content_col1:
                    st.markdown("#### On-Page Elements")
                    st.text_input("Title", value=title, disabled=True)
                    st.text_area("Meta Description", value=meta, height=80, disabled=True)
                    st.text_input("H1 Tags", value=", ".join(h1) if h1 else "None", disabled=True)
                    
                with content_col2:
                    st.markdown("#### Keyword Analysis")
                    st.markdown(f"**Keyword in Title:** {'✅ Yes' if title_has_keyword else '❌ No'}")
                    st.markdown(f"**Keyword in Meta:** {'✅ Yes' if meta_has_keyword else '❌ No'}")
                    st.markdown(f"**Keyword in H1:** {'✅ Yes' if h1_has_keyword else '❌ No'}")
                    st.markdown(f"**Token Coverage:** {token_coverage}%")
                    
                    if token_counts:
                        st.markdown("**Individual Token Counts:**")
                        for token, count in token_counts.items():
                            st.markdown(f"- *{token}*: {count} times")

            with tab4:
                st.markdown("### 🎯 Recommended Actions")
                
                # Group recommendations by priority
                critical = [r for r in recommended_fixes if "CRITICAL" in r['Priority']]
                high = [r for r in recommended_fixes if "HIGH" in r['Priority']]
                medium = [r for r in recommended_fixes if "MEDIUM" in r['Priority']]
                excellent = [r for r in recommended_fixes if "EXCELLENT" in r['Priority']]
                
                if critical:
                    with st.expander(f"🔴 CRITICAL Issues ({len(critical)})", expanded=True):
                        for rec in critical:
                            st.error(f"**{rec['Issue']}**\n\n💡 {rec['Recommended Fix']}\n\n📊 Impact: {rec['Impact']}")
                
                if high:
                    with st.expander(f"🟠 HIGH Priority ({len(high)})", expanded=False):
                        for rec in high:
                            st.warning(f"**{rec['Issue']}**\n\n💡 {rec['Recommended Fix']}\n\n📊 Impact: {rec['Impact']}")
                
                if medium:
                    with st.expander(f"🟡 MEDIUM Priority ({len(medium)})", expanded=False):
                        for rec in medium:
                            st.info(f"**{rec['Issue']}**\n\n💡 {rec['Recommended Fix']}\n\n📊 Impact: {rec['Impact']}")
                
                if excellent:
                    with st.expander(f"✅ Status: Excellent", expanded=False):
                        for rec in excellent:
                            st.success(f"**{rec['Issue']}**\n\n{rec['Recommended Fix']}")

            with tab5:
                st.markdown("### 🤖 GEO Score — AI Search Visibility")
                st.caption("How well this page is optimized for ChatGPT, Claude, Perplexity, and Google AI Overviews")

                with st.spinner("Running GEO analysis..."):
                    geo_crawlers   = check_ai_crawlers(url)
                    geo_citability = score_citability(soup)
                    geo_llmstxt    = check_llmstxt(url)
                    geo_eeat       = check_eeat(soup, url)
                    geo_result     = calculate_geo_score(
                        crawler_score    = geo_crawlers["score"],
                        citability_score = geo_citability["score"],
                        eeat_score       = geo_eeat["score"],
                        llmstxt_exists   = geo_llmstxt["exists"],
                        has_schema       = has_schema
                    )

                # ── GEO Score gauge ──────────────────────────────────────
                geo_col1, geo_col2 = st.columns([2, 3])
                with geo_col1:
                    st.plotly_chart(
                        create_score_gauge(geo_result["score"], title="GEO Score"),
                        use_container_width=True
                    )
                    st.markdown(f"**Band:** {geo_result['band']}")

                with geo_col2:
                    st.markdown("#### 📊 Score Breakdown")
                    breakdown = geo_result["breakdown"]
                    for key, data in breakdown.items():
                        label = {"citability": "Content Citability", "eeat": "E-E-A-T",
                                 "crawlers": "AI Crawler Access", "schema": "Schema Markup",
                                 "llmstxt": "llms.txt"}.get(key, key)
                        bar_pct = int(data["score"])
                        st.markdown(f"**{label}** — {bar_pct}/100")
                        st.progress(bar_pct / 100)

                st.markdown("---")

                # ── AI Crawler Access ────────────────────────────────────
                geo_c1, geo_c2 = st.columns(2)

                with geo_c1:
                    st.markdown("#### 🤖 AI Crawler Access")
                    st.caption(f"robots.txt score: **{geo_crawlers['score']}/100**")
                    for crawler in geo_crawlers["crawlers"]:
                        icon = "✅" if crawler["status"] == "allowed" else ("❌" if crawler["status"] == "blocked" else "⚠️")
                        badge = "🔴" if crawler["priority"] == "critical" else "🟡"
                        st.markdown(f"{icon} {badge} **{crawler['name']}** — {crawler['status']}")
                    sitemap_icon = "✅" if geo_crawlers["has_sitemap"] else "❌"
                    st.markdown(f"{sitemap_icon} Sitemap in robots.txt")

                with geo_c2:
                    st.markdown("#### 📄 llms.txt & E-E-A-T")

                    # llms.txt
                    if geo_llmstxt["exists"]:
                        st.success(f"✅ llms.txt found — {geo_llmstxt['sections']} sections, {geo_llmstxt['links']} links")
                    else:
                        st.warning("❌ No llms.txt found — consider adding one to guide AI crawlers")
                        st.markdown("[What is llms.txt?](https://llmstxt.org)")

                    st.markdown("**E-E-A-T Signals**")
                    signals = geo_eeat["signals"]
                    eeat_items = [
                        ("Author byline",    signals.get("has_author", False)),
                        ("Publication date", signals.get("has_date", False)),
                        ("About page",       signals.get("has_about", False)),
                        ("Contact page",     signals.get("has_contact", False)),
                        ("Privacy policy",   signals.get("has_privacy", False)),
                        ("HTTPS",            signals.get("has_https", False)),
                    ]
                    for label, passed in eeat_items:
                        st.markdown(status_indicator(passed, label), unsafe_allow_html=True)

                st.markdown("---")

                # ── Citability ───────────────────────────────────────────
                st.markdown("#### ✍️ Content Citability")
                st.caption("How likely AI models are to directly quote/cite content from this page")
                cit_col1, cit_col2, cit_col3 = st.columns(3)
                with cit_col1:
                    st.metric("Citability Score", f"{geo_citability['score']}/100")
                with cit_col2:
                    st.metric("Grade", f"{geo_citability['grade']} — {geo_citability['grade_label']}")
                with cit_col3:
                    st.metric("Optimal Blocks", f"{geo_citability['optimal_blocks']} / {geo_citability['blocks_analyzed']}")

                if geo_citability.get("top_blocks"):
                    with st.expander("📋 Top Citable Content Blocks", expanded=False):
                        for block in geo_citability["top_blocks"][:3]:
                            st.markdown(f"**{block.get('heading', 'No heading')}** — Score: {block['score']}/100 ({block['grade']}) | {block['word_count']} words")
                            st.caption(block.get("preview", ""))
                            st.markdown("---")

            # PageSpeed Section (if available)
            if pagespeed_data:
                st.markdown("---")
                st.markdown("### ⚡ PageSpeed Insights (Mobile)")
                
                ps_cols = st.columns(4)
                
                with ps_cols[0]:
                    perf_score = int(pagespeed_data.get("performance_score", 0) * 100)
                    st.metric("Performance", f"{perf_score}/100")
                
                with ps_cols[1]:
                    acc_score = int(pagespeed_data.get("accessibility_score", 0) * 100)
                    st.metric("Accessibility", f"{acc_score}/100")
                
                with ps_cols[2]:
                    bp_score = int(pagespeed_data.get("best_practices_score", 0) * 100)
                    st.metric("Best Practices", f"{bp_score}/100")
                
                with ps_cols[3]:
                    seo_score = int(pagespeed_data.get("seo_score", 0) * 100)
                    st.metric("SEO", f"{seo_score}/100")
                
                st.markdown("**Core Web Vitals:**")
                vital_cols = st.columns(5)
                
                with vital_cols[0]:
                    st.text(f"FCP: {pagespeed_data.get('first_contentful_paint', 'N/A')}")
                with vital_cols[1]:
                    st.text(f"LCP: {pagespeed_data.get('largest_contentful_paint', 'N/A')}")
                with vital_cols[2]:
                    st.text(f"SI: {pagespeed_data.get('speed_index', 'N/A')}")
                with vital_cols[3]:
                    st.text(f"TBT: {pagespeed_data.get('total_blocking_time', 'N/A')}")
                with vital_cols[4]:
                    st.text(f"CLS: {pagespeed_data.get('cumulative_layout_shift', 'N/A')}")

            # Comparison Section (if URL provided)
            if compare_url:
                st.markdown("---")
                st.markdown("### 📊 Side-by-Side Comparison")
                
                try:
                    comp_soup, _ = get_page_soup(compare_url)
                    comp_title = get_title(comp_soup)
                    comp_meta = get_meta_description(comp_soup)
                    comp_h1 = get_h1_tags(comp_soup)
                    comp_text = get_text_content(comp_soup)
                    comp_wc = count_words(comp_text)
                    comp_kc = count_keyword(comp_text, keyword)
                    comp_kd = keyword_density(comp_text, keyword)
                    comp_internal, comp_external = get_links(comp_soup, compare_url)
                    comp_missing_alt = get_images_missing_alt(comp_soup)
                    comp_tech = check_technical_seo(compare_url, comp_soup)
                    comp_has_schema = has_schema_markup(comp_soup)
                    
                    comp_score, _ = calculate_seo_score(
                        comp_title, comp_meta, comp_h1, comp_kc, comp_wc,
                        len(comp_missing_alt),
                        keyword_in_title(comp_title, keyword),
                        keyword_in_meta(comp_meta, keyword),
                        keyword_in_h1(comp_h1, keyword),
                        title_length(comp_title),
                        meta_description_length(comp_meta),
                        len(comp_internal), len(comp_external),
                        comp_has_schema,
                        comp_tech.get('https_enabled', False),
                        comp_tech.get('mobile_viewport', False)
                    )
                    
                    comp_data = {
                        "Metric": ["SEO Score", "Word Count", "Keyword Count", "Keyword Density", 
                                  "Internal Links", "External Links", "Missing ALT"],
                        "Primary Venue": [score, wc, kc, f"{kd}%", len(internal), len(external), len(missing_alt)],
                        "Comparison Venue": [comp_score, comp_wc, comp_kc, f"{comp_kd}%", 
                                           len(comp_internal), len(comp_external), len(comp_missing_alt)],
                        "Winner": [
                            compare_metric(score, comp_score),
                            compare_metric(wc, comp_wc),
                            compare_metric(kc, comp_kc),
                            compare_metric(kd, comp_kd),
                            compare_metric(len(internal), len(comp_internal)),
                            compare_metric(len(external), len(comp_external)),
                            compare_metric(len(missing_alt), len(comp_missing_alt), higher_is_better=False)
                        ]
                    }
                    
                    st.dataframe(pd.DataFrame(comp_data), use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error analyzing comparison URL: {e}")

            # Multi-Venue Leaderboard
            if venue_urls_text.strip():
                st.markdown("---")
                st.markdown("### 🏆 Multi-Venue Leaderboard")
                
                venue_urls = [u.strip() for u in venue_urls_text.strip().split("\n") if u.strip()]
                
                if venue_urls:
                    leaderboard_progress = st.progress(0)
                    leaderboard_rows = []
                    
                    for idx, venue_url in enumerate(venue_urls):
                        try:
                            leaderboard_progress.progress((idx + 1) / len(venue_urls))
                            venue_data = analyze_venue(venue_url, keyword)
                            leaderboard_rows.append(venue_data)
                        except Exception:
                            st.warning(f"Could not analyze: {venue_url}")
                    
                    leaderboard_progress.empty()
                    
                    if leaderboard_rows:
                        leaderboard_df = pd.DataFrame(leaderboard_rows)
                        leaderboard_df = leaderboard_df.sort_values(by="SEO Score", ascending=False)
                        
                        st.dataframe(leaderboard_df, use_container_width=True)
                        
                        chart = px.bar(
                            leaderboard_df.reset_index(),
                            x="Venue Name",
                            y="SEO Score",
                            color="Score Band",
                            text="SEO Score",
                            title="Venue SEO Score Comparison"
                        )
                        
                        st.plotly_chart(chart, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Analysis Error: {e}")
            st.info("Please check the URL is valid and accessible.")
    else:
        st.warning("⚠️ Please enter both URL and keyword to analyze.")

# ==================== COMPETITORS SECTION ====================

if competitors_clicked:
    _allowed, _remaining = _check_limit()
    if not _allowed:
        st.markdown("""
<div style="background:rgba(176,32,37,0.1);border:1px solid rgba(176,32,37,0.3);
            border-radius:12px;padding:1.2rem 1.6rem;">
    <div style="font-size:0.75rem;font-weight:800;color:#FF5252;letter-spacing:0.1em;
                text-transform:uppercase;margin-bottom:0.4rem;">Free Try Limit Reached</div>
    <div style="font-size:0.88rem;color:rgba(255,255,255,0.6);">
        You've used your <strong>2 complimentary analyses</strong> from this IP address.<br>
        Click <strong style="color:#7EC7A3;">+ USE YOUR OWN API KEYS</strong> above to continue with unlimited access.
    </div>
</div>""", unsafe_allow_html=True)
        st.stop()
    elif not keyword:
        st.error("❌ Please enter a target keyword first.")
    elif not url:
        st.error("❌ Please enter the Primary Venue URL first.")
    elif not gemini_api_key:
        st.error("❌ Gemini API key not configured. Add GEMINI_API_KEY to Streamlit secrets.")
    else:
        if not _using_own_keys():
            _increment_ip_uses(_ip_hash)
        _render_badge(_badge_placeholder)
        try:
            from competitor_utils import get_competitors_via_gemini
            from location_utils import get_location_from_url

            st.markdown("---")

            # ── Step 1: Ask Gemini for competitors ──────────────────────────
            location = get_location_from_url(url)
            country = location['country_name'] if location and location.get('country_name') else "global"

            with st.spinner(f"🤖 Asking AI: who are the local competitors of {url} for '{keyword}'?"):
                try:
                    gemini_competitors = get_competitors_via_gemini(url, keyword, gemini_api_key, location)
                except Exception as e:
                    err_str = str(e)
                    if "QUOTA_429||" in err_str:
                        raw_google = err_str.split("QUOTA_429||", 1)[1]
                        raw_lower = raw_google.lower()
                        if "spending" in raw_lower or "spend" in raw_lower:
                            st.error("💳 **Gemini spending cap exceeded.** The API key's project has hit its monthly spend cap.")
                            st.info(f"📋 **Google's exact message:** `{raw_google[:300]}`\n\n👉 Go to [aistudio.google.com/spend](https://aistudio.google.com/spend) — make sure the **project** matches the one your API key belongs to.")
                        elif "resource_exhausted" in raw_lower or "quota" in raw_lower or "rate" in raw_lower:
                            st.warning("⏱️ **Gemini rate limit hit** — too many requests per minute. Wait 30–60 seconds and click Find Competitors again.")
                            st.info(f"📋 **Google's exact message:** `{raw_google[:200]}`")
                        else:
                            st.error(f"❌ **Gemini 429 error.** Google's raw response: `{raw_google[:300]}`")
                    elif "INVALID_API_KEY" in err_str:
                        raw_google = err_str.split("||", 1)[1] if "||" in err_str else err_str
                        st.error("🔑 **Gemini API key is invalid or rejected.**")
                        st.info(f"📋 Google says: `{raw_google[:200]}`\n\nIn Streamlit Cloud → App settings → Secrets, verify `GEMINI_API_KEY = \"AIza...\"` is correct and from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).")
                    elif "INVALID_API_KEY" in err_str or "FORBIDDEN" in err_str or "403" in err_str:
                        st.error("🚫 **Gemini API not enabled** for this key's project.")
                        st.info("Enable the Generative Language API at console.cloud.google.com → APIs & Services.")
                    elif "ALL_FAILED||" in err_str:
                        detail = err_str.split("ALL_FAILED||", 1)[1]
                        st.error(f"❌ **All Gemini models failed.** {detail}")
                    else:
                        st.error(f"❌ Gemini failed: {e}")
                    gemini_competitors = []

            if not gemini_competitors:
                st.stop()

            st.success(f"✅ AI identified {len(gemini_competitors)} competitors ({country})")

            # ── Step 2: Analyze primary venue ───────────────────────────────
            st.markdown(f"""
<div style="background:#0d0d0d;border:1px solid rgba(176,32,37,0.2);border-radius:14px;
            padding:1.6rem 2rem;margin:1.2rem 0 0.8rem;">
    <div style="font-size:0.6rem;font-weight:800;color:#B02025;letter-spacing:0.18em;
                text-transform:uppercase;margin-bottom:0.5rem;">Competitive Intelligence</div>
    <div style="font-size:1.3rem;font-weight:800;color:#fff;margin-bottom:0.3rem;">
        SEO Score Comparison
    </div>
    <div style="font-size:0.85rem;color:rgba(255,255,255,0.4);">
        Benchmarking <strong style="color:rgba(255,255,255,0.7);">{url}</strong>
        against <strong style="color:#B02025;">{len(gemini_competitors)}</strong> competitors
        &nbsp;·&nbsp; keyword: <strong style="color:rgba(255,255,255,0.7);">{keyword}</strong>
    </div>
</div>
""", unsafe_allow_html=True)

            benchmark_rows = []
            progress = st.progress(0)
            total = len(gemini_competitors) + 1
            st.markdown("""
<div style="background:rgba(126,199,163,0.06);border:1px solid rgba(126,199,163,0.15);
            border-left:3px solid #7EC7A3;border-radius:10px;padding:0.9rem 1.2rem;
            font-size:0.83rem;color:rgba(255,255,255,0.6);line-height:1.6;">
    <strong style="color:#7EC7A3;">Processing in progress</strong> — fetching and scoring each site.
    The page may appear idle but analysis is running in the background.
    Typical completion: <strong style="color:rgba(255,255,255,0.75);">2–4 minutes</strong>.
</div>
""", unsafe_allow_html=True)

            with st.spinner("Analyzing primary venue..."):
                try:
                    primary_data = analyze_venue(url, keyword)
                    primary_data["Role"] = "🏠 Primary Venue"
                    benchmark_rows.append(primary_data)
                except Exception as e:
                    st.warning(f"Could not analyze primary URL: {e}")
            progress.progress(1 / total)

            # ── Step 3: Analyze each competitor ─────────────────────────────
            for idx, comp in enumerate(gemini_competitors):
                comp_url = comp.get("website") or f"https://{comp.get('domain', '')}"
                comp_name = comp.get("name", comp_url)
                if not comp_url or comp_url == "https://":
                    continue
                with st.spinner(f"Analyzing competitor {idx+1}/{len(gemini_competitors)}: {comp_name}..."):
                    try:
                        row = analyze_venue(comp_url, keyword)
                        row["Role"] = "🎯 Competitor"
                        benchmark_rows.append(row)
                    except Exception:
                        benchmark_rows.append({
                            "Venue Name": comp_name,
                            "URL": comp_url,
                            "SEO Score": 0,
                            "Score Band": "Blocked",
                            "Role": "🎯 Competitor",
                            "Word Count": 0, "Keyword Count": 0,
                            "Keyword Density": 0, "Internal Links": 0,
                            "External Links": 0, "Images Missing ALT": 0,
                            "HTTPS": "✗", "Schema": "✗"
                        })
                progress.progress((idx + 2) / total)

            progress.empty()

            if not benchmark_rows:
                st.warning("No data to display.")
                st.stop()

            # ── Step 4: Display score comparison ────────────────────────────
            benchmark_df = pd.DataFrame(benchmark_rows)

            # Separate blocked from valid results
            error_rows = [r for r in benchmark_rows if r.get("Score Band") == "Blocked"]
            valid_rows = [r for r in benchmark_rows if r.get("Score Band") != "Blocked"]

            if error_rows:
                blocked = [r["Venue Name"] for r in error_rows]
                st.warning(f"⚠️ {len(error_rows)} site(s) blocked automated access (common for large corporate sites): {', '.join(blocked)}")

            primary_row = next((r for r in valid_rows if "Primary" in r.get("Role", "")), None)

            if not primary_row:
                st.error(f"❌ Could not fetch **{url}** — the site blocks automated requests. Try a different URL that doesn't block bots.")
                # Still show competitors if we have them
                valid_comp_rows = [r for r in valid_rows if "Competitor" in r.get("Role", "")]
                if valid_comp_rows:
                    st.markdown("### 📊 Competitor Scores (primary site unavailable)")

            # Score bar chart — primary + top 10 competitors by score
            if valid_rows:
                primary_valid = [r for r in valid_rows if "Primary" in r.get("Role", "")]
                comp_valid = sorted(
                    [r for r in valid_rows if "Competitor" in r.get("Role", "")],
                    key=lambda x: x.get("SEO Score", 0), reverse=True
                )[:10]
                chart_rows = primary_valid + comp_valid
                valid_df = pd.DataFrame(chart_rows)
                # Short label: domain only
                from urllib.parse import urlparse as _up
                valid_df["Label"] = valid_df["URL"].apply(
                    lambda u: _up(u).netloc.replace("www.", "") if u else ""
                )
                # Sort by score ascending so highest is at top of horizontal chart
                valid_df = valid_df.sort_values("SEO Score", ascending=True)
                fig = px.bar(
                    valid_df,
                    x="SEO Score",
                    y="Label",
                    color="Role",
                    text="SEO Score",
                    orientation="h",
                    color_discrete_map={"🏠 Primary Venue": "#B02025", "🎯 Competitor": "#3a3a3a"},
                    title=f"SEO Score vs Competitors — '{keyword}'"
                )
                fig.update_traces(textposition="outside", textfont_size=11,
                                  marker_line_width=0)
                chart_height = max(380, len(chart_rows) * 38)
                fig.update_layout(
                    height=chart_height,
                    showlegend=True,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="rgba(255,255,255,0.7)", family="Outfit"),
                    title_font=dict(size=13, color="rgba(255,255,255,0.5)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
                    margin=dict(l=10, r=60, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Summary metrics
            if primary_row:
                best_comp = max(
                    [r for r in valid_rows if "Competitor" in r.get("Role", "")],
                    key=lambda x: x.get("SEO Score", 0),
                    default={}
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Your SEO Score", primary_row.get("SEO Score", 0))
                m2.metric("Best Competitor Score", best_comp.get("SEO Score", "N/A") if best_comp else "N/A")
                if best_comp:
                    gap = primary_row.get("SEO Score", 0) - best_comp.get("SEO Score", 0)
                    m3.metric("Gap vs Best", f"{gap:+d}", delta_color="normal")
                all_comps = [r for r in benchmark_rows if "Competitor" in r.get("Role","")]
                m4.metric("Competitors Analysed", len(all_comps))

            # Full data table — all rows including errors
            st.markdown("""<div style="font-size:0.6rem;font-weight:800;color:#B02025;
                letter-spacing:0.18em;text-transform:uppercase;margin:1.5rem 0 0.5rem;">
                Full Comparison — All Venues</div>""", unsafe_allow_html=True)
            display_cols = ["Role", "Venue Name", "SEO Score", "Score Band", "Word Count", "HTTPS", "Schema"]
            available_cols = [c for c in display_cols if c in benchmark_df.columns]
            st.dataframe(benchmark_df[available_cols], use_container_width=True)

            # ── Step 5: AI Executive Summary ────────────────────────────────
            if primary_row and gemini_api_key:
                st.markdown("""
<div style="font-size:0.6rem;font-weight:800;color:#B02025;letter-spacing:0.18em;
            text-transform:uppercase;margin:2rem 0 0.8rem;">AI Executive Report</div>
""", unsafe_allow_html=True)
                best_comp_name = best_comp.get("Venue Name", "top competitor") if best_comp else "N/A"

                insights = generate_strategic_insights(
                    primary_row=primary_row,
                    benchmark_rows=benchmark_rows,
                    keyword=keyword
                )

                with st.spinner("Generating AI analysis report..."):
                    ai_summary = generate_ai_executive_summary(
                        gemini_api_key=gemini_api_key,
                        primary_name=primary_row.get("Venue Name", url),
                        keyword=keyword,
                        primary_rank="N/A",
                        primary_score=primary_row.get("SEO Score", 0),
                        top_competitor=best_comp_name,
                        strategic_insights=insights,
                        recommended_fixes=[],
                        benchmark_rows=benchmark_rows,
                    )
                if ai_summary:
                    # Parse sections and render as styled cards
                    import re as _re
                    section_colors = {
                        "executive summary": "#7EC7A3",
                        "strengths": "#4CAF50",
                        "weaknesses": "#FF5252",
                        "keyword": "#FF9800",
                        "technical": "#B02025",
                        "competitor": "#667eea",
                        "priority": "#FFD600",
                        "conclusion": "#7EC7A3",
                    }
                    sections = _re.split(r'\n##\s+', "\n" + ai_summary)
                    for sec in sections:
                        if not sec.strip():
                            continue
                        lines = sec.strip().split("\n", 1)
                        title = lines[0].strip().lstrip("#").strip()
                        body = lines[1].strip() if len(lines) > 1 else ""
                        color = "#B02025"
                        for k, v in section_colors.items():
                            if k in title.lower():
                                color = v
                                break
                        # Convert markdown bold/bullets to HTML
                        body_html = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        body_html = _re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:rgba(255,255,255,0.9);">\1</strong>', body_html)
                        body_html = _re.sub(r'^\s*[-•]\s+', '<li>', body_html, flags=_re.MULTILINE)
                        body_html = _re.sub(r'^\s*\d+\.\s+', '<li style="margin-bottom:0.4rem">', body_html, flags=_re.MULTILINE)
                        body_html = body_html.replace("\n", "<br>")
                        st.markdown(f"""
<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);
            border-left:3px solid {color};border-radius:12px;
            padding:1.4rem 1.8rem;margin-bottom:1rem;">
    <div style="font-size:0.7rem;font-weight:800;letter-spacing:0.14em;
                text-transform:uppercase;color:{color};margin-bottom:0.8rem;">{title}</div>
    <div style="font-size:0.88rem;color:rgba(255,255,255,0.65);line-height:1.75;">{body_html}</div>
</div>
""", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Competitor analysis error: {e}")
