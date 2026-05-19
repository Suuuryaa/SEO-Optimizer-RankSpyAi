import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import serp_utils
import time
from datetime import datetime
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
# Load from Streamlit secrets (cloud) or .env (local development)
default_pagespeed = ""
default_serper = ""
default_gemini = ""

try:
    # Try Streamlit Cloud secrets first
    default_pagespeed = st.secrets["PAGESPEED_API_KEY"]
    default_serper = st.secrets["SERPER_API_KEY"]
    default_gemini = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError, AttributeError):
    # Fall back to .env file for local development
    try:
        from dotenv import load_dotenv
        load_dotenv()
        default_pagespeed = os.getenv("PAGESPEED_API_KEY", "")
        default_serper = os.getenv("SERPER_API_KEY", "")
        default_gemini = os.getenv("GEMINI_API_KEY", "")
    except:
        pass

# Use keys directly in background - never expose to UI
pagespeed_api_key = default_pagespeed
serp_key = default_serper
gemini_api_key = default_gemini

# Daily usage limit for demo protection
DAILY_LIMIT = 50

if 'daily_uses' not in st.session_state:
    st.session_state.daily_uses = 0
    st.session_state.last_reset = date.today()

# Reset counter daily
if st.session_state.last_reset != date.today():
    st.session_state.daily_uses = 0
    st.session_state.last_reset = date.today()


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

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: 800;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================

st.title("🎯 SEO Intelligence Dashboard")
st.markdown("**Analyze, benchmark, and optimize your website's search performance**")
st.markdown("---")

# ==================== INPUT SECTION ====================

col1, col2 = st.columns(2)

with col1:
    url = st.text_input("🌐 Primary Venue URL", placeholder="https://example.com")
    keyword = st.text_input("🔑 Target Keyword", placeholder="mini golf auckland")

with col2:
    compare_url = st.text_input("📊 Comparison URL (optional)", placeholder="https://competitor.com")

# Show usage info instead of API configuration
st.info(f"💡 Demo mode: {DAILY_LIMIT - st.session_state.daily_uses} analyses remaining today")

st.markdown("### 🏆 Multi-Venue Leaderboard")
venue_urls_text = st.text_area(
    "Enter multiple venue URLs (one per line)",
    height=100,
    placeholder="https://venue1.com\nhttps://venue2.com\nhttps://venue3.com"
)

st.markdown("---")

# Action Buttons
col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 3])

with col_btn1:
    analyze_clicked = st.button("🔍 Analyze SEO", use_container_width=True, type="primary")

with col_btn2:
    competitors_clicked = st.button("🎯 Find Competitors", use_container_width=True)

# ==================== ANALYZE SECTION ====================


# ==================== ANALYZE SECTION ====================

if analyze_clicked:
    # Check daily limit
    if st.session_state.daily_uses >= DAILY_LIMIT:
        st.error(f"📊 Daily demo limit reached ({DAILY_LIMIT} analyses/day). Please try again tomorrow!")
        st.info("💡 Want unlimited usage? This is a portfolio demo with usage limits to protect API costs.")
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

            # Increment usage counter after successful analysis
            st.session_state.daily_uses += 1

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
                    st.markdown("### 📈 Key Metrics")
                    
                    metric_col1, metric_col2 = st.columns(2)
                    
                    with metric_col1:
                        st.metric("📝 Word Count", f"{wc:,}")
                        st.metric("🔑 Keyword Count", kc)
                        st.metric("🔗 Internal Links", len(internal))
                    
                    with metric_col2:
                        st.metric("📊 Keyword Density", f"{kd}%")
                        st.metric("🖼️ Missing ALT Tags", len(missing_alt))
                        st.metric("🌐 External Links", len(external))
                
                # Executive Summary
                st.markdown("### 📋 Executive Summary")
                summary_cols = st.columns(4)
                
                with summary_cols[0]:
                    st.info(f"**Status**\n\n{summary['Overall Status']}")
                with summary_cols[1]:
                    st.warning(f"**Top Issue**\n\n{summary['Top Issue']}")
                with summary_cols[2]:
                    st.success(f"**Strength**\n\n{summary['Strongest Area']}")
                with summary_cols[3]:
                    st.error(f"**Priority**\n\n{summary['Priority Action']}")

            with tab2:
                st.markdown("### 🔧 Technical SEO Audit")
                
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
    if not keyword:
        st.error("❌ Please enter a target keyword first.")
    elif not url:
        st.error("❌ Please enter the Primary Venue URL first.")
    elif not gemini_api_key:
        st.error("❌ Gemini API key not configured. Add GEMINI_API_KEY to Streamlit secrets.")
    else:
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
                    st.error(f"❌ Gemini failed: {e}")
                    gemini_competitors = []

            if not gemini_competitors:
                st.error("⚠️ Gemini returned an empty competitor list. The model may have returned non-JSON output.")
                st.stop()

            st.success(f"✅ AI identified {len(gemini_competitors)} competitors ({country})")

            # ── Step 2: Analyze primary venue ───────────────────────────────
            st.markdown("### 📊 SEO Score Comparison")
            st.markdown(f"Analyzing **{url}** and {len(gemini_competitors)} competitors against keyword: **{keyword}**")

            benchmark_rows = []
            progress = st.progress(0)
            total = len(gemini_competitors) + 1

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
                            "Score Band": "Error",
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

            # Score bar chart — primary highlighted
            fig = px.bar(
                benchmark_df,
                x="Venue Name",
                y="SEO Score",
                color="Role",
                text="SEO Score",
                color_discrete_map={"🏠 Primary Venue": "#667eea", "🎯 Competitor": "#FF7043"},
                title=f"SEO Score vs Competitors — keyword: '{keyword}'"
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-30, height=420, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

            # Summary metrics
            primary_row = next((r for r in benchmark_rows if "Primary" in r.get("Role", "")), None)
            if primary_row:
                best_comp = max(
                    [r for r in benchmark_rows if "Competitor" in r.get("Role", "")],
                    key=lambda x: x.get("SEO Score", 0),
                    default={}
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Your SEO Score", primary_row.get("SEO Score", 0))
                m2.metric("Best Competitor Score", best_comp.get("SEO Score", "N/A"))
                gap = primary_row.get("SEO Score", 0) - best_comp.get("SEO Score", 0)
                m3.metric("Gap vs Best", f"{gap:+d}", delta_color="normal")
                m4.metric("Competitors Analysed", len(gemini_competitors))

            # Full data table
            st.markdown("### 📋 Full Comparison Table")
            display_cols = ["Role", "Venue Name", "URL", "SEO Score", "Score Band",
                           "Keyword Count", "Word Count", "HTTPS", "Schema"]
            st.dataframe(benchmark_df[display_cols], use_container_width=True)

            # ── Step 5: AI Executive Summary ────────────────────────────────
            if primary_row and gemini_api_key:
                st.markdown("### 🤖 AI Executive Summary")
                best_comp_name = best_comp.get("Venue Name", "top competitor") if best_comp else "N/A"

                insights = generate_strategic_insights(
                    primary_row=primary_row,
                    benchmark_rows=benchmark_rows,
                    keyword=keyword
                )

                with st.spinner("Generating AI summary..."):
                    ai_summary = generate_ai_executive_summary(
                        gemini_api_key=gemini_api_key,
                        primary_name=primary_row.get("Venue Name", url),
                        keyword=keyword,
                        primary_rank="N/A",
                        primary_score=primary_row.get("SEO Score", 0),
                        top_competitor=best_comp_name,
                        strategic_insights=insights,
                        recommended_fixes=[]
                    )
                if ai_summary:
                    st.markdown(ai_summary)

        except Exception as e:
            st.error(f"❌ Competitor analysis error: {e}")
