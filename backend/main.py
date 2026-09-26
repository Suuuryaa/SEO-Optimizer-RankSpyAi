"""
FastAPI backend — RankSpy AI  (upgraded)

New in this version:
  - Redis result cache (24h TTL) via cache.py
  - Server-side per-IP rate limiting via cache.py (replaces localStorage)
  - Async-parallelised analysis pipeline
  - POST /suggest-meta   — HF BART-powered meta title + description generator
  - POST /schema         — JSON-LD schema markup generator
  - POST /content-brief  — AI content gap brief vs competitors
  - GET  /rate-status    — returns current IP usage count for frontend counter
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor

_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from config import active_keys, GLOBAL_LIMIT
from cache import (
    get_cached, set_cached,
    check_ip_rate_limit, get_ip_usage,
    DAILY_FREE_LIMIT,
)
from rate_limiter import check_and_consume, get_global_uses, get_remaining
from models import (
    AnalyzeRequest, AnalyzeResponse,
    CompetitorsRequest, CompetitorsResponse,
    CompareRequest, CompareResponse,
    LeaderboardRequest, LeaderboardResponse,
    PageSpeedRequest, PageSpeedResponse,
    HealthResponse, SeoSummary,
)

from seo_utils import (
    get_page_soup, get_title, get_meta_description, get_h1_tags,
    get_text_content, count_words, count_keyword, keyword_density,
    get_links, get_images_missing_alt, keyword_in_title, keyword_in_meta,
    keyword_in_h1, title_length, meta_description_length,
    check_technical_seo, analyze_content_quality, has_schema_markup,
)
from scoring import calculate_seo_score, get_score_band
from summary_utils import get_executive_summary, generate_ai_executive_summary
from leaderboard_utils import analyze_venue
from comparison_utils import compare_metric
from pagespeed_utils import get_pagespeed_data
from competitor_utils import get_competitors_via_gemini, filter_direct_competitors
from serp_utils import progressive_competitor_search
from insight_utils import generate_strategic_insights
from geo_utils import (
    check_ai_crawlers, score_citability, check_llmstxt,
    check_eeat, calculate_geo_score,
)
from ai.semantic import semantic_keyword_score
from ai.meta_gen import generate_meta_suggestions
from ai.schema_gen import generate_schema
from ai.content_brief import generate_content_brief
from ai.local_seo import analyze_local_seo
from ai.keyphrase import extract_keyphrases
from deep_crawl import deep_crawl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8)

_is_prod = os.environ.get("ENV", "development").lower() == "production"
app = FastAPI(
    title="RankSpy AI API",
    version="2.0.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

# ── Security headers middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"]         = "1; mode=block"
        return response

# ── Body size limit (1 MB) ────────────────────────────────────────────────────
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    _LIMIT = 1_000_000  # 1 MB

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > self._LIMIT:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware)

_ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://rankspyseo.xyz,https://www.rankspyseo.xyz,http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
async def warmup_hf():
    """Pre-warm HuggingFace models in background — avoids cold-start delay."""
    import threading
    def _warm():
        try:
            from ai.semantic import _embed
            _embed(["warmup"])
            logger.info("HuggingFace MiniLM warmed up")
        except Exception as e:
            logger.warning(f"HF warmup failed: {e}")
    threading.Thread(target=_warm, daemon=True).start()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    """Get real client IP — Cloudflare sets CF-Connecting-IP."""
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        or "unknown"
    )


def _has_own_keys(user_api_keys) -> bool:
    """Only bypass pool if keys look like real API keys (min 20 chars, no whitespace)."""
    if not user_api_keys:
        return False
    sk = user_api_keys.serper_key or ""
    gk = user_api_keys.gemini_key or ""
    import re as _re
    _real = lambda k: len(k) >= 20 and not _re.search(r'\s', k)
    return _real(sk) and _real(gk)


def _gate(user_api_keys) -> dict:
    result = check_and_consume(user_has_own_keys=_has_own_keys(user_api_keys))
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result["message"])
    return result


async def _run(fn, *args):
    """Run a blocking function in the thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _sanitize_input(v: str, max_len: int = 200) -> str:
    """Strip HTML tags and control chars from any user-supplied string before echoing."""
    from html import escape as _escape
    import re as _re
    v = _re.sub(r'[\x00-\x1f\x7f]', '', v)   # control chars
    v = _re.sub(r'<[^>]+>', '', v)             # strip HTML tags
    return _escape(v.strip())[:max_len]


def _full_seo_analysis(url: str, keyword: str, keys: dict) -> dict:
    """Full synchronous SEO pipeline — runs in executor."""
    soup, _ = get_page_soup(url)

    title    = get_title(soup)
    meta     = get_meta_description(soup)
    h1       = get_h1_tags(soup)
    text     = get_text_content(soup)
    wc       = count_words(text)
    kc       = count_keyword(text, keyword)
    kd       = keyword_density(text, keyword)
    internal, external = get_links(soup, url)
    missing  = get_images_missing_alt(soup)
    tkw      = keyword_in_title(title, keyword)
    mkw      = keyword_in_meta(meta, keyword)
    hkw      = keyword_in_h1(h1, keyword)
    tlen     = title_length(title)
    mlen     = meta_description_length(meta)
    tech     = check_technical_seo(url, soup)
    schema   = has_schema_markup(soup)
    cq       = analyze_content_quality(text)

    score, recs = calculate_seo_score(
        title, meta, h1, kc, wc, len(missing),
        tkw, mkw, hkw, tlen, mlen,
        internal_links_count=len(internal),
        external_links_count=len(external),
        has_schema=schema,
        https_enabled=tech.get("https_enabled", False),
        mobile_viewport=tech.get("mobile_viewport", False),
    )

    summary_raw = get_executive_summary(score, kc, len(missing), wc)

    return {
        "url": url, "keyword": _sanitize_input(keyword),
        "title": title, "meta_description": meta,
        "h1_tags": h1, "word_count": wc, "keyword_count": kc,
        "keyword_density": kd, "internal_links": len(internal),
        "external_links": len(external), "missing_alt": len(missing),
        "keyword_in_title": tkw, "keyword_in_meta": mkw, "keyword_in_h1": hkw,
        "title_length": tlen, "meta_length": mlen,
        "seo_score": score, "score_band": get_score_band(score),
        "recommendations": recs, "technical_seo": tech,
        "content_quality": cq,
        "summary": {
            "overall_status":  summary_raw["Overall Status"],
            "top_issue":       summary_raw["Top Issue"],
            "strongest_area":  summary_raw["Strongest Area"],
            "priority_action": summary_raw["Priority Action"],
        },
        "_soup": soup,
        "_text": text,
    }


# ── New request models ─────────────────────────────────────────────────────────

class SuggestMetaRequest(BaseModel):
    url:     str
    keyword: str = ""

    class Config:
        # allow extra so frontend can pass crawlMode etc without breaking
        extra = "ignore"


class SchemaRequest(BaseModel):
    url:     str
    keyword: str = ""

    class Config:
        extra = "ignore"


class ContentBriefRequest(BaseModel):
    url:           str
    keyword:       str
    user_api_keys: Optional[object] = None

    class Config:
        extra = "ignore"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        pool_uses=get_global_uses(),
        pool_limit=GLOBAL_LIMIT,
        remaining=get_remaining(),
    )


@app.get("/rate-status")
def rate_status(request: Request):
    """Return global pool usage — never resets until manually cleared."""
    used = get_global_uses()
    remaining = max(0, GLOBAL_LIMIT - used)
    return {
        "ip_used":      used,
        "ip_remaining": remaining,
        "daily_limit":  GLOBAL_LIMIT,
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    gate = _gate(req.user_api_keys)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    # ── Check result cache first ──────────────────────────────────────────────
    js_mode = req.crawl_mode == "javascript"
    cached = get_cached(req.url, req.keyword)
    if cached and not req.geo and not req.pagespeed and not js_mode:
        logger.info(f"/analyze cache HIT: {req.url}")
        cached["pool_uses"]      = gate["uses"]
        cached["pool_remaining"] = gate["remaining"]
        return cached

    # ── Run analysis pipeline ─────────────────────────────────────────────────
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, keys)
    except Exception as exc:
        logger.error(f"/analyze error for {req.url}: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    # ── Deep Playwright crawl (JS mode) ───────────────────────────────────────
    if js_mode:
        try:
            logger.info(f"/analyze deep crawl: {req.url}")
            crawl_data = await deep_crawl(req.url)
            if "error" not in crawl_data:
                # Enrich with HF keyphrases across all discovered content
                combined = crawl_data.get("combined_text", "")
                if combined:
                    kp = await _run(extract_keyphrases, combined)
                    crawl_data["keyphrases"] = kp
                result["deep_crawl"] = crawl_data
                # Boost word count with JS-rendered text
                if combined:
                    from seo_utils import count_words as _cw
                    result["word_count"] = max(result.get("word_count", 0), _cw(combined))
        except Exception as exc:
            logger.warning(f"/analyze deep crawl error: {exc}")
            result["deep_crawl"] = {"error": str(exc)}

    soup = result.pop("_soup")
    text = result.pop("_text")

    # ── Semantic score (HF MiniLM) — runs parallel to GEO/PageSpeed ──────────
    semantic_task = asyncio.create_task(
        _run(semantic_keyword_score, text, req.keyword)
    )

    # ── GEO analysis ──────────────────────────────────────────────────────────
    if req.geo:
        try:
            crawler_data    = await _run(check_ai_crawlers, req.url)
            citability_data = await _run(score_citability, soup)
            llmstxt_data    = await _run(check_llmstxt, req.url)
            eeat_data       = await _run(check_eeat, soup, req.url)
            has_schema      = result["technical_seo"].get("has_schema", False)
            geo             = calculate_geo_score(
                crawler_score=crawler_data["score"],
                citability_score=citability_data["score"],
                eeat_score=eeat_data["score"],
                llmstxt_exists=llmstxt_data["exists"],
                has_schema=has_schema,
            )
            result["geo_score"] = {**geo, "crawlers": crawler_data,
                                   "citability": citability_data,
                                   "llmstxt": llmstxt_data, "eeat": eeat_data}
        except Exception as exc:
            logger.warning(f"/analyze GEO error: {exc}")
            result["geo_score"] = {"error": str(exc)}

    # ── PageSpeed ─────────────────────────────────────────────────────────────
    if req.pagespeed:
        if not keys["pagespeed"]:
            result["pagespeed"] = {"error": "PAGESPEED_API_KEY not configured."}
        else:
            try:
                result["pagespeed"] = await _run(
                    get_pagespeed_data, req.url, keys["pagespeed"], req.strategy
                )
            except Exception as exc:
                logger.warning(f"/analyze PageSpeed error: {exc}")
                result["pagespeed"] = {"error": str(exc)}

    # ── Await semantic score ──────────────────────────────────────────────────
    try:
        result["semantic"] = await semantic_task
    except Exception as exc:
        logger.warning(f"/analyze semantic error: {exc}")
        result["semantic"] = {"semantic_score": None, "hf_available": False}

    result["pool_uses"]      = gate["uses"]
    result["pool_remaining"] = gate["remaining"]

    # Cache result (no GEO/PageSpeed/deep crawl to keep cache clean)
    if not req.geo and not req.pagespeed and not js_mode:
        set_cached(req.url, req.keyword, result)

    return result


@app.post("/competitors")
async def competitors(req: CompetitorsRequest, request: Request):
    gate = _gate(req.user_api_keys)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    if not keys["serper"]:
        raise HTTPException(status_code=400, detail="SERPER_API_KEY is required.")

    # Primary analysis
    try:
        primary_raw = await _run(_full_seo_analysis, req.url, req.keyword, keys)
    except Exception as exc:
        logger.error(f"/competitors primary error: {exc}")
        raise HTTPException(status_code=502, detail=f"Primary analysis failed: {exc}")

    primary_raw.pop("_soup", None)
    primary_text = primary_raw.pop("_text", "")

    # Competitor discovery
    try:
        _, direct_competitors, search_log, location_msg = await _run(
            progressive_competitor_search,
            req.url, req.keyword, keys["serper"],
            filter_direct_competitors, 3, keys["gemini"] or None,
        )
    except Exception as exc:
        logger.error(f"/competitors discovery error: {exc}")
        raise HTTPException(status_code=502, detail=f"Discovery failed: {exc}")

    # Analyse competitors in parallel
    async def _analyze_comp(comp):
        comp_url = comp.get("Link", comp.get("link", ""))
        if not comp_url:
            return None
        try:
            row = await _run(analyze_venue, comp_url, req.keyword)
            row["Role"]      = "Direct Competitor"
            row["SERP Rank"] = comp.get("SERP Rank", comp.get("Direct Rank", "N/A"))
            return row
        except Exception as exc:
            logger.warning(f"comp error {comp_url}: {exc}")
            return {"Venue Name": comp_url, "URL": comp_url, "SEO Score": 0,
                    "Score Band": "Blocked", "Role": "Direct Competitor", "error": str(exc)}

    comp_tasks = [_analyze_comp(c) for c in direct_competitors[:8]]
    comp_rows  = [r for r in await asyncio.gather(*comp_tasks) if r]

    # Semantic score for primary
    semantic = await _run(semantic_keyword_score, primary_text, req.keyword)
    primary_raw["semantic"] = semantic

    # Content brief
    try:
        brief = await _run(
            generate_content_brief,
            primary_raw, comp_rows, req.keyword, keys["gemini"] or ""
        )
        primary_raw["content_brief"] = brief
    except Exception as exc:
        logger.warning(f"content_brief error: {exc}")
        primary_raw["content_brief"] = None

    # AI summary
    ai_summary = None
    if keys["gemini"] and comp_rows:
        try:
            primary_row = {
                "Venue Name":         primary_raw.get("title", req.url),
                "SERP Rank":          1,
                "SEO Score":          primary_raw["seo_score"],
                "Keyword Count":      primary_raw["keyword_count"],
                "Word Count":         primary_raw["word_count"],
                "Images Missing ALT": primary_raw["missing_alt"],
                "Role":               "Primary Venue",
            }
            all_rows = [primary_row] + comp_rows
            insights = await _run(generate_strategic_insights, primary_row, all_rows, req.keyword)
            best_comp = max(comp_rows, key=lambda r: r.get("SEO Score", 0), default={})
            ai_summary = await _run(
                generate_ai_executive_summary,
                keys["gemini"], primary_row["Venue Name"], req.keyword,
                1, primary_raw["seo_score"],
                best_comp.get("Venue Name", "N/A"), insights, all_rows,
            )
        except Exception as exc:
            logger.warning(f"AI summary error: {exc}")
            ai_summary = f"AI summary unavailable: {exc}"

    return CompetitorsResponse(
        primary=primary_raw, competitors=comp_rows,
        search_log=search_log, location_msg=location_msg,
        ai_summary=ai_summary,
        pool_uses=gate["uses"], pool_remaining=gate["remaining"],
    )


@app.post("/suggest-meta")
async def suggest_meta(req: SuggestMetaRequest, request: Request):
    """
    Generate AI-powered meta title + description suggestions.
    Does NOT consume a rate-limit check — it's a lightweight helper.
    """
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    soup = result.pop("_soup")
    text = result.pop("_text")

    try:
        suggestions = await _run(
            generate_meta_suggestions,
            result["title"],
            result["meta_description"],
            result["h1_tags"],
            text,
            req.keyword,
            req.url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "url":              req.url,
        "keyword":          req.keyword,
        "current_title":    result["title"],
        "current_meta":     result["meta_description"],
        "title_length":     result["title_length"],
        "meta_length":      result["meta_length"],
        **suggestions,
    }


@app.post("/schema")
async def schema_endpoint(req: SchemaRequest, request: Request):
    """Generate JSON-LD schema markup for the given URL."""
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    soup = result.pop("_soup")
    text = result.pop("_text")

    try:
        schema_data = await _run(
            generate_schema,
            req.url,
            result["title"],
            result["meta_description"],
            result["h1_tags"],
            text,
            result["technical_seo"],
            result["word_count"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"url": req.url, **schema_data}


@app.post("/local-seo")
async def local_seo_endpoint(req: SuggestMetaRequest, request: Request):
    """Analyze page for local SEO signals."""
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    soup = result.pop("_soup")
    text = result.pop("_text")

    try:
        local_data = await _run(analyze_local_seo, req.url, soup, text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"url": req.url, "keyword": req.keyword, **local_data}


@app.post("/compare")
async def compare(req: CompareRequest, request: Request):
    gate = _gate(req.user_api_keys)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)
    try:
        r1, r2 = await asyncio.gather(
            _run(analyze_venue, req.url1, req.keyword),
            _run(analyze_venue, req.url2, req.keyword),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    comparison = {
        "SEO Score":          compare_metric(r1["SEO Score"], r2["SEO Score"]),
        "Word Count":         compare_metric(r1["Word Count"], r2["Word Count"]),
        "Keyword Count":      compare_metric(r1["Keyword Count"], r2["Keyword Count"]),
        "Internal Links":     compare_metric(r1["Internal Links"], r2["Internal Links"]),
        "External Links":     compare_metric(r1["External Links"], r2["External Links"]),
        "Images Missing ALT": compare_metric(r1["Images Missing ALT"], r2["Images Missing ALT"],
                                             higher_is_better=False),
    }
    return CompareResponse(site1=r1, site2=r2, comparison=comparison,
                           pool_uses=gate["uses"], pool_remaining=gate["remaining"])


@app.post("/leaderboard")
async def leaderboard(req: LeaderboardRequest, request: Request):
    if len(req.urls) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 URLs.")
    gate = _gate(req.user_api_keys)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    tasks = [_run(analyze_venue, url, req.keyword) for url in req.urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    rows = []
    for url, r in zip(req.urls, results):
        if isinstance(r, Exception):
            rows.append({"Venue Name": url, "URL": url, "SEO Score": 0,
                         "Score Band": "Blocked", "error": str(r)})
        else:
            rows.append(r)

    rows.sort(key=lambda r: r.get("SEO Score", 0), reverse=True)
    return LeaderboardResponse(rows=rows, pool_uses=gate["uses"], pool_remaining=gate["remaining"])


@app.post("/pagespeed")
async def pagespeed(req: PageSpeedRequest, request: Request):
    gate = _gate(req.user_api_keys)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)
    if not keys["pagespeed"]:
        raise HTTPException(status_code=400, detail="PAGESPEED_API_KEY required.")
    try:
        data = await _run(get_pagespeed_data, req.url, keys["pagespeed"], req.strategy)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return PageSpeedResponse(url=req.url, strategy=req.strategy, data=data,
                             pool_uses=gate["uses"], pool_remaining=gate["remaining"])


class TrackRequest(BaseModel):
    url: str
    keyword: str


@app.post("/track")
async def track_keyword(req: TrackRequest, request: Request):
    """Save a URL+keyword for rank tracking, then immediately check its SERP position."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    serper_key   = os.environ.get("SERPER_API_KEY", "")

    from rank_tracker import save_tracking, check_rank, save_rank_result

    try:
        row = await _run(save_tracking, req.url, req.keyword, supabase_url, supabase_key)
    except Exception as exc:
        logger.error(f"/track save_tracking error: {exc}")
        raise HTTPException(status_code=502, detail=f"Failed to save tracking: {exc}")

    rank_result = None
    if serper_key:
        try:
            rank_result = await _run(check_rank, req.url, req.keyword, serper_key)
            await _run(
                save_rank_result,
                row["id"], rank_result["position"], supabase_url, supabase_key,
            )
        except Exception as exc:
            logger.warning(f"/track check_rank error: {exc}")
            rank_result = {"error": str(exc)}

    return {"tracking": row, "rank": rank_result}


@app.get("/rankings")
async def get_rankings(url: str, request: Request):
    """Get all tracked keywords + rank history for a URL."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")

    from rank_tracker import get_tracking_history

    try:
        history = await _run(get_tracking_history, url, supabase_url, supabase_key)
    except Exception as exc:
        logger.error(f"/rankings error: {exc}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch rankings: {exc}")

    return {"url": url, "tracked": history}


class ContactRequest(BaseModel):
    name:    str = Field(min_length=1, max_length=100)
    email:   str = Field(min_length=5, max_length=200)
    message: str = Field(min_length=1, max_length=3000)

# Simple in-process per-IP rate limiter for /contact (no Redis dep needed)
_contact_ips: dict = {}

def _contact_rate_ok(ip: str) -> bool:
    """Allow max 3 submissions per IP per 10 minutes."""
    import time
    now = time.time()
    window = 600  # 10 min
    calls = _contact_ips.get(ip, [])
    calls = [t for t in calls if now - t < window]
    if len(calls) >= 3:
        return False
    calls.append(now)
    _contact_ips[ip] = calls
    return True


@app.post("/contact")
async def contact_form(req: ContactRequest, request: Request):
    """Send contact form email via Gmail SMTP. Credentials from env vars."""
    import re as _re, smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Basic email format check
    if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', req.email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Per-IP rate limit
    ip = _client_ip(request)
    if not _contact_rate_ok(ip):
        raise HTTPException(status_code=429, detail="Too many contact requests. Try again later.")

    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient  = os.environ.get("CONTACT_RECIPIENT", "")

    if not gmail_user or not gmail_pass or not recipient:
        # Silently accept but log — don't expose why it failed to client
        logger.warning(f"Contact form submission from {req.email} (email not configured)")
        return {"ok": True}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"RankSpy Contact: {req.name}"
        msg["From"] = gmail_user
        msg["To"] = recipient

        body = f"""
New contact form submission from RankSpy AI:

Name: {req.name}
Email: {req.email}

Message:
{req.message}
        """.strip()

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, recipient, msg.as_string())

        logger.info(f"Contact email sent from {req.email}")
        return {"ok": True}
    except Exception as exc:
        logger.error(f"Contact email failed: {exc}")
        # Still return ok to not expose email config details
        return {"ok": True}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log internally with full detail, never expose stack trace to client
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
