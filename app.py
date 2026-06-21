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

# ==================== GLOBAL RATE LIMITING (Upstash Redis) ====================
GLOBAL_LIMIT = 30  # shared pool across ALL users

_upstash_url = ""
_upstash_token = ""
try:
    _upstash_url   = st.secrets["UPSTASH_REDIS_REST_URL"]
    _upstash_token = st.secrets["UPSTASH_REDIS_REST_TOKEN"]
except Exception:
    pass

def _redis_get(key):
    if not _upstash_url or not _upstash_token:
        return 0
    try:
        import requests as _r
        resp = _r.get(
            f"{_upstash_url}/get/{key}",
            headers={"Authorization": f"Bearer {_upstash_token}"},
            timeout=5
        )
        val = resp.json().get("result")
        return int(val) if val else 0
    except Exception:
        return 0

def _redis_incr(key):
    if not _upstash_url or not _upstash_token:
        return 1
    try:
        import requests as _r
        resp = _r.get(
            f"{_upstash_url}/incr/{key}",
            headers={"Authorization": f"Bearer {_upstash_token}"},
            timeout=5
        )
        return int(resp.json().get("result", 1))
    except Exception:
        return 1

_GLOBAL_KEY = "global:uses"

def _get_global_uses():
    return _redis_get(_GLOBAL_KEY)

def _increment_global_uses():
    return _redis_incr(_GLOBAL_KEY)

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
    used = _get_global_uses()
    remaining = max(0, GLOBAL_LIMIT - used)
    return remaining > 0, remaining

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
if "seo_data" not in st.session_state:
    st.session_state.seo_data = None
if "comp_data" not in st.session_state:
    st.session_state.comp_data = None
if "results_view" not in st.session_state:
    st.session_state.results_view = "seo"

if "user_serper_key" not in st.session_state:
    st.session_state.user_serper_key = ""
if "user_gemini_key" not in st.session_state:
    st.session_state.user_gemini_key = ""
if "user_pagespeed_key" not in st.session_state:
    st.session_state.user_pagespeed_key = ""
if "user_scraperapi_key" not in st.session_state:
    st.session_state.user_scraperapi_key = ""

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


def create_horizontal_bar(labels, values, colors=None, title="", display_labels=None):
    """Horizontal bar chart for factor scoring."""
    if colors is None:
        colors = ['#667eea' if v >= 70 else '#FFA726' if v >= 50 else '#EF5350' for v in values]
    text = display_labels if display_labels else [f"{v}" for v in values]
    text_colors = colors if colors else ['white'] * len(values)
    fig = go.Figure(go.Bar(
        y=labels, x=values, orientation='h',
        marker=dict(color=colors, line=dict(width=0)),
        text=text,
        textposition='outside',
        textfont=dict(color=text_colors, size=12, family="Arial Black")
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


# ==================== RESULTS RENDER FUNCTIONS ====================

def _render_seo_results(d):
    """Render the full SEO analysis display from a stored results dict."""
    from urllib.parse import urlparse as _urlp

    url = d["url"]; keyword = d["keyword"]; score = d["score"]; summary = d["summary"]
    recommended_fixes = d["recommended_fixes"]; wc = d["wc"]; kc = d["kc"]; kd = d["kd"]
    internal = d["internal"]; external = d["external"]; missing_alt = d["missing_alt"]
    title = d["title"]; meta = d["meta"]; h1 = d["h1"]
    title_has_keyword = d["title_has_keyword"]; meta_has_keyword = d["meta_has_keyword"]
    h1_has_keyword = d["h1_has_keyword"]; token_counts = d["token_counts"]
    token_coverage = d["token_coverage"]; title_len = d["title_len"]; meta_len = d["meta_len"]
    tech_seo = d["tech_seo"]; has_schema = d["has_schema"]; pagespeed_data = d["pagespeed_data"]
    soup = d["soup"]; compare_url = d["compare_url"]; venue_urls_text = d["venue_urls_text"]

    _, gemini_api_key, pagespeed_api_key, _ = _active_keys()

    _domain = _urlp(url).netloc.replace("www.", "")
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d0d0d 0%,#111 100%);
            border:1px solid rgba(176,32,37,0.2);border-radius:16px;
            padding:1.4rem 2rem;margin:1rem 0 1.5rem;
            display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
    <div>
        <div style="font-size:0.6rem;font-weight:800;color:#B02025;letter-spacing:0.18em;
                    text-transform:uppercase;margin-bottom:0.3rem;">Analysis Complete</div>
        <div style="font-size:1.1rem;font-weight:700;color:#fff;">{_domain}</div>
        <div style="font-size:0.78rem;color:rgba(255,255,255,0.35);margin-top:0.1rem;">
            Keyword: <span style="color:rgba(255,255,255,0.6);">{keyword}</span>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;">
        <div style="width:10px;height:10px;border-radius:50%;background:#00C853;
                    box-shadow:0 0 8px #00C853;"></div>
        <span style="font-size:0.72rem;font-weight:600;color:rgba(255,255,255,0.45);
                     letter-spacing:0.08em;text-transform:uppercase;">Report Ready</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # Download report button — combines SEO + competitor data if both available
    _rec_html = "".join([f"<div class='card'><p><strong>{r['Issue']}</strong></p><p>{r['Recommended Fix']}</p><p><em>Impact: {r['Impact']}</em></p></div>" for r in recommended_fixes[:10]])

    _comp_section = ""
    _cd = st.session_state.comp_data
    if _cd and _cd.get("keyword") == keyword:
        _bench = _cd.get("benchmark_rows", [])
        _valid = [r for r in _bench if r.get("Score Band") != "Blocked"]
        _comp_rows_html = "".join([
            f"<tr><td>{r.get('Venue Name','')}</td><td>{r.get('SEO Score',0)}</td>"
            f"<td>{r.get('Score Band','')}</td><td>{r.get('Word Count',0)}</td>"
            f"<td>{'✓' if r.get('HTTPS') == 'Yes' else '✗'}</td>"
            f"<td>{'✓' if r.get('Schema') == 'Yes' else '✗'}</td></tr>"
            for r in _valid
        ])
        _ai_text = _cd.get("ai_summary", "")
        _ai_html = f"<div class='card' style='white-space:pre-wrap;'>{_ai_text}</div>" if _ai_text else ""
        _comp_section = f"""
<h1 style='margin-top:3rem;'>Competitor Intelligence Report</h1>
<p><strong>Keyword:</strong> {_cd.get('keyword','')} &nbsp;|&nbsp; <strong>Market:</strong> {_cd.get('country','')}</p>
<h2>Competitor Score Comparison</h2>
<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%;'>
<thead><tr style='background:#B02025;color:#fff;'><th>Venue</th><th>SEO Score</th><th>Band</th><th>Words</th><th>HTTPS</th><th>Schema</th></tr></thead>
<tbody>{_comp_rows_html}</tbody>
</table>
<h2>AI Executive Report</h2>
{_ai_html}"""

    _report_html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>SEO Report — {_domain}</title>
<style>body{{font-family:Arial,sans-serif;background:#f8f8f8;color:#222;padding:2rem;max-width:900px;margin:0 auto;}}
h1{{color:#B02025;border-bottom:2px solid #B02025;padding-bottom:0.5rem;}}
h2{{color:#333;margin-top:1.5rem;}}
.card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem;margin:0.8rem 0;}}
.metric{{display:inline-block;background:#fff;border:1px solid #ddd;border-radius:6px;padding:0.5rem 1rem;margin:0.3rem;text-align:center;min-width:120px;}}
.metric .val{{font-size:1.6rem;font-weight:bold;color:#B02025;}}
.metric .lbl{{font-size:0.7rem;color:#888;text-transform:uppercase;}}
.pass{{color:#4CAF50;font-weight:bold;}} .fail{{color:#EF5350;font-weight:bold;}}
table{{font-size:0.85rem;}} th,td{{padding:6px 10px;text-align:left;}}
</style></head><body>
<h1>SEO Analysis Report</h1>
<p><strong>Site:</strong> {url} &nbsp;|&nbsp; <strong>Keyword:</strong> {keyword} &nbsp;|&nbsp; <strong>Score:</strong> {score}/100</p>
<h2>Key Metrics</h2>
<div class='metric'><div class='val'>{wc:,}</div><div class='lbl'>Word Count</div></div>
<div class='metric'><div class='val'>{kc}</div><div class='lbl'>Keyword Hits</div></div>
<div class='metric'><div class='val'>{kd}%</div><div class='lbl'>Keyword Density</div></div>
<div class='metric'><div class='val'>{len(internal)}</div><div class='lbl'>Internal Links</div></div>
<div class='metric'><div class='val'>{len(external)}</div><div class='lbl'>External Links</div></div>
<div class='metric'><div class='val'>{len(missing_alt)}</div><div class='lbl'>Missing ALTs</div></div>
<h2>Executive Summary</h2>
<div class='card'><p><strong>Status:</strong> {summary['Overall Status']}</p>
<p><strong>Strongest Area:</strong> {summary['Strongest Area']}</p>
<p><strong>Top Issue:</strong> {summary['Top Issue']}</p>
<p><strong>Priority Action:</strong> {summary['Priority Action']}</p></div>
<h2>Technical SEO</h2>
<div class='card'>
<p class='{"pass" if tech_seo.get("https_enabled") else "fail"}'>{"✓" if tech_seo.get("https_enabled") else "✗"} HTTPS</p>
<p class='{"pass" if tech_seo.get("mobile_viewport") else "fail"}'>{"✓" if tech_seo.get("mobile_viewport") else "✗"} Mobile Viewport</p>
<p class='{"pass" if has_schema else "fail"}'>{"✓" if has_schema else "✗"} Schema Markup</p>
<p class='{"pass" if tech_seo.get("has_canonical") else "fail"}'>{"✓" if tech_seo.get("has_canonical") else "✗"} Canonical URL</p>
</div>
<h2>Recommendations</h2>
{_rec_html}
{_comp_section}
</body></html>"""
    _dl_label = "⬇ Download Full Report (SEO + Competitors)" if _comp_section else "⬇ Download Report (HTML)"
    st.download_button(
        label=_dl_label,
        data=_report_html.encode("utf-8"),
        file_name=f"seo_report_{_domain}_{keyword.replace(' ','_')}.html",
        mime="text/html",
        key="dl_seo_stored"
    )

    def _metric(label, val, color):
        return (f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);border-top:2px solid {color};border-radius:10px;padding:1rem 1rem 0.8rem;text-align:center;">'
                f'<div style="font-size:1.8rem;font-weight:800;color:{color};line-height:1;">{val}</div>'
                f'<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.35);margin-top:0.3rem;">{label}</div>'
                f'</div>')

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Technical SEO", "Content Analysis", "Recommendations", "GEO Score"])

    with tab1:
        # Score Gauge + Key Metrics
        col_gauge, col_metrics = st.columns([2, 3])

        with col_gauge:
            st.plotly_chart(create_score_gauge(score), use_container_width=True)
            _band = get_score_band(score)
            _band_color = "#00C853" if score >= 80 else ("#FF9800" if score >= 60 else "#EF5350")
            st.markdown(
                f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                f'border-left:3px solid {_band_color};border-radius:8px;'
                f'padding:0.5rem 0.9rem;margin-top:0.3rem;display:inline-block;">'
                f'<span style="font-size:0.55rem;font-weight:800;letter-spacing:0.12em;'
                f'text-transform:uppercase;color:rgba(255,255,255,0.35);">Score Band</span>'
                f'<div style="font-size:0.9rem;font-weight:700;color:{_band_color};margin-top:0.1rem;">{_band}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        with col_metrics:
            st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)
            kc1, kc2, kc3 = st.columns(3)
            kc1.markdown(_metric("Word Count", f"{wc:,}", "#B02025"), unsafe_allow_html=True)
            kc2.markdown(_metric("Keyword Hits", kc, "#00C853" if kc >= 3 else "#EF5350"), unsafe_allow_html=True)
            kc3.markdown(_metric("Keyword Density", f"{kd}%", "#FF9800"), unsafe_allow_html=True)
            st.markdown("<div style='margin:0.5rem 0;'></div>", unsafe_allow_html=True)
            kc4, kc5, kc6 = st.columns(3)
            kc4.markdown(_metric("Internal Links", len(internal), "#7EC7A3"), unsafe_allow_html=True)
            kc5.markdown(_metric("External Links", len(external), "#667eea"), unsafe_allow_html=True)
            kc6.markdown(_metric("Missing ALTs", len(missing_alt), "#EF5350" if missing_alt else "#00C853"), unsafe_allow_html=True)

        # ── Row 2: Radar + SEO factors bar + Link donut ──────────
        st.markdown("---")
        r2a, r2b, r2c = st.columns([1.1, 1.1, 0.9])

        with r2a:
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
            total_links = len(internal) + len(external) or 1
            st.plotly_chart(create_donut_chart(
                labels=["Internal", "External"],
                values=[len(internal), max(len(external), 1)],
                colors=["#B02025", "#7EC7A3"],
                title="Link Distribution",
                center_text=f"{total_links}<br>links"
            ), use_container_width=True)

        # ── Row 3: Keyword status donut + executive summary ───────
        st.markdown("---")
        r3a, r3b = st.columns([1, 2])

        with r3a:
            kw_present = sum([title_has_keyword, meta_has_keyword, h1_has_keyword, kc > 0])
            st.markdown("<div class='section-header'>Keyword Placement</div>", unsafe_allow_html=True)
            _kw_slots = [
                ("Title Tag", title_has_keyword),
                ("Meta Description", meta_has_keyword),
                ("H1 Heading", h1_has_keyword),
                ("Body Content", kc > 0),
            ]
            _cov_color = "#00C853" if kw_present == 4 else ("#FF9800" if kw_present >= 2 else "#EF5350")
            st.markdown(
                f'<div style="font-size:1.6rem;font-weight:800;color:{_cov_color};margin-bottom:0.8rem;">'
                f'{kw_present}<span style="font-size:1rem;color:rgba(255,255,255,0.3);">/4 covered</span></div>',
                unsafe_allow_html=True
            )
            for _slot, _hit in _kw_slots:
                _ic = "✅" if _hit else "❌"
                _sc = "rgba(255,255,255,0.7)" if _hit else "rgba(255,255,255,0.3)"
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">'
                    f'<span>{_ic}</span>'
                    f'<span style="font-size:0.82rem;color:{_sc};">{_slot}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with r3b:
            st.markdown("<div class='section-header'>Executive Summary</div>", unsafe_allow_html=True)
            _summary_items = [
                ("#7EC7A3", "Overall Status", summary['Overall Status']),
                ("#4CAF50", "Strongest Area", summary['Strongest Area']),
                ("#FF9800", "Top Issue", summary['Top Issue']),
                ("#B02025", "Priority Action", summary['Priority Action']),
            ]
            sc1, sc2 = st.columns(2)
            for i, (color, label, text) in enumerate(_summary_items):
                col = sc1 if i % 2 == 0 else sc2
                col.markdown(f"""
<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);
            border-left:3px solid {color};border-radius:8px;
            padding:0.8rem 1rem;margin-bottom:0.6rem;">
    <div style="font-size:0.58rem;font-weight:800;letter-spacing:0.12em;
                text-transform:uppercase;color:{color};margin-bottom:0.3rem;">{label}</div>
    <div style="font-size:0.82rem;color:rgba(255,255,255,0.65);line-height:1.4;">{text}</div>
</div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="section-header">Technical SEO Audit</div>', unsafe_allow_html=True)

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
        # Pass/fail tile grid — 3 per row
        _tech_checks = [
            ("HTTPS", tech_seo.get('https_enabled', False)),
            ("Canonical URL", tech_seo.get('has_canonical', False)),
            ("Indexable", not tech_seo.get('robots_noindex', True)),
            ("Mobile Viewport", tech_seo.get('mobile_viewport', False)),
            ("Language Tag", tech_seo.get('has_lang', False)),
            ("Single H1", tech_seo.get('proper_h1_usage', False)),
            ("Open Graph", tech_seo.get('has_og_title', False)),
            ("Twitter Card", tech_seo.get('has_twitter_card', False)),
            ("Schema Markup", has_schema),
        ]
        _pass_count = sum(1 for _, v in _tech_checks if v)
        st.markdown(
            f'<div style="font-size:0.75rem;color:rgba(255,255,255,0.4);margin-bottom:1rem;">'
            f'<span style="color:#00C853;font-weight:700;">{_pass_count} passed</span>'
            f'  ·  '
            f'<span style="color:#EF5350;font-weight:700;">{len(_tech_checks)-_pass_count} failed</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        _tile_cols = st.columns([1, 1, 1], gap="medium")
        for i, (name, passed) in enumerate(_tech_checks):
            _color = "#00C853" if passed else "#EF5350"
            _bg = "rgba(0,200,83,0.06)" if passed else "rgba(239,83,80,0.06)"
            _icon = "✓" if passed else "✗"
            _label = "PASS" if passed else "FAIL"
            _tile_cols[i % 3].markdown(
                f'<div style="background:{_bg};border:1px solid {_color}22;'
                f'border-top:2px solid {_color};border-radius:10px;'
                f'padding:1.6rem 1.4rem;margin-bottom:1.2rem;text-align:center;">'
                f'<div style="font-size:2rem;font-weight:900;color:{_color};line-height:1;margin-bottom:0.6rem;">{_icon}</div>'
                f'<div style="font-size:0.78rem;font-weight:700;color:rgba(255,255,255,0.8);'
                f'margin:0 0 0.4rem;letter-spacing:0.02em;">{name}</div>'
                f'<div style="font-size:0.58rem;font-weight:800;letter-spacing:0.16em;'
                f'text-transform:uppercase;color:{_color};opacity:0.85;">{_label}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        if has_schema:
            schemas = detect_schema_markup(soup)
            if schemas['json_ld']:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.45);margin-top:0.3rem;">'
                    f'JSON-LD Types: <span style="color:#00C853;">{", ".join(schemas["json_ld"])}</span></div>',
                    unsafe_allow_html=True
                )

        # PageSpeed Section
        if pagespeed_data:
            st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-header'>⚡ PageSpeed Insights (Mobile)</div>", unsafe_allow_html=True)

            perf_score = int(pagespeed_data.get("performance_score", 0) * 100)
            acc_score  = int(pagespeed_data.get("accessibility_score", 0) * 100)
            bp_score   = int(pagespeed_data.get("best_practices_score", 0) * 100)
            seo_score  = int(pagespeed_data.get("seo_score", 0) * 100)

            def _ps_color(s):
                return "#00C853" if s >= 90 else ("#FF9800" if s >= 50 else "#EF5350")

            ps_cols = st.columns(4)
            for col, lbl, val in zip(ps_cols,
                ["Performance", "Accessibility", "Best Practices", "SEO"],
                [perf_score, acc_score, bp_score, seo_score]):
                col.markdown(
                    f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                    f'border-top:2px solid {_ps_color(val)};border-radius:10px;'
                    f'padding:1rem;text-align:center;">'
                    f'<div style="font-size:2rem;font-weight:800;color:{_ps_color(val)};line-height:1;">{val}<span style="font-size:1rem;color:rgba(255,255,255,0.3);">/100</span></div>'
                    f'<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
                    f'color:rgba(255,255,255,0.35);margin-top:0.3rem;">{lbl}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

            vitals = [
                ("FCP", pagespeed_data.get("first_contentful_paint", "N/A")),
                ("LCP", pagespeed_data.get("largest_contentful_paint", "N/A")),
                ("SI",  pagespeed_data.get("speed_index", "N/A")),
                ("TBT", pagespeed_data.get("total_blocking_time", "N/A")),
                ("CLS", pagespeed_data.get("cumulative_layout_shift", "N/A")),
            ]
            vital_cols = st.columns(5)
            for col, (label, val) in zip(vital_cols, vitals):
                col.markdown(
                    f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                    f'border-radius:8px;padding:0.7rem 0.8rem;text-align:center;">'
                    f'<div style="font-size:0.95rem;font-weight:700;color:rgba(255,255,255,0.85);">{val}</div>'
                    f'<div style="font-size:0.55rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
                    f'color:rgba(255,255,255,0.3);margin-top:0.2rem;">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with tab3:
        st.markdown('<div class="section-header">Content Analysis</div>', unsafe_allow_html=True)

        content_col1, content_col2 = st.columns(2)

        with content_col1:
            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.5rem;">On-Page Elements</div>', unsafe_allow_html=True)
            st.text_input("Title", value=title, disabled=True)
            st.text_area("Meta Description", value=meta, height=80, disabled=True)
            st.text_input("H1 Tags", value=", ".join(h1) if h1 else "None", disabled=True)

        with content_col2:
            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.8rem;">Keyword Analysis</div>', unsafe_allow_html=True)

            for _label, _hit in [("Keyword in Title", title_has_keyword), ("Keyword in Meta", meta_has_keyword), ("Keyword in H1", h1_has_keyword)]:
                _c = "#00C853" if _hit else "#EF5350"
                _ic = "✓" if _hit else "✗"
                _txt = "Yes" if _hit else "No"
                st.markdown(
                    f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);'
                    f'border-left:3px solid {_c};border-radius:8px;'
                    f'padding:0.55rem 0.9rem;margin-bottom:0.45rem;'
                    f'display:flex;align-items:center;justify-content:space-between;">'
                    f'<span style="font-size:0.78rem;color:rgba(255,255,255,0.6);">{_label}</span>'
                    f'<span style="font-size:0.78rem;font-weight:700;color:{_c};">{_ic} {_txt}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            _cov_color = "#00C853" if token_coverage >= 75 else ("#FF9800" if token_coverage >= 50 else "#EF5350")
            st.markdown(
                f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);'
                f'border-left:3px solid {_cov_color};border-radius:8px;'
                f'padding:0.55rem 0.9rem;margin-bottom:0.8rem;'
                f'display:flex;align-items:center;justify-content:space-between;">'
                f'<span style="font-size:0.78rem;color:rgba(255,255,255,0.6);">Token Coverage</span>'
                f'<span style="font-size:0.78rem;font-weight:700;color:{_cov_color};">{token_coverage}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            if token_counts:
                st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0.4rem 0 0.5rem;">Token Counts</div>', unsafe_allow_html=True)
                for token, count in token_counts.items():
                    _word = "time" if count == 1 else "times"
                    st.markdown(
                        f'<div style="display:flex;align-items:center;justify-content:space-between;'
                        f'padding:0.35rem 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                        f'<span style="font-size:0.78rem;color:rgba(255,255,255,0.5);font-style:italic;">{token}</span>'
                        f'<span style="font-size:0.78rem;font-weight:600;color:rgba(255,255,255,0.7);">{count} {_word}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    with tab4:
        st.markdown('<div class="section-header">Recommended Actions</div>', unsafe_allow_html=True)

        _priority_groups = [
            ("CRITICAL", "#FF5252", [r for r in recommended_fixes if "CRITICAL" in r['Priority']]),
            ("HIGH PRIORITY", "#FF9800", [r for r in recommended_fixes if "HIGH" in r['Priority']]),
            ("MEDIUM PRIORITY", "#FFD600", [r for r in recommended_fixes if "MEDIUM" in r['Priority']]),
        ]
        for _pg_label, _pg_color, _pg_items in _priority_groups:
            if not _pg_items:
                continue
            st.markdown(f'<div style="font-size:0.6rem;font-weight:800;color:{_pg_color};letter-spacing:0.18em;text-transform:uppercase;margin:1.2rem 0 0.6rem;">{_pg_label} ({len(_pg_items)})</div>', unsafe_allow_html=True)
            for rec in _pg_items:
                st.markdown(f"""<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);border-left:3px solid {_pg_color};border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.6rem;"><div style="font-size:0.88rem;font-weight:700;color:rgba(255,255,255,0.85);margin-bottom:0.4rem;">{rec['Issue']}</div><div style="font-size:0.8rem;color:rgba(255,255,255,0.5);margin-bottom:0.3rem;">{rec['Recommended Fix']}</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.28);letter-spacing:0.04em;">Impact: {rec['Impact']}</div></div>""", unsafe_allow_html=True)

        _excellent = [r for r in recommended_fixes if "EXCELLENT" in r['Priority']]
        if _excellent:
            for rec in _excellent:
                st.markdown(f"""<div style="background:#0a0a0a;border:1px solid rgba(76,175,80,0.2);border-left:3px solid #4CAF50;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.6rem;"><div style="font-size:0.88rem;font-weight:700;color:#4CAF50;">✓ {rec['Issue']}</div><div style="font-size:0.8rem;color:rgba(255,255,255,0.4);margin-top:0.3rem;">{rec['Recommended Fix']}</div></div>""", unsafe_allow_html=True)

    with tab5:
        st.markdown('<div class="section-header">GEO Score — AI Search Visibility</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.8rem;color:rgba(255,255,255,0.35);margin-bottom:1rem;">How well this page is optimized for ChatGPT, Claude, Perplexity, and Google AI Overviews</div>', unsafe_allow_html=True)

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

        geo_col1, geo_col2 = st.columns([2, 3])
        with geo_col1:
            st.plotly_chart(
                create_score_gauge(geo_result["score"], title="GEO Score"),
                use_container_width=True
            )
            _geo_band_color = "#00C853" if geo_result["score"] >= 80 else ("#FF9800" if geo_result["score"] >= 60 else "#EF5350")
            st.markdown(
                f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                f'border-left:3px solid {_geo_band_color};border-radius:8px;'
                f'padding:0.5rem 0.9rem;margin-top:0.3rem;display:inline-block;">'
                f'<span style="font-size:0.55rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.35);">Band</span>'
                f'<div style="font-size:0.9rem;font-weight:700;color:{_geo_band_color};margin-top:0.1rem;">{geo_result["band"]}</div>'
                f'</div>', unsafe_allow_html=True
            )

        with geo_col2:
            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.8rem;">Score Breakdown</div>', unsafe_allow_html=True)
            breakdown = geo_result["breakdown"]
            _bd_labels = {"citability": "Content Citability", "eeat": "E-E-A-T",
                          "crawlers": "AI Crawler Access", "schema": "Schema Markup", "llmstxt": "llms.txt"}
            for key, data in breakdown.items():
                label = _bd_labels.get(key, key)
                bar_pct = int(data["score"])
                _bc = "#00C853" if bar_pct >= 80 else ("#FF9800" if bar_pct >= 50 else "#EF5350")
                st.markdown(
                    f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);'
                    f'border-radius:8px;padding:0.6rem 1rem;margin-bottom:0.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
                    f'<span style="font-size:0.78rem;color:rgba(255,255,255,0.6);">{label}</span>'
                    f'<span style="font-size:0.78rem;font-weight:700;color:{_bc};">{bar_pct}/100</span>'
                    f'</div>'
                    f'<div style="background:rgba(255,255,255,0.06);border-radius:4px;height:4px;">'
                    f'<div style="background:{_bc};width:{bar_pct}%;height:4px;border-radius:4px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown("<div style='margin:1.5rem 0;border-top:1px solid rgba(255,255,255,0.06);'></div>", unsafe_allow_html=True)

        geo_c1, geo_c2 = st.columns([1.2, 1], gap="large")

        with geo_c1:
            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.6rem;">AI Crawler Access</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:0.72rem;color:rgba(255,255,255,0.35);margin-bottom:0.6rem;">'
                f'robots.txt score: <span style="color:#B02025;font-weight:700;">{geo_crawlers["score"]}/100</span></div>',
                unsafe_allow_html=True
            )
            for crawler in geo_crawlers["crawlers"]:
                _cs = crawler["status"]
            _crawler_rows_html = ""
            for crawler in geo_crawlers["crawlers"]:
                _cs = crawler["status"]
                _cc = "#00C853" if _cs == "allowed" else ("#EF5350" if _cs == "blocked" else "#FF9800")
                _ci = "✓" if _cs == "allowed" else ("✗" if _cs == "blocked" else "–")
                _is_crit = crawler["priority"] == "critical"
                _fw = "600" if _is_crit else "400"
                _fc = "rgba(255,255,255,0.75)" if _is_crit else "rgba(255,255,255,0.45)"
                _crawler_rows_html += (
                    f'<div style="display:flex;align-items:center;gap:1rem;'
                    f'padding:0.4rem 0.6rem;margin-bottom:2px;'
                    f'background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);border-radius:6px;">'
                    f'<span style="font-size:0.75rem;color:{_fc};font-weight:{_fw};flex:1;">{crawler["name"]}</span>'
                    f'<span style="font-size:0.72rem;font-weight:700;color:{_cc};white-space:nowrap;">{_ci} {_cs}</span>'
                    f'</div>'
                )
            _sm_c = "#00C853" if geo_crawlers["has_sitemap"] else "#EF5350"
            _sm_i = "✓" if geo_crawlers["has_sitemap"] else "✗"
            _crawler_rows_html += (
                f'<div style="font-size:0.72rem;font-weight:600;color:{_sm_c};margin-top:0.5rem;">'
                f'{_sm_i} Sitemap in robots.txt</div>'
            )
            st.markdown(_crawler_rows_html, unsafe_allow_html=True)

        with geo_c2:
            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.6rem;">llms.txt</div>', unsafe_allow_html=True)
            if geo_llmstxt["exists"]:
                st.markdown(
                    f'<div style="background:rgba(0,200,83,0.06);border:1px solid rgba(0,200,83,0.2);'
                    f'border-left:3px solid #00C853;border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.8rem;">'
                    f'<span style="font-size:0.78rem;color:#00C853;font-weight:600;">✓ llms.txt found</span>'
                    f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.4);margin-top:0.2rem;">'
                    f'{geo_llmstxt["sections"]} sections · {geo_llmstxt["links"]} links</div></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div style="background:rgba(239,83,80,0.06);border:1px solid rgba(239,83,80,0.2);'
                    f'border-left:3px solid #EF5350;border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.4rem;">'
                    f'<span style="font-size:0.78rem;color:#EF5350;font-weight:600;">✗ No llms.txt found</span>'
                    f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.4);margin-top:0.2rem;">'
                    f'Consider adding one to guide AI crawlers</div></div>',
                    unsafe_allow_html=True
                )
                st.markdown('<a href="https://llmstxt.org" target="_blank" style="font-size:0.72rem;color:#667eea;">What is llms.txt?</a>', unsafe_allow_html=True)

            st.markdown('<div style="font-size:0.65rem;font-weight:800;color:rgba(255,255,255,0.4);letter-spacing:0.14em;text-transform:uppercase;margin:0.8rem 0 0.5rem;">E-E-A-T Signals</div>', unsafe_allow_html=True)
            signals = geo_eeat["signals"]
            eeat_items = [
                ("Author byline",    signals.get("has_author", False)),
                ("Publication date", signals.get("has_date", False)),
                ("About page",       signals.get("has_about", False)),
                ("Contact page",     signals.get("has_contact", False)),
                ("Privacy policy",   signals.get("has_privacy", False)),
                ("HTTPS",            signals.get("has_https", False)),
            ]
            _eeat_html = ""
            for label, passed in eeat_items:
                _ec = "#00C853" if passed else "#EF5350"
                _ei = "✓" if passed else "✗"
                _eeat_html += (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:0.4rem 0.6rem;margin-bottom:2px;'
                    f'background:#0a0a0a;border:1px solid rgba(255,255,255,0.05);border-radius:6px;">'
                    f'<span style="font-size:0.75rem;color:rgba(255,255,255,0.55);">{label}</span>'
                    f'<span style="font-size:0.75rem;font-weight:700;color:{_ec};">{_ei}</span>'
                    f'</div>'
                )
            st.markdown(_eeat_html, unsafe_allow_html=True)

        st.markdown("<div style='margin:1.5rem 0;border-top:1px solid rgba(255,255,255,0.06);'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Content Citability</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.75rem;color:rgba(255,255,255,0.3);margin-bottom:1rem;">How likely AI models are to directly quote/cite content from this page</div>', unsafe_allow_html=True)

        cit_col1, cit_col2, cit_col3 = st.columns(3)
        _cit_score = geo_citability["score"]
        _cit_color = "#00C853" if _cit_score >= 80 else ("#FF9800" if _cit_score >= 50 else "#EF5350")
        for col, lbl, val in zip(
            [cit_col1, cit_col2, cit_col3],
            ["Citability Score", "Grade", "Optimal Blocks"],
            [f"{_cit_score}/100", f"{geo_citability['grade']} — {geo_citability['grade_label']}", f"{geo_citability['optimal_blocks']} / {geo_citability['blocks_analyzed']}"]
        ):
            col.markdown(
                f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                f'border-top:2px solid {_cit_color};border-radius:10px;padding:1rem;text-align:center;">'
                f'<div style="font-size:1.4rem;font-weight:800;color:{_cit_color};line-height:1;">{val}</div>'
                f'<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
                f'color:rgba(255,255,255,0.3);margin-top:0.3rem;">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        if geo_citability.get("top_blocks"):
            st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
            if "show_cit_blocks" not in st.session_state:
                st.session_state.show_cit_blocks = False
            _cit_toggle_label = "— Hide Content Blocks" if st.session_state.show_cit_blocks else "+ Top Citable Content Blocks"
            if st.button(_cit_toggle_label, key="toggle_cit_blocks", type="secondary"):
                st.session_state.show_cit_blocks = not st.session_state.show_cit_blocks
                st.rerun()
            if st.session_state.show_cit_blocks:
                for block in geo_citability["top_blocks"][:3]:
                    st.markdown(
                        f'<div style="background:#0a0a0a;border:1px solid rgba(255,255,255,0.06);'
                        f'border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.6rem;">'
                        f'<div style="font-size:0.82rem;font-weight:700;color:rgba(255,255,255,0.8);margin-bottom:0.3rem;">'
                        f'{block.get("heading","No heading")}</div>'
                        f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.35);margin-bottom:0.4rem;">'
                        f'Score: {block["score"]}/100 · {block["grade"]} · {block["word_count"]} words</div>'
                        f'<div style="font-size:0.75rem;color:rgba(255,255,255,0.45);font-style:italic;">'
                        f'{block.get("preview","")}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

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

            comp_data_table = {
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

            st.dataframe(pd.DataFrame(comp_data_table), use_container_width=True)

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


def _render_comp_results(d):
    """Render the full competitor analysis display from a stored results dict."""
    url = d["url"]; keyword = d["keyword"]; country = d["country"]
    benchmark_rows = d["benchmark_rows"]; gemini_competitors = d["gemini_competitors"]

    _, gemini_api_key, _, _ = _active_keys()

    benchmark_df = pd.DataFrame(benchmark_rows)

    error_rows = [r for r in benchmark_rows if r.get("Score Band") == "Blocked"]
    valid_rows = [r for r in benchmark_rows if r.get("Score Band") != "Blocked"]

    primary_row = next((r for r in valid_rows if "Your Site" in r.get("Role", "") or "Primary" in r.get("Role", "")), None)

    if valid_rows:
        primary_valid = [r for r in valid_rows if "Primary" in r.get("Role", "")]
        comp_valid = sorted(
            [r for r in valid_rows if "Competitor" in r.get("Role", "")],
            key=lambda x: x.get("SEO Score", 0), reverse=True
        )[:10]
        chart_rows = primary_valid + comp_valid
        valid_df = pd.DataFrame(chart_rows)
        from urllib.parse import urlparse as _up
        valid_df["Label"] = valid_df["URL"].apply(
            lambda u: _up(u).netloc.replace("www.", "") if u else ""
        )
        valid_df = valid_df.sort_values("SEO Score", ascending=True)
        fig = px.bar(
            valid_df,
            x="SEO Score",
            y="Label",
            color="Role",
            text="SEO Score",
            orientation="h",
            color_discrete_map={"🏠 Your Site": "#B02025", "🎯 Competitor": "#555555"},
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

    st.markdown("""<div style="font-size:0.6rem;font-weight:800;color:#B02025;
        letter-spacing:0.18em;text-transform:uppercase;margin:1.5rem 0 0.5rem;">
        Full Comparison — All Venues</div>""", unsafe_allow_html=True)
    display_cols = ["Role", "Venue Name", "SEO Score", "Score Band", "Word Count", "HTTPS", "Schema"]
    available_cols = [c for c in display_cols if c in benchmark_df.columns]
    st.dataframe(benchmark_df[available_cols], use_container_width=True)

    if primary_row and gemini_api_key:
        st.markdown("""
<div style="font-size:0.6rem;font-weight:800;color:#B02025;letter-spacing:0.18em;
            text-transform:uppercase;margin:2rem 0 0.8rem;">AI Executive Report</div>
""", unsafe_allow_html=True)
        best_comp = max(
            [r for r in valid_rows if "Competitor" in r.get("Role", "")],
            key=lambda x: x.get("SEO Score", 0),
            default={}
        )
        best_comp_name = best_comp.get("Venue Name", "top competitor") if best_comp else "N/A"

        insights = generate_strategic_insights(
            primary_row=primary_row,
            benchmark_rows=benchmark_rows,
            keyword=keyword
        )

        if "ai_summary" not in d or not d["ai_summary"]:
            with st.spinner("Generating AI analysis report..."):
                d["ai_summary"] = generate_ai_executive_summary(
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
        ai_summary = d["ai_summary"]
        if ai_summary:
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
            sections = _re.split(r'\n#{1,3}\s+', "\n" + ai_summary)
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Barlow+Condensed:wght@700;800;900&family=Inter:wght@300;400;500;600&display=swap');
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
@keyframes line-sweep {
    0%   { transform: translateX(-100%) rotate(-25deg); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateX(200%) rotate(-25deg); opacity: 0; }
}
@keyframes line-sweep2 {
    0%   { transform: translateX(-100%) rotate(-15deg); opacity: 0; }
    10%  { opacity: 0.6; }
    90%  { opacity: 0.6; }
    100% { transform: translateX(200%) rotate(-15deg); opacity: 0; }
}
@keyframes pulse-glow {
    0%, 100% { opacity: 0.4; transform: scaleX(1); }
    50%       { opacity: 1;   transform: scaleX(1.05); }
}
@keyframes marquee {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
@keyframes spin {
    to { transform: rotate(360deg); }
}

/* ═══════════════════════════════════════════════
   BASE — Pure black like DigitalStrike
═══════════════════════════════════════════════ */
* { font-family: 'Space Grotesk', 'Outfit', sans-serif !important; }
h1,h2,h3,h4 { font-family: 'Barlow Condensed', 'Outfit', sans-serif !important; }
.stTextInput label, .stTextArea label, .stSelectbox label,
.section-header, .hero-eyebrow, .input-card-title,
.kpi-label { font-family: 'Inter', 'Outfit', sans-serif !important; }
.main > div { padding-top: 0 !important; }
.block-container {
    padding: 0 2.5rem 1rem !important;
    max-width: 100% !important;
    margin: 0 !important;
}

/* ── Ticker strip ── */
.ticker-wrap {
    width: 100%; overflow: hidden; background: #0a0a0a;
    border-top: 1px solid rgba(176,32,37,0.15);
    border-bottom: 1px solid rgba(176,32,37,0.15);
    padding: 6px 0; margin: 0 -2.5rem;
}
.ticker-track {
    display: flex; gap: 0;
    width: max-content;
    animation: marquee 60s linear infinite;
    white-space: nowrap;
}
.ticker-item {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; color: rgba(255,255,255,0.22);
    padding: 0 2.5rem;
}
.ticker-dot {
    color: #B02025; margin-right: 2.5rem; opacity: 0.7;
}

/* ── Hero red lines ── */
.hero-line {
    position: absolute; top: 0; left: 0;
    width: 60%; height: 1px;
    background: linear-gradient(90deg, transparent, #B02025 40%, #FF4444 60%, transparent);
    pointer-events: none;
}
.hero-line-1 { animation: line-sweep 5s ease-in-out 0s infinite; top: 30%; }
.hero-line-2 { animation: line-sweep 5s ease-in-out 1.8s infinite; top: 55%; width: 40%;
               background: linear-gradient(90deg, transparent, rgba(176,32,37,0.5) 50%, transparent); }
.hero-line-3 { animation: line-sweep2 7s ease-in-out 0.8s infinite; top: 75%; width: 30%;
               background: linear-gradient(90deg, transparent, rgba(255,68,68,0.3) 50%, transparent); }
.hero-glow-bar {
    position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, #B02025 30%, #FF4444 50%, #B02025 70%, transparent);
    animation: pulse-glow 3s ease-in-out infinite;
}

/* Full black base + moving grid lines (Webflow aesthetic) */
.stApp { background: #000000 !important; }
.stApp > div { position: relative; }
html, body { overflow: hidden !important; height: 100% !important; }
.stApp { overflow-y: auto !important; height: 100vh !important; }
section[data-testid="stSidebar"] { overflow: hidden !important; }
section:not([data-testid="stSidebar"]) { overflow: visible !important; height: auto !important; min-height: unset !important; }
[data-testid="stAppViewContainer"] { overflow: visible !important; height: auto !important; }
[data-testid="stVerticalBlock"] { overflow: visible !important; height: auto !important; }
[data-testid="block-container"] { overflow: visible !important; height: auto !important; max-height: unset !important; }

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
    padding: 1.6rem 2.5rem 1.4rem;
    margin: 0 -2.5rem 1.2rem;
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
    margin-bottom: 0.4rem; animation: fadeInLeft 0.6s 0.1s ease-out both;
}
.hero-title {
    font-size: clamp(1.8rem, 3.5vw, 3rem);
    font-family: 'Barlow Condensed', 'Outfit', sans-serif !important;
    font-weight: 900; line-height: 0.95;
    letter-spacing: -1px;
    color: #ffffff;
    margin: 0 0 0.2rem;
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
    font-size: 0.95rem; color: rgba(255,255,255,0.5);
    font-weight: 400; line-height: 1.5;
    max-width: 560px; margin: 0.3rem 0 0;
    animation: fadeInLeft 0.7s 0.35s ease-out both;
}
.hero-badges {
    display: flex; gap: 0.5rem; margin-top: 0.6rem; flex-wrap: wrap;
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
    position: relative; overflow: visible;
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
   BUTTONS
═══════════════════════════════════════════════ */
.stButton > button {
    width: 100% !important;
    border-radius: 50px !important;
    height: 3.5em !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    transition: all 0.25s ease !important;
    border: none !important;
    position: relative !important;
    overflow: hidden !important;
}
/* shimmer sweep */
.stButton > button::after {
    content: '' !important;
    position: absolute !important; top: 0 !important; left: -100% !important;
    width: 50% !important; height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent) !important;
    animation: shimmer 3s infinite !important;
}
/* PRIMARY — bold red */
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
/* SECONDARY — ghost white */
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
    display: inline-flex; align-items: center; gap: 8px;
    background: #0a0a0a;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 50px; padding: 0.5rem 1rem;
    font-size: 0.75rem; color: rgba(255,255,255,0.55); font-weight: 500;
    white-space: nowrap;
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

/* ── Results toggle switcher ── */
.results-toggle {
    display: flex; gap: 0; margin: 2rem 0 0;
    background: #0a0a0a; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 50px; padding: 4px; width: fit-content;
}
.toggle-btn {
    padding: 0.55rem 1.6rem; border-radius: 50px; border: none;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; cursor: pointer; transition: all 0.25s;
    background: transparent; color: rgba(255,255,255,0.35);
}
.toggle-btn.active {
    background: #B02025; color: #fff;
    box-shadow: 0 2px 12px rgba(176,32,37,0.4);
}
.toggle-btn.has-data { color: rgba(255,255,255,0.6); }
.toggle-dot {
    display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    background: #7EC7A3; margin-right: 6px; vertical-align: middle;
    box-shadow: 0 0 6px #7EC7A3;
}

/* ── Remove Streamlit default top padding ── */
header[data-testid="stHeader"] { display: none !important; }
#root > div:nth-child(1) > div > div > div > div > section > div { padding-top: 0 !important; }

/* ── Vertical spacing ── */
.stTextInput { margin-bottom: 1rem !important; }
.stTextArea { margin-bottom: 1rem !important; }
div[data-testid="column"] { padding: 0 0.4rem !important; }
div[data-testid="stVerticalBlock"] > div { gap: 0.6rem; }
div[data-testid="stButton"] { margin-bottom: 0.4rem !important; }

/* ── Collapse admin button row gap ── */
div[data-testid="stHorizontalBlock"]:has(button[data-testid="baseButton-secondary"][kind="secondary"]) {
    margin-top: 0 !important; margin-bottom: 0 !important;
    min-height: 0 !important;
}
/* Zero out the spacer column next to admin button */
div[data-testid="stHorizontalBlock"] > div:first-child:has(+ div button[key="admin_btn"]) {
    display: none !important;
}

/* ── Compare toggle button — small inline style ── */
button[kind="secondary"][data-testid="baseButton-secondary"]:has-text("COMPARE") {
    width: auto !important;
}
div[data-testid="stButton"]:has(button[key="toggle_compare"]),
div[data-testid="stButton"]:has(button[key="toggle_own_keys"]) { display: inline-flex !important; }
div[data-testid="stButton"]:has(button[key="toggle_compare"]) button,
div[data-testid="stButton"]:has(button[key="toggle_own_keys"]) button,
div[data-testid="stButton"]:has(button[key="toggle_compare"]) button:focus,
div[data-testid="stButton"]:has(button[key="toggle_own_keys"]) button:focus,
div[data-testid="stButton"]:has(button[key="toggle_compare"]) button:active,
div[data-testid="stButton"]:has(button[key="toggle_own_keys"]) button:active {
    width: auto !important;
    font-size: 0.72rem !important;
    height: 2.6em !important;
    padding: 0 1.4rem !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    letter-spacing: 0.14em !important;
    color: rgba(255,255,255,0.55) !important;
    border-radius: 10px !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
div[data-testid="stButton"]:has(button[key="toggle_compare"]) button:hover,
div[data-testid="stButton"]:has(button[key="toggle_own_keys"]) button:hover {
    background: rgba(176,32,37,0.08) !important;
    border-color: rgba(176,32,37,0.35) !important;
    color: rgba(255,100,100,0.9) !important;
}
</style>
""", unsafe_allow_html=True)

# ==================== HERO HEADER ====================

st.markdown("""
<div class="hero-header">
    <div class="hero-line hero-line-1"></div>
    <div class="hero-line hero-line-2"></div>
    <div class="hero-line hero-line-3"></div>
    <div class="hero-glow-bar"></div>
    <div class="hero-eyebrow">AI-Powered SEO Intelligence</div>
    <div class="hero-title">RANKSPY<span class="hero-title-accent">AI</span></div>
    <p class="hero-sub">SEO Audit & Competitor Intel. Powered by AI, driven by data.</p>
    <div class="hero-badges">
        <span class="hero-badge">Real-Time Intelligence</span>
        <span class="hero-badge">Competitive Benchmarking</span>
        <span class="hero-badge">Technical SEO Audit</span>
        <span class="hero-badge">AI-Powered Insights</span>
        <span class="hero-badge">Enterprise-Grade Analysis</span>
        <span class="hero-badge">Strategic Action Plans</span>
    </div>
</div>

<div class="ticker-wrap">
    <div class="ticker-track">
        <span class="ticker-item">SEO Analysis</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Competitor Intelligence</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Technical Audit</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Keyword Strategy</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">AI-Powered Insights</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">SERP Benchmarking</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Content Scoring</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Schema Markup</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Core Web Vitals</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Backlink Analysis</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">SEO Analysis</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Competitor Intelligence</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Technical Audit</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Keyword Strategy</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">AI-Powered Insights</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">SERP Benchmarking</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Content Scoring</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Schema Markup</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Core Web Vitals</span><span class="ticker-dot">✦</span>
        <span class="ticker-item">Backlink Analysis</span><span class="ticker-dot">✦</span>
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

# Mobile preview toggle
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = False

if st.session_state.mobile_mode:
    st.markdown("""
<style>
[data-testid="block-container"] {
    max-width: 390px !important;
    margin: 0 auto !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    border-left: 1px solid rgba(255,255,255,0.06) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    min-height: 100vh !important;
}
.stColumns { flex-wrap: wrap !important; }
.stColumn { min-width: 100% !important; flex: 100% !important; }
</style>
""", unsafe_allow_html=True)

# Corner buttons — fixed position HTML so they never stack on mobile
_mob_active = st.session_state.mobile_mode
_mob_label = "📱 Mobile View" if not _mob_active else "📱 Exit Mobile"
_corner_btns_html = f"""
<style>
#corner-btns {{ position:fixed; top:12px; right:16px; z-index:10000; display:flex; gap:8px; align-items:center; }}
#corner-btns a {{
    background:#111; border:1px solid rgba(255,255,255,0.12); color:rgba(255,255,255,0.7);
    font-size:0.65rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
    padding:6px 12px; border-radius:50px; text-decoration:none; cursor:pointer;
    white-space:nowrap;
}}
#corner-btns a:hover {{ background:#1a1a1a; color:#fff; }}
#corner-btns a.active {{ background:rgba(176,32,37,0.2); border-color:rgba(176,32,37,0.5); color:#ff6b6b; }}
</style>
<div id="corner-btns">
  <a href="?mobile_toggle=1" class="{'active' if _mob_active else ''}">{_mob_label}</a>
</div>
"""
st.markdown(_corner_btns_html, unsafe_allow_html=True)

# Handle mobile toggle via query param
if st.query_params.get("mobile_toggle"):
    st.session_state.mobile_mode = not st.session_state.mobile_mode
    st.query_params.clear()
    st.rerun()

if st.session_state.mobile_mode:
    st.markdown("""
<div style="position:fixed;bottom:16px;left:50%;transform:translateX(-50%);z-index:9999;
    background:#B02025;color:#fff;font-size:0.6rem;font-weight:800;letter-spacing:0.1em;
    text-transform:uppercase;padding:0.3rem 0.85rem;border-radius:50px;pointer-events:none;
    white-space:nowrap;box-shadow:0 4px 20px rgba(176,32,37,0.5);">
  📱 Smartphone View Active
</div>
""", unsafe_allow_html=True)

# Hidden admin button (top-right, small)
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
        used = _get_global_uses()
        rem = max(0, GLOBAL_LIMIT - used)
        bar_color = "#00C853" if rem == GLOBAL_LIMIT else "#FFA726" if rem > 0 else "#EF5350"
        badge_text = f'<strong style="color:{bar_color}">{rem}</strong> / {GLOBAL_LIMIT} free tries left'
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

toggle_label = "— COMPARE SPECIFIC URLS" if st.session_state.show_compare_urls else "+ COMPARE SPECIFIC URLS"
_tc1, _tc2 = st.columns([2, 5])
with _tc1:
    st.button(toggle_label, key="toggle_compare", type="secondary", use_container_width=True,
              on_click=lambda: st.session_state.update(show_compare_urls=not st.session_state.show_compare_urls))

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

_own_keys_label = "— BRING YOUR OWN API KEYS" if st.session_state.show_own_keys else "+ BRING YOUR OWN API KEYS"
_tk1, _tk2 = st.columns([2, 5])
with _tk1:
    st.button(_own_keys_label, key="toggle_own_keys", type="secondary", use_container_width=True,
              on_click=lambda: st.session_state.update(show_own_keys=not st.session_state.show_own_keys))

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

st.markdown("<br><br>", unsafe_allow_html=True)

# ==================== ACTION BUTTONS ====================

col_btn1, col_btn2, col_spacer = st.columns([2, 2, 3])

with col_btn1:
    analyze_clicked = st.button("🔍 Analyze SEO", use_container_width=True, type="primary")

with col_btn2:
    competitors_clicked = st.button("🎯 Find Competitors", use_container_width=True, type="secondary")

# ==================== RESULTS TOGGLE (inline, below buttons) ====================

_has_seo  = st.session_state.seo_data is not None
_has_comp = st.session_state.comp_data is not None

if _has_seo or _has_comp:
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    st.markdown("""<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.25);
letter-spacing:0.18em;text-transform:uppercase;margin-bottom:0.4rem;">Switch Results View</div>""", unsafe_allow_html=True)
    _t1, _t2, _spacer = st.columns([1.4, 1.8, 8])
    with _t1:
        if st.button("SEO Analysis", key="view_seo",
                     type="primary" if st.session_state.results_view == "seo" else "secondary",
                     disabled=not _has_seo):
            st.session_state.results_view = "seo"
            st.rerun()
    with _t2:
        if st.button("Competitor Intel", key="view_comp",
                     type="primary" if st.session_state.results_view == "comp" else "secondary",
                     disabled=not _has_comp):
            st.session_state.results_view = "comp"
            st.rerun()
    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:0.8rem 0 0;'>", unsafe_allow_html=True)

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
        You've used all <strong>4 free analyses</strong> from your IP address.<br>
        Click <strong style="color:#7EC7A3;">+ USE YOUR OWN API KEYS</strong> above to continue with unlimited access using your own free API keys.
    </div>
</div>""", unsafe_allow_html=True)
        st.stop()
    
    if url and keyword:
        try:
            # ── Styled loading card ──
            loading_card = st.empty()
            progress_bar = st.progress(0)

            def _set_step(label, pct, step=1, total=5):
                steps_html = "".join([
                    f'<div style="width:8px;height:8px;border-radius:50%;background:'
                    f'{"#B02025" if i < step else ("rgba(176,32,37,0.4)" if i == step else "rgba(255,255,255,0.1)")};">'
                    f'</div>' for i in range(1, total+1)
                ])
                loading_card.markdown(f"""
<div style="background:#0d0d0d;border:1px solid rgba(176,32,37,0.2);border-radius:14px;
            padding:1.4rem 2rem;margin:0.8rem 0;display:flex;align-items:center;gap:1.5rem;">
    <div style="flex-shrink:0;">
        <div style="width:44px;height:44px;border-radius:50%;
                    border:2px solid rgba(176,32,37,0.3);
                    border-top-color:#B02025;
                    animation:spin 1s linear infinite;
                    display:flex;align-items:center;justify-content:center;">
        </div>
    </div>
    <div style="flex:1;">
        <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.15em;
                    text-transform:uppercase;color:#B02025;margin-bottom:0.3rem;">
            Analyzing — Step {step} of {total}
        </div>
        <div style="font-size:0.95rem;font-weight:600;color:rgba(255,255,255,0.85);">
            {label}
        </div>
    </div>
    <div style="display:flex;gap:6px;align-items:center;">{steps_html}</div>
</div>
""", unsafe_allow_html=True)
                progress_bar.progress(pct)

            _set_step("Fetching page content", 20, 1)
            time.sleep(0.2)

            st.session_state.keyword = keyword
            st.session_state.url = url
            st.session_state.has_seo_results = False

            soup, raw_html = get_page_soup(url)

            _set_step("Extracting SEO elements", 40, 2)
            time.sleep(0.2)

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
            _set_step("Running technical SEO audit", 60, 3)
            time.sleep(0.2)

            tech_seo = check_technical_seo(url, soup)
            has_schema = has_schema_markup(soup)

            _set_step("Calculating SEO score", 80, 4)
            time.sleep(0.2)

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
                    _set_step("Fetching Core Web Vitals", 90, 5)
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
            loading_card.empty()
            progress_bar.empty()

            # Increment IP usage counter
            if not _using_own_keys():
                _increment_global_uses()
            _render_badge(_badge_placeholder)
            # Store all SEO results in session state for persistent display
            st.session_state.seo_data = dict(
                url=url, keyword=keyword, score=score, summary=summary,
                recommended_fixes=recommended_fixes, wc=wc, kc=kc, kd=kd,
                internal=internal, external=external, missing_alt=missing_alt,
                title=title, meta=meta, h1=h1,
                title_has_keyword=title_has_keyword, meta_has_keyword=meta_has_keyword,
                h1_has_keyword=h1_has_keyword, token_counts=token_counts,
                token_coverage=token_coverage, title_len=title_len, meta_len=meta_len,
                tech_seo=tech_seo, has_schema=has_schema, pagespeed_data=pagespeed_data,
                soup=soup, compare_url=compare_url, venue_urls_text=venue_urls_text,
            )
            st.session_state.results_view = "seo"
            st.session_state.has_seo_results = True

            # ==================== DISPLAY RESULTS ====================
            _render_seo_results(st.session_state.seo_data)

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
        You've used all <strong>4 free analyses</strong> from your IP address.<br>
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
            _increment_global_uses()
        _render_badge(_badge_placeholder)
        try:
            from competitor_utils import get_competitors_via_gemini
            from location_utils import get_location_from_url

            st.markdown("---")

            # ── Step 1: Ask Gemini for competitors ──────────────────────────
            location = get_location_from_url(url)
            country = location['country_name'] if location and location.get('country_name') else "global"

            # Fetch SERP results to pass as context to Gemini
            _serp_results = []
            if serp_key:
                try:
                    from serp_utils import get_serp_results
                    _serp_results = get_serp_results(keyword, serp_key) or []
                except Exception:
                    pass

            with st.spinner(f"🤖 Asking AI: who are the direct competitors of {url} for '{keyword}'?"):
                try:
                    gemini_competitors = get_competitors_via_gemini(
                        url, keyword, gemini_api_key, location, serp_results=_serp_results
                    )
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

            _SEO_FACTS = [
                ("75% of users never scroll past the first page of Google results.", "Search Behavior"),
                ("Pages with a meta description get 5.8% more clicks than those without.", "Meta Tags"),
                ("Google uses over 200 ranking factors to determine search position.", "Algorithm"),
                ("Sites that load in 1s convert 3x more than sites that load in 5s.", "Page Speed"),
                ("Schema markup can increase click-through rates by up to 30%.", "Structured Data"),
                ("Content with images gets 94% more views than text-only content.", "Content"),
                ("Mobile traffic now accounts for over 60% of all web searches.", "Mobile SEO"),
                ("AI tools like ChatGPT cite sources with strong E-E-A-T signals far more often.", "GEO"),
                ("Backlinks remain one of the top 3 Google ranking factors in 2024.", "Off-Page SEO"),
                ("The average first-page Google result contains 1,447 words.", "Content"),
                ("LLMs.txt helps AI crawlers understand your site structure and purpose.", "AI Visibility"),
                ("Sites with HTTPS rank higher — Google confirmed it as a ranking signal.", "Technical SEO"),
                ("Internal linking boosts crawlability and distributes page authority.", "Link Structure"),
                ("53% of mobile users abandon a site that takes more than 3 seconds to load.", "Page Speed"),
                ("H1 tags with your target keyword improve on-page relevance signals.", "On-Page SEO"),
                ("Gemini AI is being used right now to score your competitors. Hang tight.", "RankSpyAI"),
                ("RankSpyAI checks 70+ SEO factors including Core Web Vitals and schema.", "RankSpyAI"),
                ("Your GEO score measures how likely AI engines are to cite your website.", "RankSpyAI"),
                ("First-page Google results have an average of 3.8x more backlinks than results on page 2.", "Off-Page SEO"),
                ("Websites with a blog generate 55% more traffic than those without.", "Content"),
                ("Once results load, switch between SEO Analysis and Competitor Intel views anytime using the buttons at the top.", "RankSpyAI Tip"),
                ("You can download your full competitor report as a CSV — look for the download button in the results.", "RankSpyAI Tip"),
                ("RankSpyAI gives you two reports in one — your full SEO audit AND a competitor benchmark table.", "RankSpyAI Tip"),
            ]

            benchmark_rows = []
            total = len(gemini_competitors) + 1
            _fact_idx = [0]
            _overlay = st.empty()

            def _render_overlay(done, current_name=""):
                fact, tag = _SEO_FACTS[_fact_idx[0] % len(_SEO_FACTS)]
                pct = int((done / total) * 100)
                _fact_idx[0] += 1
                _overlay.markdown(f"""
<div style="position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.93);
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            font-family:'Space Grotesk','Outfit',sans-serif;">

  <!-- Top label -->
  <div style="position:absolute;top:2rem;left:2.5rem;">
    <div style="font-size:0.6rem;font-weight:800;letter-spacing:0.25em;
                text-transform:uppercase;color:#B02025;">RankSpyAI</div>
    <div style="font-size:0.75rem;color:rgba(255,255,255,0.3);margin-top:0.2rem;">
        Working hard to get you the right intel...
    </div>
  </div>

  <!-- Centre: fact card -->
  <div style="max-width:640px;width:90%;text-align:center;padding:0 1rem;">
    <div style="font-size:0.6rem;font-weight:800;letter-spacing:0.25em;
                text-transform:uppercase;color:#B02025;margin-bottom:1.2rem;">
        Did you know &nbsp;·&nbsp; {tag}
    </div>
    <div style="font-size:clamp(1.1rem,2.5vw,1.6rem);font-weight:600;
                color:rgba(255,255,255,0.85);line-height:1.5;">
        {fact}
    </div>
  </div>

  <!-- Bottom bar -->
  <div style="position:absolute;bottom:0;left:0;right:0;padding:1.5rem 2.5rem;">
    <!-- Progress bar -->
    <div style="background:rgba(255,255,255,0.07);border-radius:4px;height:3px;
                margin-bottom:0.9rem;overflow:hidden;">
      <div style="background:linear-gradient(90deg,#B02025,#ff4444);
                  height:100%;width:{pct}%;transition:width 0.4s ease;border-radius:4px;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);">
        {"Analyzing your site..." if done == 0 else f"Analyzing competitor {done}/{len(gemini_competitors)}: {current_name}"}
      </div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.25);">
        {done} / {total} &nbsp;·&nbsp; {pct}% complete
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            import threading

            _stop_flag = [False]
            _current_done = [0]
            _current_name = [""]

            # Fact rotator thread — updates overlay every 4s independently
            def _fact_rotator():
                while not _stop_flag[0]:
                    _render_overlay(_current_done[0], _current_name[0])
                    for _ in range(40):  # check stop every 0.1s, total 4s
                        if _stop_flag[0]:
                            break
                        time.sleep(0.1)

            _render_overlay(0)
            _t = threading.Thread(target=_fact_rotator, daemon=True)
            _t.start()

            try:
                primary_data = analyze_venue(url, keyword)
                primary_data["Role"] = "🏠 Your Site"
                primary_data["Venue Name"] = url.replace("https://","").replace("http://","").replace("www.","").split("/")[0]
                benchmark_rows.append(primary_data)
            except Exception as e:
                st.warning(f"Could not analyze primary URL: {e}")

            # ── Step 3: Analyze each competitor ─────────────────────────────
            for idx, comp in enumerate(gemini_competitors):
                comp_url = comp.get("website") or f"https://{comp.get('domain', '')}"
                comp_name = comp.get("name", comp_url)
                if not comp_url or comp_url == "https://":
                    continue
                _current_done[0] = idx + 1
                _current_name[0] = comp_name
                try:
                    row = analyze_venue(comp_url, keyword)
                    row["Venue Name"] = comp_name  # use Gemini's brand name
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

            _stop_flag[0] = True
            _t.join(timeout=1)

            if not benchmark_rows:
                _overlay.empty()
                st.warning("No data to display.")
                st.stop()

            _overlay.empty()

            # Store competitor results in session state
            st.session_state.comp_data = dict(
                url=url, keyword=keyword, country=country,
                benchmark_rows=benchmark_rows,
                gemini_competitors=gemini_competitors,
            )
            st.session_state.results_view = "comp"

            # ── Step 4: Display results ─────────────────────────────────
            _render_comp_results(st.session_state.comp_data)

        except Exception as e:
            st.error(f"❌ Competitor analysis error: {e}")

# Render stored results when toggle is used (no new analysis running)
if not analyze_clicked and not competitors_clicked:
    if st.session_state.results_view == "seo" and st.session_state.seo_data:
        _render_seo_results(st.session_state.seo_data)
    elif st.session_state.results_view == "comp" and st.session_state.comp_data:
        _render_comp_results(st.session_state.comp_data)
    elif not st.session_state.seo_data and not st.session_state.comp_data:
        # ── What is SEO ──
        st.markdown("""
<div style="margin:3rem 0 1.2rem;">
  <div style="font-size:0.75rem;letter-spacing:0.18em;color:#B02025;text-transform:uppercase;font-weight:700;margin-bottom:0.5rem;">SEO Explained</div>
  <div style="font-size:1.9rem;font-weight:800;color:#fff;line-height:1.2;">What is SEO & why does it matter?</div>
  <div style="font-size:0.95rem;color:rgba(255,255,255,0.5);margin-top:0.5rem;max-width:580px;">Search Engine Optimisation is how your website earns free, organic traffic from Google — without paying for ads.</div>
</div>
""", unsafe_allow_html=True)

        sa, sb, sc, sd = st.columns(4)
        _seo_cards = [
            (sa, "🔍", "Higher Rankings", "Appear on page 1 of Google when customers search for your products or services."),
            (sb, "📈", "More Organic Traffic", "Drive a steady stream of visitors without spending on ads — 24/7, for free."),
            (sc, "🏆", "Beat Competitors", "Understand exactly what your rivals are doing and outrank them with data."),
            (sd, "💼", "Build Trust", "Sites that rank high are perceived as credible. SEO signals authority to both Google and your customers."),
        ]
        for col, icon, title, body in _seo_cards:
            with col:
                st.markdown(f"""
<div style="background:#0d0d0d;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:1.3rem 1.1rem 1.4rem;height:100%;box-sizing:border-box;">
  <div style="font-size:2rem;margin-bottom:0.7rem;">{icon}</div>
  <div style="font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:0.45rem;">{title}</div>
  <div style="font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.55;">{body}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:2.5rem;'></div>", unsafe_allow_html=True)

        # ── How It Works ──
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
<div style="background:#0d0d0d;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:1.4rem;height:100%;">
  <div style="font-size:2.2rem;font-weight:900;color:rgba(176,32,37,0.35);line-height:1;margin-bottom:0.8rem;">01</div>
  <div style="font-size:0.95rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">Enter your URL &amp; keyword</div>
  <div style="font-size:0.78rem;color:rgba(255,255,255,0.38);line-height:1.6;">Paste your website URL and the keyword you want to rank for. Optionally add competitor URLs to compare against.</div>
</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown("""
<div style="background:#0d0d0d;border:1px solid rgba(176,32,37,0.2);border-radius:14px;padding:1.4rem;height:100%;">
  <div style="font-size:2.2rem;font-weight:900;color:rgba(176,32,37,0.35);line-height:1;margin-bottom:0.8rem;">02</div>
  <div style="font-size:0.95rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">Choose your analysis</div>
  <div style="font-size:0.78rem;color:rgba(255,255,255,0.38);line-height:1.6;"><b style="color:rgba(255,255,255,0.6);">Analyze SEO</b> — full technical audit of your page.<br><b style="color:rgba(255,255,255,0.6);">Find Competitors</b> — AI discovers who outranks you on Google.</div>
</div>""", unsafe_allow_html=True)
        with c3:
            st.markdown("""
<div style="background:#0d0d0d;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:1.4rem;height:100%;">
  <div style="font-size:2.2rem;font-weight:900;color:rgba(176,32,37,0.35);line-height:1;margin-bottom:0.8rem;">03</div>
  <div style="font-size:0.95rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">Get your AI report</div>
  <div style="font-size:0.78rem;color:rgba(255,255,255,0.38);line-height:1.6;">100-point SEO score, competitor benchmarks, keyword gaps, GEO visibility, and a prioritized Gemini AI action plan. Switch between <b style="color:rgba(255,255,255,0.5);">SEO Analysis</b> and <b style="color:rgba(255,255,255,0.5);">Competitor Intel</b> views anytime.</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:2rem 0;'>", unsafe_allow_html=True)

        st.markdown("""
<style>
.lp-section { padding: 4rem 0 3rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
.lp-row { display: flex; align-items: center; gap: 3rem; }
.lp-row.reverse { flex-direction: row-reverse; }
.lp-text { flex: 1; }
.lp-graphic { flex: 1; }
.lp-eyebrow {
    font-size: 0.65rem; font-weight: 800; letter-spacing: 0.22em;
    text-transform: uppercase; color: #B02025; margin-bottom: 0.6rem;
}
.lp-heading {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: clamp(1.8rem, 3vw, 2.6rem);
    font-weight: 800; color: #ffffff; line-height: 1.1;
    margin: 0 0 0.5rem;
}
.lp-heading span { color: #B02025; }
.lp-desc {
    font-size: 0.9rem; color: rgba(255,255,255,0.45);
    line-height: 1.7; margin-bottom: 1.2rem; max-width: 480px;
}
.lp-bullets { list-style: none; padding: 0; margin: 0; }
.lp-bullets li {
    font-size: 0.85rem; color: rgba(255,255,255,0.6);
    padding: 0.35rem 0; display: flex; align-items: center; gap: 0.6rem;
}
.lp-bullets li::before {
    content: ''; width: 6px; height: 6px; border-radius: 50%;
    background: #B02025; flex-shrink: 0;
}
.lp-mock {
    background: #0d0d0d;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.4rem;
    position: relative;
}
.lp-mock-bar {
    display: flex; gap: 5px; margin-bottom: 1rem;
}
.lp-mock-dot {
    width: 8px; height: 8px; border-radius: 50%;
}
.lp-mock-row {
    display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.6rem;
}
.lp-mock-label {
    font-size: 0.65rem; color: rgba(255,255,255,0.3);
    text-transform: uppercase; letter-spacing: 0.1em; width: 90px; flex-shrink: 0;
}
.lp-mock-bar-fill {
    height: 6px; border-radius: 3px; flex: 1;
}
.lp-mock-score {
    font-size: 2.5rem; font-weight: 900;
    font-family: 'Barlow Condensed', sans-serif;
    margin-bottom: 0.3rem;
}
.lp-mock-tag {
    display: inline-block;
    font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; padding: 3px 10px; border-radius: 20px;
    margin: 2px;
}
.lp-divider {
    border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 0;
}

@media (max-width: 768px) {
    /* Hero */
    .hero-header { padding: 1.2rem 1rem 1rem !important; margin: 0 -1rem 1rem !important; }
    .hero-title { font-size: 2.8rem !important; }
    .hero-sub { font-size: 0.8rem !important; }
    .hero-badges { gap: 0.4rem !important; }
    .hero-badge { font-size: 0.6rem !important; padding: 5px 10px !important; }

    /* Input card */
    .input-card { padding: 1.2rem 1rem 1rem !important; }

    /* Marketing sections */
    .lp-row { flex-direction: column !important; gap: 1.5rem !important; }
    .lp-row.reverse { flex-direction: column !important; }
    .lp-graphic { width: 100% !important; }
    .lp-mock { max-width: 100% !important; }
    .lp-heading { font-size: 1.6rem !important; }
    .lp-desc { font-size: 0.85rem !important; }
    .lp-section { padding: 2rem 0 1.5rem !important; }
    .lp-bullet { font-size: 0.82rem !important; }

    /* Streamlit columns — stack on mobile */
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Ticker */
    .ticker-wrap { font-size: 0.6rem !important; }

    /* General spacing */
    [data-testid="block-container"] { padding-left: 1rem !important; padding-right: 1rem !important; }
}
</style>

<!-- SECTION 1: SEO Audit -->
<div class="lp-section">
  <div class="lp-row">
    <div class="lp-text">
      <div class="lp-eyebrow">SEO Audit</div>
      <div class="lp-heading">Full technical audit.<br><span>100-point score.</span></div>
      <p class="lp-desc">RankSpyAI scans your page for every factor that affects your Google ranking — from meta tags to Core Web Vitals.</p>
      <ul class="lp-bullets">
        <li>Title, meta description & heading analysis</li>
        <li>Core Web Vitals & PageSpeed scores</li>
        <li>Schema markup & structured data check</li>
        <li>Canonical, robots & indexability audit</li>
        <li>Mobile responsiveness & image optimization</li>
      </ul>
    </div>
    <div class="lp-graphic">
      <div class="lp-mock">
        <div class="lp-mock-bar">
          <div class="lp-mock-dot" style="background:#ff5f57;"></div>
          <div class="lp-mock-dot" style="background:#febc2e;"></div>
          <div class="lp-mock-dot" style="background:#28c840;"></div>
        </div>
        <div style="margin-bottom:1rem;">
          <div class="lp-mock-score" style="color:#7EC7A3;">87</div>
          <div style="font-size:0.7rem;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.12em;">SEO Score</div>
        </div>
        <div class="lp-mock-row"><span class="lp-mock-label">On-Page</span><div class="lp-mock-bar-fill" style="background:linear-gradient(90deg,#7EC7A3,#3d9970);width:88%;"></div></div>
        <div class="lp-mock-row"><span class="lp-mock-label">Technical</span><div class="lp-mock-bar-fill" style="background:linear-gradient(90deg,#B02025,#ff4444);width:62%;"></div></div>
        <div class="lp-mock-row"><span class="lp-mock-label">Content</span><div class="lp-mock-bar-fill" style="background:linear-gradient(90deg,#f5a623,#e8890a);width:75%;"></div></div>
        <div class="lp-mock-row"><span class="lp-mock-label">Speed</span><div class="lp-mock-bar-fill" style="background:linear-gradient(90deg,#7EC7A3,#3d9970);width:91%;"></div></div>
        <div style="margin-top:1rem;display:flex;gap:0.4rem;flex-wrap:wrap;">
          <span class="lp-mock-tag" style="background:rgba(176,32,37,0.15);color:#ff6b6b;border:1px solid rgba(176,32,37,0.3);">✗ Missing meta desc</span>
          <span class="lp-mock-tag" style="background:rgba(126,199,163,0.1);color:#7EC7A3;border:1px solid rgba(126,199,163,0.2);">✓ Schema found</span>
          <span class="lp-mock-tag" style="background:rgba(245,166,35,0.1);color:#f5a623;border:1px solid rgba(245,166,35,0.2);">⚠ Slow LCP</span>
        </div>
      </div>
    </div>
  </div>
</div>
<hr class="lp-divider"/>

<!-- SECTION 2: Competitor Intel -->
<div class="lp-section">
  <div class="lp-row reverse">
    <div class="lp-text">
      <div class="lp-eyebrow">Competitor Intel</div>
      <div class="lp-heading">See who's beating<br><span>you on Google.</span></div>
      <p class="lp-desc">RankSpyAI automatically identifies your real competitors from SERP data and benchmarks your SEO scores against theirs.</p>
      <ul class="lp-bullets">
        <li>AI-identified top SERP competitors</li>
        <li>Side-by-side SEO score comparison</li>
        <li>Gap analysis — where you're losing</li>
        <li>Domain authority & backlink signals</li>
        <li>Content depth & keyword overlap</li>
      </ul>
    </div>
    <div class="lp-graphic">
      <div class="lp-mock">
        <div class="lp-mock-bar">
          <div class="lp-mock-dot" style="background:#ff5f57;"></div>
          <div class="lp-mock-dot" style="background:#febc2e;"></div>
          <div class="lp-mock-dot" style="background:#28c840;"></div>
        </div>
        <div style="font-size:0.6rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.25);margin-bottom:0.8rem;">Competitor Benchmark</div>
        <div style="display:flex;flex-direction:column;gap:0.5rem;">
          <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(176,32,37,0.08);border:1px solid rgba(176,32,37,0.2);border-radius:8px;padding:0.5rem 0.8rem;">
            <span style="font-size:0.75rem;color:rgba(255,255,255,0.7);">yoursite.com</span>
            <span style="font-size:1rem;font-weight:800;color:#7EC7A3;">87</span>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:0.5rem 0.8rem;">
            <span style="font-size:0.75rem;color:rgba(255,255,255,0.4);">competitor1.com</span>
            <span style="font-size:1rem;font-weight:800;color:#f5a623;">92</span>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:0.5rem 0.8rem;">
            <span style="font-size:0.75rem;color:rgba(255,255,255,0.4);">competitor2.com</span>
            <span style="font-size:1rem;font-weight:800;color:#ff6b6b;">74</span>
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:0.5rem 0.8rem;">
            <span style="font-size:0.75rem;color:rgba(255,255,255,0.4);">competitor3.com</span>
            <span style="font-size:1rem;font-weight:800;color:#ff6b6b;">68</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<hr class="lp-divider"/>

<!-- SECTION 3: AI Insights -->
<div class="lp-section">
  <div class="lp-row">
    <div class="lp-text">
      <div class="lp-eyebrow">AI-Powered Insights</div>
      <div class="lp-heading">Not just data.<br><span>Actionable strategy.</span></div>
      <p class="lp-desc">Gemini AI reads your full audit and writes a prioritized action plan — telling you exactly what to fix first and why.</p>
      <ul class="lp-bullets">
        <li>Executive summary of your SEO health</li>
        <li>Prioritized fix list by impact</li>
        <li>Keyword opportunity detection</li>
        <li>Strategic recommendations vs competitors</li>
        <li>GEO / AI visibility scoring</li>
      </ul>
    </div>
    <div class="lp-graphic">
      <div class="lp-mock">
        <div class="lp-mock-bar">
          <div class="lp-mock-dot" style="background:#ff5f57;"></div>
          <div class="lp-mock-dot" style="background:#febc2e;"></div>
          <div class="lp-mock-dot" style="background:#28c840;"></div>
        </div>
        <div style="font-size:0.6rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.25);margin-bottom:0.8rem;">AI Strategy Report</div>
        <div style="display:flex;flex-direction:column;gap:0.6rem;">
          <div style="background:rgba(176,32,37,0.08);border-left:3px solid #B02025;border-radius:0 8px 8px 0;padding:0.6rem 0.8rem;">
            <div style="font-size:0.6rem;font-weight:700;color:#ff6b6b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.2rem;">High Priority</div>
            <div style="font-size:0.78rem;color:rgba(255,255,255,0.7);">Add meta description — currently missing</div>
          </div>
          <div style="background:rgba(245,166,35,0.06);border-left:3px solid #f5a623;border-radius:0 8px 8px 0;padding:0.6rem 0.8rem;">
            <div style="font-size:0.6rem;font-weight:700;color:#f5a623;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.2rem;">Medium Priority</div>
            <div style="font-size:0.78rem;color:rgba(255,255,255,0.7);">Compress images to improve LCP score</div>
          </div>
          <div style="background:rgba(126,199,163,0.06);border-left:3px solid #7EC7A3;border-radius:0 8px 8px 0;padding:0.6rem 0.8rem;">
            <div style="font-size:0.6rem;font-weight:700;color:#7EC7A3;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.2rem;">Opportunity</div>
            <div style="font-size:0.78rem;color:rgba(255,255,255,0.7);">Target keyword "SEO audit tool" — low competition</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<hr class="lp-divider"/>

<!-- SECTION 4: GEO / AI Visibility -->
<div class="lp-section" style="border-bottom:none;">
  <div class="lp-row reverse">
    <div class="lp-text">
      <div class="lp-eyebrow">GEO & AI Visibility</div>
      <div class="lp-heading">Rank in ChatGPT,<br><span>Gemini & Perplexity.</span></div>
      <p class="lp-desc">Search is shifting to AI. RankSpyAI scores how likely your site is to be cited by LLMs — and what's stopping it.</p>
      <ul class="lp-bullets">
        <li>AI crawler access check (GPTBot, ClaudeBot)</li>
        <li>LLMs.txt presence & configuration</li>
        <li>E-E-A-T signal detection</li>
        <li>Citability score out of 100</li>
        <li>Structured data for AI readability</li>
      </ul>
    </div>
    <div class="lp-graphic">
      <div class="lp-mock">
        <div class="lp-mock-bar">
          <div class="lp-mock-dot" style="background:#ff5f57;"></div>
          <div class="lp-mock-dot" style="background:#febc2e;"></div>
          <div class="lp-mock-dot" style="background:#28c840;"></div>
        </div>
        <div style="margin-bottom:1rem;">
          <div class="lp-mock-score" style="color:#B02025;">42</div>
          <div style="font-size:0.7rem;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.12em;">GEO Visibility Score</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:0.45rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.72rem;color:rgba(255,255,255,0.45);">GPTBot access</span>
            <span style="font-size:0.72rem;color:#7EC7A3;font-weight:700;">✓ Allowed</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.72rem;color:rgba(255,255,255,0.45);">ClaudeBot access</span>
            <span style="font-size:0.72rem;color:#7EC7A3;font-weight:700;">✓ Allowed</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.72rem;color:rgba(255,255,255,0.45);">LLMs.txt</span>
            <span style="font-size:0.72rem;color:#ff6b6b;font-weight:700;">✗ Missing</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.72rem;color:rgba(255,255,255,0.45);">E-E-A-T signals</span>
            <span style="font-size:0.72rem;color:#f5a623;font-weight:700;">⚠ Weak</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.72rem;color:rgba(255,255,255,0.45);">Structured data</span>
            <span style="font-size:0.72rem;color:#7EC7A3;font-weight:700;">✓ Present</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<hr class="lp-divider"/>

<!-- SECTION 5: Switch & Download -->
<div class="lp-section" style="border-bottom:none;">
  <div class="lp-row">
    <div class="lp-text">
      <div class="lp-eyebrow">Results &amp; Reports</div>
      <div class="lp-heading">Two reports.<br><span>One click away.</span></div>
      <p class="lp-desc">After your analysis runs, switch between your full SEO audit and the competitor benchmark table instantly. Download everything as a CSV.</p>
      <ul class="lp-bullets">
        <li>Switch between SEO Analysis and Competitor Intel views</li>
        <li>Download full competitor table as CSV</li>
        <li>Executive AI summary in every report</li>
        <li>Keyword opportunity breakdown</li>
        <li>Prioritized action plan by impact</li>
      </ul>
    </div>
    <div class="lp-graphic">
      <div class="lp-mock">
        <div class="lp-mock-bar">
          <div class="lp-mock-dot" style="background:#ff5f57;"></div>
          <div class="lp-mock-dot" style="background:#febc2e;"></div>
          <div class="lp-mock-dot" style="background:#28c840;"></div>
        </div>
        <div style="font-size:0.55rem;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.2);margin-bottom:0.8rem;">Switch Results View</div>
        <div style="display:flex;gap:0.5rem;margin-bottom:1.2rem;">
          <div style="flex:1;background:#B02025;border-radius:50px;padding:0.5rem 0;text-align:center;font-size:0.65rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#fff;">SEO Analysis</div>
          <div style="flex:1;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:50px;padding:0.5rem 0;text-align:center;font-size:0.65rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.4);">Competitor Intel</div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.6rem;">
          <div style="font-size:0.6rem;font-weight:700;color:#B02025;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.3rem;">SEO Score</div>
          <div style="font-size:1.8rem;font-weight:900;color:#7EC7A3;line-height:1;">87<span style="font-size:0.8rem;color:rgba(255,255,255,0.25);font-weight:400;">/100</span></div>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:0.5rem;background:rgba(126,199,163,0.06);border:1px solid rgba(126,199,163,0.15);border-radius:8px;padding:0.55rem 1rem;">
          <span style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#7EC7A3;">⬇ Download CSV Report</span>
        </div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── FAQ Section ──
        st.markdown("""
<div style="padding:4rem 0 2rem;text-align:center;">
  <div style="font-size:0.65rem;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:#B02025;margin-bottom:0.6rem;">FAQ</div>
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:clamp(1.8rem,3vw,2.6rem);font-weight:800;color:#ffffff;line-height:1.1;margin-bottom:0.5rem;">Frequently asked <span style="color:#B02025;">questions.</span></div>
  <div style="font-size:0.88rem;color:rgba(255,255,255,0.35);margin-bottom:1rem;">Everything you need to know about RankSpyAI.</div>
</div>
""", unsafe_allow_html=True)

        faqs = [
            ("What is RankSpyAI?",
             "RankSpyAI is a free AI-powered SEO audit and competitor intelligence tool. It analyzes your website, gives you a 100-point SEO score, identifies technical issues, and shows you exactly how you stack up against competitors — all powered by Gemini AI."),
            ("How does the SEO Audit work?",
             "Enter your URL and target keyword, then click Analyze SEO. RankSpyAI fetches your page, scans 70+ SEO factors including meta tags, Core Web Vitals, schema markup, heading structure, internal links, and more — then generates a prioritized action plan."),
            ("What does Find Competitors do?",
             "Find Competitors uses Serper API to pull real Google SERP data for your keyword, then Gemini AI identifies your actual competitors. You get a side-by-side SEO score comparison showing where you are winning and where you are losing."),
            ("What is the GEO / AI Visibility score?",
             "GEO stands for Generative Engine Optimization — how well your site is optimized to appear in AI-powered search engines like ChatGPT, Gemini, and Perplexity. RankSpyAI checks your AI crawler access, LLMs.txt file, E-E-A-T signals, and citability."),
            ("Is it really free?",
             "Yes. You get 30 free analyses shared across all users. For unlimited access, simply add your own free API keys (Serper and Gemini are both free to get) in the Bring Your Own API Keys section."),
            ("What API keys do I need for unlimited access?",
             "You need a Serper API key (free at serper.dev) and a Gemini API key (free at aistudio.google.com). Optionally add a Google PageSpeed API key for detailed performance metrics. Keys are stored only in your browser session and never saved."),
            ("How is this different from other SEO tools?",
             "Most SEO tools give you raw data. RankSpyAI uses Gemini AI to interpret that data and write a strategic action plan specific to your site and keyword. It also combines traditional SEO scoring with GEO/AI visibility — something most tools do not offer yet."),
        ]

        faq_html = '<div style="max-width:780px;margin:0 auto;">'
        for q, a in faqs:
            faq_html += f"""
<details style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;margin-bottom:0.6rem;background:#0d0d0d;padding:0;overflow:hidden;">
  <summary style="padding:1rem 1.2rem;font-size:0.95rem;font-weight:600;color:#fff;cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;">
    {q}
    <span style="font-size:1.1rem;color:#B02025;margin-left:1rem;flex-shrink:0;">＋</span>
  </summary>
  <div style="padding:0 1.2rem 1rem;font-size:0.87rem;color:rgba(255,255,255,0.5);line-height:1.75;border-top:1px solid rgba(255,255,255,0.05);padding-top:0.8rem;">{a}</div>
</details>"""
        faq_html += '</div>'
        st.markdown(faq_html, unsafe_allow_html=True)

        st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
