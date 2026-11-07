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

# backend/ must win over the old Streamlit-era duplicates in the project root
# (seo_utils, competitor_utils, summary_utils, ...). Inserting the root at
# position 0 used to shadow every hardened backend module.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
if _PARENT not in sys.path:
    sys.path.append(_PARENT)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from config import active_keys, GLOBAL_LIMIT, ADMIN_SECRET
from log_sanitizer import configure_logging
configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
from cache import (
    get_cached, set_cached,
    check_ip_rate_limit, get_ip_usage, check_ip_quota,
    DAILY_FREE_LIMIT,
)

# Per-IP daily caps for endpoints outside the global pool. Each helper call
# scrapes the page again (ScraperAPI credits); /track also spends Serper.
HELPER_DAILY_LIMIT = int(os.getenv("HELPER_DAILY_LIMIT", "60"))
TRACK_DAILY_LIMIT  = int(os.getenv("TRACK_DAILY_LIMIT", "10"))


def _quota_gate(request: Request, bucket: str, limit: int) -> None:
    if not check_ip_quota(_client_ip(request), bucket, limit):
        raise HTTPException(status_code=429, detail="Daily limit reached for this feature. Try again tomorrow.")
from rate_limiter import check_and_consume, get_global_uses, get_remaining, refund
from models import (
    AnalyzeRequest, AnalyzeResponse,
    CompetitorsRequest, CompetitorsResponse,
    CompareRequest, CompareResponse,
    LeaderboardRequest, LeaderboardResponse,
    PageSpeedRequest, PageSpeedResponse,
    HealthResponse, SeoSummary,
)

from bs4 import BeautifulSoup
from seo_utils import (
    FetchError, render_page_html, THIN_PAGE_WORDS,
    get_page_soup, get_page_meta, page_cached, get_title, get_meta_description, get_h1_tags,
    get_text_content, count_words, count_keyword, keyword_density,
    get_links, get_images_missing_alt, keyword_in_title, keyword_in_meta,
    keyword_in_h1, title_length, meta_description_length,
    check_technical_seo, analyze_content_quality, has_schema_markup,
    match_keyword, best_h1_match, check_indexability,
)
from scoring import calculate_seo_score, get_score_band, SCORING_VERSION
from summary_utils import get_executive_summary, generate_ai_executive_summary
from leaderboard_utils import analyze_venue, row_error
from location_utils import get_location_from_url, location_for_country, country_is_from_domain
from comparison_utils import compare_metric
from pagespeed_utils import get_pagespeed_data
from google_check import google_seo_check
from competitor_utils import get_competitors_via_gemini, filter_direct_competitors, find_brand_rivals
from serp_utils import progressive_competitor_search
from insight_utils import generate_strategic_insights
from geo_utils import (
    check_ai_crawlers, score_citability, check_llmstxt,
    check_eeat, calculate_geo_score, check_snippet_controls,
)
from ai.meta_gen import generate_meta_suggestions
from ai.schema_gen import generate_schema
from ai.content_brief import generate_content_brief
from ai.local_seo import analyze_local_seo
from ai.keyphrase import extract_keyphrases
from deep_crawl import deep_crawl

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
class SecurityHeadersMiddleware:
    """Plain ASGI (not BaseHTTPMiddleware, whose task group wraps errors raised
    while the body is read, e.g. the 413 below, into an ExceptionGroup)."""
    _HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"x-xss-protection", b"1; mode=block"),
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                names = {h[0] for h in self._HEADERS}
                message["headers"] = [h for h in message.get("headers", []) if h[0].lower() not in names] + self._HEADERS
            await send(message)

        await self.app(scope, receive, send_with_headers)

# ── Body size limit (1 MB) ────────────────────────────────────────────────────
class _BodyTooLarge(HTTPException):
    """Raised from the counting receive(); an HTTPException so FastAPI's body
    parser re-raises it instead of turning it into a 400."""

    def __init__(self):
        super().__init__(status_code=413, detail="Payload too large")


class MaxBodySizeMiddleware:
    """Rejects bodies over 1 MB: by Content-Length up front, and by counting the
    bytes actually received (chunked uploads have no Content-Length)."""
    _LIMIT = 1_000_000  # 1 MB

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cl = dict(scope.get("headers") or []).get(b"content-length")
        if cl is not None:
            try:
                size = int(cl)
                if size < 0:
                    raise ValueError
            except ValueError:
                return await JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})(scope, receive, send)
            if size > self._LIMIT:
                return await JSONResponse(status_code=413, content={"detail": "Payload too large"})(scope, receive, send)

        received = 0
        started = False

        async def counting_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._LIMIT:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            if not started:
                await JSONResponse(status_code=413, content={"detail": "Payload too large"})(scope, receive, send)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware)

_ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://rankspyseo.xyz,https://www.rankspyseo.xyz"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

# Cloudflare IPv4 ranges (update periodically via https://www.cloudflare.com/ips/)
_CF_RANGES = [
    "173.245.48.0/20","103.21.244.0/22","103.22.200.0/22","103.31.4.0/22",
    "141.101.64.0/18","108.162.192.0/18","190.93.240.0/20","188.114.96.0/20",
    "197.234.240.0/22","198.41.128.0/17","162.158.0.0/15","104.16.0.0/13",
    "104.24.0.0/14","172.64.0.0/13","131.0.72.0/22",
]
import ipaddress as _ipaddr
_CF_NETS = [_ipaddr.ip_network(r) for r in _CF_RANGES]

def _is_cloudflare_ip(ip: str) -> bool:
    try:
        addr = _ipaddr.ip_address(ip)
        return any(addr in net for net in _CF_NETS)
    except ValueError:
        return False

# Railway's edge proxy connects from the shared 100.64.0.0/10 range, so the
# socket address is the proxy, not the visitor. Only behind that proxy do we
# trust the forwarding headers it sets.
_RAILWAY_PROXY_NET = _ipaddr.ip_network("100.64.0.0/10")


def _client_ip(request: Request) -> str:
    """Real client IP: Cloudflare header from Cloudflare, Railway forwarding headers from Railway's proxy."""
    real_ip = (request.client.host or "unknown") if request.client else "unknown"
    if _is_cloudflare_ip(real_ip):
        return request.headers.get("CF-Connecting-IP") or real_ip
    try:
        behind_railway = _ipaddr.ip_address(real_ip) in _RAILWAY_PROXY_NET
    except ValueError:
        behind_railway = False
    if behind_railway:
        # Railway's proxy overwrites X-Real-IP; X-Forwarded-For is client-controlled
        # (its first entry can be forged), so it is never trusted.
        fwd = (request.headers.get("X-Real-IP") or "").strip()
        try:
            _ipaddr.ip_address(fwd)
            return fwd
        except ValueError:
            pass
    return real_ip


def _key_works(kind: str, key: str) -> bool:
    """One cheap live call proves a user key is real; the verdict is cached in Redis.

    Format checks alone let anyone skip the free pool with made-up keys.
    """
    import hashlib
    import requests as _rq
    from cache import _redis, _redis_set_ex
    fp = hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:24]
    cached = _redis(f"/get/keyok:{fp}")
    if cached in ("1", "0"):
        return cached == "1"
    try:
        if kind == "serper":
            r = _rq.get("https://google.serper.dev/account", headers={"X-API-KEY": key}, timeout=8)
        else:
            r = _rq.get("https://generativelanguage.googleapis.com/v1beta/models",
                        params={"pageSize": 1}, headers={"x-goog-api-key": key}, timeout=8)
        ok = r.status_code == 200
    except Exception as exc:
        logger.warning(f"key check ({kind}) failed: {exc}")
        return False
    _redis_set_ex(f"keyok:{fp}", "1" if ok else "0", 3600 if ok else 600)
    return ok


def _has_own_keys(user_api_keys) -> bool:
    """Bypass the pool only for keys that match the format AND answer a real API call."""
    if not user_api_keys:
        return False
    import re as _re
    sk = user_api_keys.serper_key or ""
    gk = user_api_keys.gemini_key or ""
    if not (_re.match(r'^[a-f0-9]{40}$', sk) and _re.match(r'^AIzaSy[A-Za-z0-9_-]{33}$', gk)):
        return False
    return _key_works("serper", sk) and _key_works("gemini", gk)


# Own-key users still use the server's scraping proxies, so they get a daily cap too.
OWN_KEY_DAILY_LIMIT = int(os.getenv("OWN_KEY_DAILY_LIMIT", "100"))


def _gate(user_api_keys, request: Request) -> dict:
    own = _has_own_keys(user_api_keys)
    if own and not check_ip_quota(_client_ip(request), "ownkeys", OWN_KEY_DAILY_LIMIT):
        raise HTTPException(status_code=429, detail="Daily limit reached for scans with your own keys. Try again tomorrow.")
    result = check_and_consume(user_has_own_keys=own)
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result["message"])
    result["pooled"] = not own
    return result


def _refund(gate: dict) -> None:
    """Give a pool credit back when the scanned page itself couldn't be read."""
    if gate and gate.get("pooled"):
        refund()


def _google_positions(keyword: str, urls: list[str], serper_key: str, gl: str = "us", hl: str | None = None,
                      with_listings: bool = False):
    """Organic Google position (top ~30) per URL's site for `keyword`.

    Returns {url: position | None (not in top 30)}, or None when the search
    could not be run, so callers can tell "not ranking" from "not measured".
    """
    if not serper_key or not keyword:
        return None
    import requests as _rq
    from urllib.parse import urlparse

    def site(u: str) -> str:
        h = (urlparse(u if "//" in u else "https://" + u).hostname or "").lower()
        return h[4:] if h.startswith("www.") else h

    from rank_tracker import serp_organic_results
    try:
        results = serp_organic_results(keyword, serper_key, gl=gl, hl=hl)
    except Exception as exc:
        logger.warning(f"google position lookup failed: {exc}")
        return None
    hosts = [site(r["link"]) for r in results]
    out, listings = {}, {}
    for u in urls:
        s = site(u)
        i = next((i for i, h in enumerate(hosts, 1) if s and (h == s or h.endswith("." + s))), None)
        out[u] = i
        if i is not None:
            listings[u] = results[i - 1]
    return (out, listings) if with_listings else out


def _analysis_http_error(exc: Exception) -> HTTPException:
    """Tell the user what happened when the page itself was the problem."""
    if isinstance(exc, FetchError):
        err = HTTPException(status_code=422, detail=str(exc))
        err.error_kind = exc.kind
        return err
    err = HTTPException(status_code=502, detail="Analysis failed. Please try again.")
    err.error_kind = "internal"
    return err


async def _run(fn, *args):
    """Run a blocking function in the thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _sanitize_input(v: str, max_len: int = 200) -> str:
    """Strip HTML tags and control chars from a user-supplied string before echoing.

    Not HTML-escaped: React escapes on render, and escaping here showed "&amp;" to users.
    """
    import re as _re
    v = _re.sub(r'[\x00-\x1f\x7f]', '', v)   # control chars
    v = _re.sub(r'<[^>]+>', '', v)             # strip HTML tags
    return v.strip()[:max_len]


def _full_seo_analysis(url: str, keyword: str, keys: dict) -> dict:
    """Full synchronous SEO pipeline — runs in executor."""
    soup, _ = get_page_soup(url)
    meta = get_page_meta(url) or {}
    final_url = meta.get("final_url") or url

    # Thin plain HTML (a JavaScript app shell): analyse the rendered page instead
    rendered_js = False
    raw_words = count_words(get_text_content(soup))
    if raw_words < THIN_PAGE_WORDS:
        html = render_page_html(url)
        if html:
            rendered = BeautifulSoup(html, "lxml")
            if count_words(get_text_content(rendered)) > raw_words:
                soup, rendered_js = rendered, True
                logger.info(f"rendered with JS: {url} ({raw_words} words in plain HTML)")

    title    = get_title(soup)
    meta_d   = get_meta_description(soup)
    h1       = get_h1_tags(soup)
    text     = get_text_content(soup)
    wc       = count_words(text)
    kc       = count_keyword(text, keyword)
    kd       = keyword_density(text, keyword)
    internal, external = get_links(soup, final_url)
    missing  = get_images_missing_alt(soup)
    t_match  = match_keyword(title, keyword)
    m_match  = match_keyword(meta_d, keyword)
    h_match  = best_h1_match(h1, keyword)
    tlen     = title_length(title)
    mlen     = meta_description_length(meta_d)
    tech     = check_technical_seo(final_url, soup)
    schema   = tech.get("has_schema", False)
    cq       = analyze_content_quality(text)

    # A page with no title and almost no text is a block page or an unrendered
    # shell, not the site — report that instead of scoring it (amazon.com scored 20).
    if not title and wc < 30:
        raise FetchError("blocked", "We couldn't read any content on this page. The site may block "
                                    "scanners, or the page may need JS rendering mode.")

    indexability = check_indexability(url, soup, meta)

    score, recs, score_uncapped, stuffing = calculate_seo_score(
        title, meta_d, h1, kc, wc, len(missing),
        t_match, m_match, h_match, tlen, mlen,
        internal_links_count=len(internal),
        external_links_count=len(external),
        has_schema=schema,
        https_enabled=tech.get("https_enabled", False),
        mobile_viewport=tech.get("mobile_viewport", False),
        keyword_density_pct=kd,
        indexability=indexability,
    )

    summary_raw = get_executive_summary(score, kc, len(missing), wc)
    # Same band words as the score card, and the top issue = the top-priority task
    summary_raw["Overall Status"] = f"{get_score_band(score)} SEO performance"
    _rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    _top = sorted(recs, key=lambda r: _rank.get(''.join(c for c in str(r.get("priority", "")).upper() if c.isalpha()), 9))
    if _top:
        summary_raw["Top Issue"] = _top[0].get("issue", summary_raw["Top Issue"])
        summary_raw["Priority Action"] = _top[0].get("fix", summary_raw["Priority Action"])

    return {
        "url": url, "keyword": _sanitize_input(keyword),
        "final_url": final_url, "http_status": meta.get("http_status"),
        "scoring_version": SCORING_VERSION,
        "title": title, "meta_description": meta_d,
        "has_title": bool(title), "has_meta_description": bool(meta_d),
        "h1_tags": h1, "word_count": wc, "keyword_count": kc,
        "keyword_density": kd, "keyword_stuffing": stuffing,
        "keyword_match": {"title": t_match, "h1": h_match, "meta": m_match},
        "internal_links": len(internal),
        "external_links": len(external), "missing_alt": len(missing),
        "keyword_in_title": t_match is not None, "keyword_in_meta": m_match is not None,
        "keyword_in_h1": h_match is not None,
        "title_length": tlen, "meta_length": mlen,
        "seo_score": score, "seo_score_uncapped": score_uncapped,
        "score_band": get_score_band(score),
        "indexability": indexability,
        "recommendations": recs, "technical_seo": tech,
        "content_quality": cq,
        "rendered_js": rendered_js,
        "summary": {
            "overall_status":  summary_raw["Overall Status"],
            "top_issue":       summary_raw["Top Issue"],
            "strongest_area":  summary_raw["Strongest Area"],
            "priority_action": summary_raw["Priority Action"],
        },
        "_soup": soup,
        "_text": text,
        "_x_robots_tag": meta.get("x_robots_tag"),
    }


# ── New request models ─────────────────────────────────────────────────────────

class _UrlModel(BaseModel):
    @field_validator("url", check_fields=False)
    @classmethod
    def _check_url(cls, v: str) -> str:
        from models import _validate_url
        return _validate_url(v)


class SuggestMetaRequest(_UrlModel):
    url:     str
    keyword: str = Field(default="", max_length=200)

    class Config:
        # allow extra so frontend can pass crawlMode etc without breaking
        extra = "ignore"


class SchemaRequest(_UrlModel):
    url:     str
    keyword: str = Field(default="", max_length=200)

    class Config:
        extra = "ignore"


class ContentBriefRequest(BaseModel):
    url:           str
    keyword:       str
    user_api_keys: Optional[object] = None

    class Config:
        extra = "ignore"


# ── Background scan jobs ──────────────────────────────────────────────────────
# A scan can take 20-60 s, and Railway's proxy cuts any single request at 60 s.
# POST /jobs/... returns a job id at once; the scan runs as a task that records
# its current step; the page polls GET /jobs/{id}. Jobs live in this process
# (one replica) and are forgotten 10 minutes after they finish.
import contextvars
import time as _time
import uuid

_JOBS: dict[str, dict] = {}
_JOB_TTL = 10 * 60
_JOB_TIMEOUT = 200            # seconds a scan may run before it is stopped
_JOBS_PER_IP = 2              # queued + running per visitor
_JOBS_UNFINISHED_MAX = 30     # queued + running in total
_JOBS_STORED_MAX = 100        # kept in memory, finished ones included
_JOB_TASKS: set = set()       # strong refs so running tasks aren't garbage-collected
_JOB_SLOTS = asyncio.Semaphore(int(os.getenv("MAX_PARALLEL_SCANS", "3")))
_current_job: contextvars.ContextVar = contextvars.ContextVar("current_job", default=None)

_STATUS_KINDS = {429: "rate_limited", 503: "busy", 422: "invalid_input", 504: "timeout"}


def _step(label: str) -> None:
    """Record progress on the running job (no-op for the plain sync endpoints)."""
    job = _current_job.get()
    if job is not None:
        job["step"] = label
        job["steps"].append(label)


def _purge_jobs() -> None:
    now = _time.time()
    for jid in [j for j, v in _JOBS.items() if v.get("finished") and now - v["finished"] > _JOB_TTL]:
        _JOBS.pop(jid, None)
    # Over the stored cap: drop the oldest finished jobs first
    if len(_JOBS) >= _JOBS_STORED_MAX:
        finished = sorted((v["finished"], j) for j, v in _JOBS.items() if v.get("finished"))
        for _, jid in finished[: len(_JOBS) - _JOBS_STORED_MAX + 1]:
            _JOBS.pop(jid, None)


async def _run_job(job: dict, make_coro) -> None:
    _current_job.set(job)
    async with _JOB_SLOTS:
        job["status"] = "running"
        try:
            result = await asyncio.wait_for(make_coro(), timeout=_JOB_TIMEOUT)
            job["result"] = result.model_dump() if hasattr(result, "model_dump") else result
            job["status"] = "done"
        except asyncio.TimeoutError:
            job.update(status="error", error="The scan took too long and was stopped. Please try again.",
                       status_code=504, error_kind="timeout")
        except FetchError as exc:
            job.update(status="error", error=str(exc), status_code=422, error_kind=exc.kind)
        except HTTPException as exc:
            kind = getattr(exc, "error_kind", None) or _STATUS_KINDS.get(exc.status_code, "internal")
            job.update(status="error", error=str(exc.detail), status_code=exc.status_code, error_kind=kind)
        except Exception as exc:
            logger.error(f"job {job['id']} failed: {exc}", exc_info=True)
            job.update(status="error", error="Scan failed. Please try again.", status_code=500,
                       error_kind="internal")
        finally:
            job["finished"] = _time.time()


def _job_ip_bucket(ip: str) -> str:
    """One visitor = one IPv4 address or one IPv6 /64 (a single host usually owns a whole /64)."""
    try:
        addr = _ipaddr.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        return str(_ipaddr.ip_network(f"{addr}/64", strict=False))
    return str(addr)


def _start_job(kind: str, make_coro, ip: str = "unknown") -> dict:
    _purge_jobs()
    ip = _job_ip_bucket(ip)
    unfinished = [j for j in _JOBS.values() if j["status"] in ("queued", "running")]
    if sum(1 for j in unfinished if j.get("ip") == ip) >= _JOBS_PER_IP:
        raise HTTPException(status_code=429, detail="You already have 2 scans running. Wait for one to finish.")
    if len(unfinished) >= _JOBS_UNFINISHED_MAX or len(_JOBS) >= _JOBS_STORED_MAX:
        raise HTTPException(status_code=503, detail="The server is busy. Please try again in a minute.")
    jid = uuid.uuid4().hex
    job = {"id": jid, "kind": kind, "status": "queued", "step": "Waiting to start", "steps": [],
           "created": _time.time(), "finished": None, "ip": ip}
    _JOBS[jid] = job
    task = asyncio.create_task(_run_job(job, make_coro))
    _JOB_TASKS.add(task)
    task.add_done_callback(_JOB_TASKS.discard)
    return {"job_id": jid, "status": "queued"}


async def _helper_gate(url: str, request: Request):
    """Meta/schema/local-SEO panels: per-IP helper quota always. When the page is
    still in the 15-minute page cache (normally from the scan just run) that's
    all; otherwise the fetch costs one pool credit like a scan."""
    await _run(_quota_gate, request, "helpers", HELPER_DAILY_LIMIT)
    if page_cached(url):
        return None
    return await _run(_gate, None, request)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        pool_uses=get_global_uses(),
        pool_limit=GLOBAL_LIMIT,
        remaining=get_remaining(),
    )


@app.post("/admin/reset-pool")
def admin_reset_pool(x_admin_key: Optional[str] = Header(None)):
    """Reset the global usage pool. Called by daily GitHub Actions cron."""
    import hmac
    if not ADMIN_SECRET or not x_admin_key or not hmac.compare_digest(x_admin_key.encode(), ADMIN_SECRET.encode()):
        raise HTTPException(status_code=403, detail="Forbidden")
    from rate_limiter import _redis_set
    _redis_set("global:uses", "0")
    logger.info("admin: global usage pool reset")
    return {"reset": True, "pool_uses": 0, "pool_limit": GLOBAL_LIMIT}


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


async def analyze(req: AnalyzeRequest, request: Request):
    js_mode = req.crawl_mode == "javascript"

    # ── Result cache first: a hit costs no pool credit ───────────────────────
    # fresh=true skips the cache (and is charged); GEO/PageSpeed/JS scans are never cached.
    cacheable = not (req.fresh or req.geo or req.pagespeed or js_mode)
    if cacheable:
        cached = await _run(get_cached, req.url, req.keyword)
        if cached:
            logger.info(f"/analyze cache HIT: {req.url}")
            uses = await _run(get_global_uses)
            cached["cached"]         = True
            cached["pool_uses"]      = uses
            cached["pool_remaining"] = max(0, GLOBAL_LIMIT - uses)
            return cached

    gate = await _run(_gate, req.user_api_keys, request)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    # ── Run analysis pipeline ─────────────────────────────────────────────────
    _step("Fetching and reading the page")
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, keys)
    except Exception as exc:
        logger.error(f"/analyze error for {req.url}: {exc}")
        if isinstance(exc, FetchError):
            await _run(_refund, gate)
        raise _analysis_http_error(exc)

    # ── Deep Playwright crawl (JS mode) ───────────────────────────────────────
    if js_mode:
        _step("Crawling sub-pages with a browser")
        try:
            logger.info(f"/analyze deep crawl: {req.url}")
            crawl_data = await deep_crawl(req.url)
            combined = crawl_data.pop("_combined_text", "")
            if "error" not in crawl_data:
                # Keyphrases across all discovered content; the text itself is never returned
                if combined:
                    crawl_data["keyphrases"] = await _run(extract_keyphrases, combined)
                result["deep_crawl"] = crawl_data
            else:
                result["deep_crawl"] = {"error": crawl_data["error"]}
        except Exception as exc:
            logger.warning(f"/analyze deep crawl error: {exc}")
            result["deep_crawl"] = {"error": "Deep crawl failed"}

    soup = result.pop("_soup")
    result.pop("_text")

    # ── GEO analysis ──────────────────────────────────────────────────────────
    if req.geo:
        _step("Checking AI visibility (GEO)")
        try:
            crawler_data    = await _run(check_ai_crawlers, result.get("final_url") or req.url)
            citability_data = await _run(score_citability, soup)
            llmstxt_data    = await _run(check_llmstxt, req.url)
            eeat_data       = await _run(check_eeat, soup, result.get("final_url") or req.url)
            snippet         = await _run(check_snippet_controls, soup, result.pop("_x_robots_tag", None))
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
                                   "llmstxt": llmstxt_data, "eeat": eeat_data,
                                   "snippet_controls": snippet["snippet_controls"],
                                   "recommendations": snippet["recommendations"]}
        except Exception as exc:
            logger.warning(f"/analyze GEO error: {exc}")
            result["geo_score"] = {"error": "GEO analysis failed"}
    result.pop("_x_robots_tag", None)

    # ── PageSpeed ─────────────────────────────────────────────────────────────
    if req.pagespeed:
        _step("Running Google PageSpeed")
        if not keys["pagespeed"]:
            result["pagespeed"] = {"error": "PageSpeed isn't available right now."}
        else:
            try:
                result["pagespeed"] = await _run(
                    get_pagespeed_data, req.url, keys["pagespeed"], req.strategy
                )
            except Exception as exc:
                logger.warning(f"/analyze PageSpeed error: {exc}")
                result["pagespeed"] = {"error": "PageSpeed analysis failed"}

    result["pool_uses"]      = gate["uses"]
    result["pool_remaining"] = gate["remaining"]
    result["cached"]         = False
    result["cached_at"]      = None

    # Cache plain scans only (fresh scans refresh the cached copy)
    if not req.geo and not req.pagespeed and not js_mode:
        await _run(set_cached, req.url, req.keyword, result)

    return result


def _domain_of(url: str) -> str:
    from urllib.parse import urlparse
    h = (urlparse(url).hostname or url).lower()
    return h[4:] if h.startswith("www.") else h


async def competitors(req: CompetitorsRequest, request: Request):
    gate = await _run(_gate, req.user_api_keys, request)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    if not keys["serper"]:
        raise HTTPException(status_code=400, detail="SERPER_API_KEY is required.")

    location = get_location_from_url(req.url)
    gl, hl = location["serper_gl"], location.get("serper_hl")

    # Primary analysis
    _step("Analysing your page")
    try:
        primary_raw = await _run(_full_seo_analysis, req.url, req.keyword, keys)
    except Exception as exc:
        logger.error(f"/competitors primary error: {exc}")
        if isinstance(exc, FetchError):
            await _run(_refund, gate)
        raise _analysis_http_error(exc)

    primary_raw.pop("_soup", None)
    primary_raw.pop("_x_robots_tag", None)
    primary_text = primary_raw.pop("_text", "")

    # Competitor discovery: first the business's own main rivals (Gemini names them,
    # we keep only sites that respond); search-based discovery only as a fallback.
    _step("Finding your competitors")
    rivals, home = [], None
    if keys["gemini"]:
        try:
            rivals, home = await _run(find_brand_rivals, req.url, keys["gemini"],
                                      primary_raw.get("title") or "", primary_raw.get("meta_description") or "")
        except Exception as exc:
            logger.warning(f"/competitors brand rivals failed: {exc}")
    # .com/.net etc. say nothing about the market: use the business's home country
    if home and not country_is_from_domain(req.url):
        loc = location_for_country(home)
        if loc:
            location = loc
            gl, hl = location["serper_gl"], location.get("serper_hl")
    try:
        if len(rivals) >= 3:
            direct_competitors = [{"Link": r["link"], "Title": r["name"], "Domain": r["domain"],
                                   "SERP Rank": "N/A"} for r in rivals]
            search_log = [f"🤖 Main competitors of {_domain_of(req.url)}: "
                          + ", ".join(r["name"] for r in rivals)]
            location_msg = f"🤖 Main competitors in {location['country_name']}"
        else:
            _, direct_competitors, search_log, location_msg = await _run(
                progressive_competitor_search,
                req.url, req.keyword, keys["serper"],
                filter_direct_competitors, 3, keys["gemini"] or None,
            )
    except Exception as exc:
        logger.error(f"/competitors discovery error: {exc}")
        raise HTTPException(status_code=502, detail="Competitor discovery failed. Please try again.")

    # Analyse competitors in parallel
    async def _analyze_comp(comp):
        comp_url = comp.get("Link", comp.get("link", ""))
        if not comp_url:
            return None
        try:
            row = await _run(analyze_venue, comp_url, req.keyword, True)
        except Exception as exc:
            logger.warning(f"comp error {comp_url}: {exc}")   # logged, never sent to the client
            message, kind = row_error(exc)
            row = {"Venue Name": comp_url, "URL": comp_url, "SEO Score": 0,
                   "Score Band": "Blocked", "error": message, "error_kind": kind}
        row["Role"]      = "Direct Competitor"
        row["SERP Rank"] = comp.get("SERP Rank", comp.get("Direct Rank", "N/A"))
        return row

    _step(f"Analysing {min(len(direct_competitors), 8)} competitor sites")
    comp_tasks = [_analyze_comp(c) for c in direct_competitors[:8]]
    comp_rows  = [r for r in await asyncio.gather(*comp_tasks) if r]

    # Content brief
    _step("Building the content brief")
    try:
        brief = await _run(
            generate_content_brief,
            {**primary_raw, "_text": primary_text}, comp_rows, req.keyword, keys["gemini"] or ""
        )
        primary_raw["content_brief"] = brief
    except Exception as exc:
        logger.warning(f"content_brief error: {exc}")
        primary_raw["content_brief"] = None

    # Page text was only needed for the content brief — never send it to clients
    for r in comp_rows:
        r.pop("_text", None)

    # Real Google positions for the site and each competitor (Serper, searched in the site's country).
    _step("Checking real Google positions")
    got = await _run(_google_positions, req.keyword, [req.url] + [r.get("URL", "") for r in comp_rows],
                     keys["serper"], gl, hl, True)
    positions, listings = got if got is not None else (None, {})
    def _pos(u):
        return "unknown" if positions is None else positions.get(u)
    primary_rank = _pos(req.url)
    primary_raw["google_position"] = primary_rank
    for r in comp_rows:
        r["SERP Rank"] = _pos(r.get("URL", ""))

    # Sites that block our scanner: use Google's own data instead — the page's
    # Google listing (title/snippet) and Google's Lighthouse SEO check of the page
    # that ranks (or the homepage). We never try to get past a site's bot protection.
    blocked_rows = [r for r in comp_rows if r.get("error")]
    if blocked_rows:
        _step("Getting Google's data for sites that block scanners")
        pagespeed_key = keys.get("pagespeed") or ""

        async def _google_data(r):
            u = r.get("URL", "")
            lst = (listings or {}).get(u)
            if lst:
                r["google_listing"] = {
                    "link": lst.get("link", ""), "title": lst.get("title", ""), "snippet": lst.get("snippet", ""),
                    "keyword_in_title": match_keyword(lst.get("title", ""), req.keyword),
                }
            target = (lst or {}).get("link") or u
            check = await _run(google_seo_check, target, pagespeed_key) if pagespeed_key else None
            if check:
                r["google_check"] = check

        await asyncio.gather(*[_google_data(r) for r in blocked_rows])

    # AI summary
    ai_summary = None
    ai_summary_error = None
    if keys["gemini"] and comp_rows:
        _step("Writing the AI strategy report")
        try:
            primary_row = {
                "Venue Name":         primary_raw.get("title") or req.url,
                "SERP Rank":          primary_rank,
                "SEO Score":          primary_raw["seo_score"],
                "Keyword Count":      primary_raw["keyword_count"],
                "Word Count":         primary_raw["word_count"],
                "Images Missing ALT": primary_raw["missing_alt"],
                "Role":               "Primary Venue",
            }
            all_rows = [primary_row] + comp_rows
            insights = await _run(generate_strategic_insights, primary_row, all_rows, req.keyword)
            best_comp = max((r for r in comp_rows if not r.get("error")),
                            key=lambda r: r.get("SEO Score", 0), default={})
            ai_summary = await _run(
                generate_ai_executive_summary,
                keys["gemini"], primary_row["Venue Name"], req.keyword,
                primary_rank, primary_raw["seo_score"],
                best_comp.get("Venue Name", "N/A"), insights, all_rows,
            )
        except Exception as exc:
            logger.warning(f"AI summary error: {exc}")
            ai_summary = None
        if not ai_summary:
            ai_summary, ai_summary_error = None, "unavailable"

    return CompetitorsResponse(
        primary=primary_raw, competitors=comp_rows,
        search_log=search_log, location_msg=location_msg,
        search_location={"gl": gl, "hl": hl, "label": location["location_string"]},
        ai_summary=ai_summary, ai_summary_error=ai_summary_error,
        pool_uses=int(gate["uses"]), pool_remaining=int(gate["remaining"]),
    )


@app.post("/jobs/analyze", status_code=202)
async def analyze_job(req: AnalyzeRequest, request: Request):
    """Start an analysis in the background; poll GET /jobs/{job_id}."""
    return _start_job("analyze", lambda: analyze(req, request), _client_ip(request))


@app.post("/jobs/competitors", status_code=202)
async def competitors_job(req: CompetitorsRequest, request: Request):
    """Start a competitor search in the background; poll GET /jobs/{job_id}."""
    return _start_job("competitors", lambda: competitors(req, request), _client_ip(request))


@app.get("/jobs/{job_id}")
async def job_status(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="This scan is no longer available. Please run it again.")
    out = {k: job[k] for k in ("id", "kind", "status", "step", "steps")}
    out["elapsed"] = round((job["finished"] or _time.time()) - job["created"], 1)
    if job["status"] == "done":
        out["result"] = job["result"]
    elif job["status"] == "error":
        out["error"] = job.get("error")
        out["status_code"] = job.get("status_code")
        out["error_kind"] = job.get("error_kind", "internal")
    return out


@app.post("/suggest-meta")
async def suggest_meta(req: SuggestMetaRequest, request: Request):
    """
    Generate AI-powered meta title + description suggestions.
    Does not draw from the global pool, but is capped per IP per day.
    """
    gate = await _helper_gate(req.url, request)
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        if isinstance(exc, FetchError):
            await _run(_refund, gate)
        raise _analysis_http_error(exc)

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
        raise HTTPException(status_code=500, detail="Meta suggestion generation failed.")

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
    gate = await _helper_gate(req.url, request)
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        if isinstance(exc, FetchError):
            await _run(_refund, gate)
        raise _analysis_http_error(exc)

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
        raise HTTPException(status_code=500, detail="Schema generation failed.")

    return {"url": req.url, **schema_data}


@app.post("/local-seo")
async def local_seo_endpoint(req: SuggestMetaRequest, request: Request):
    """Analyze page for local SEO signals."""
    gate = await _helper_gate(req.url, request)
    try:
        result = await _run(_full_seo_analysis, req.url, req.keyword, {})
    except Exception as exc:
        if isinstance(exc, FetchError):
            await _run(_refund, gate)
        raise _analysis_http_error(exc)

    soup = result.pop("_soup")
    text = result.pop("_text")

    try:
        local_data = await _run(analyze_local_seo, req.url, soup, text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Local SEO analysis failed.")

    return {"url": req.url, "keyword": req.keyword, **local_data}


async def compare(req: CompareRequest, request: Request):
    gate = await _run(_gate, req.user_api_keys, request)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)
    try:
        r1, r2 = await asyncio.gather(
            _run(analyze_venue, req.url1, req.keyword),
            _run(analyze_venue, req.url2, req.keyword),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Comparison failed. Please try again.")

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


async def leaderboard(req: LeaderboardRequest, request: Request):
    if len(req.urls) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 URLs.")
    gate = await _run(_gate, req.user_api_keys, request)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)

    tasks = [_run(analyze_venue, url, req.keyword) for url in req.urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    rows = []
    for url, r in zip(req.urls, results):
        if isinstance(r, Exception):
            logger.warning(f"/leaderboard row error {url}: {r}")
            message, kind = row_error(r)
            rows.append({"Venue Name": url, "URL": url, "SEO Score": 0,
                         "Score Band": "Blocked", "error": message, "error_kind": kind})
        else:
            rows.append(r)

    rows.sort(key=lambda r: r.get("SEO Score", 0), reverse=True)
    return LeaderboardResponse(rows=rows, pool_uses=gate["uses"], pool_remaining=gate["remaining"])


async def pagespeed(req: PageSpeedRequest, request: Request):
    gate = await _run(_gate, req.user_api_keys, request)
    keys = active_keys(req.user_api_keys.model_dump() if req.user_api_keys else None)
    if not keys["pagespeed"]:
        raise HTTPException(status_code=400, detail="PAGESPEED_API_KEY required.")
    try:
        data = await _run(get_pagespeed_data, req.url, keys["pagespeed"], req.strategy)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="PageSpeed analysis failed. Please try again.")
    return PageSpeedResponse(url=req.url, strategy=req.strategy, data=data,
                             pool_uses=gate["uses"], pool_remaining=gate["remaining"])


class TrackRequest(_UrlModel):
    url: str
    keyword: str = Field(min_length=1, max_length=200)


@app.post("/track")
async def track_keyword(req: TrackRequest, request: Request):
    """Save a URL+keyword for rank tracking, then immediately check its SERP position."""
    await _run(_quota_gate, request, "track", TRACK_DAILY_LIMIT)
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    serper_key   = os.environ.get("SERPER_API_KEY", "")

    from rank_tracker import save_tracking, check_rank, save_rank_result

    try:
        row = await _run(save_tracking, req.url, req.keyword, supabase_url, supabase_key)
    except Exception as exc:
        logger.error(f"/track save_tracking error: {exc}")
        raise HTTPException(status_code=502, detail="Failed to save tracking. Please try again.")

    rank_result = None
    if serper_key:
        try:
            loc = get_location_from_url(req.url)
            rank_result = await _run(check_rank, req.url, req.keyword, serper_key,
                                     loc["serper_gl"], loc.get("serper_hl"))
            await _run(
                save_rank_result,
                row["id"], rank_result["position"], supabase_url, supabase_key,
            )
        except Exception as exc:
            logger.warning(f"/track check_rank error: {exc}")
            rank_result = {"error": "Rank check failed"}

    return {"tracking": row, "rank": rank_result}


@app.get("/rankings")
async def get_rankings(url: str, request: Request):
    """Get all tracked keywords + rank history for a URL."""
    await _run(_quota_gate, request, "rankings", 60)
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")

    from rank_tracker import get_tracking_history

    try:
        history = await _run(get_tracking_history, url, supabase_url, supabase_key)
    except Exception as exc:
        logger.error(f"/rankings error: {exc}")
        raise HTTPException(status_code=502, detail="Failed to fetch rankings. Please try again.")

    return {"url": url, "tracked": history}


class ContactRequest(BaseModel):
    name:    str = Field(min_length=1, max_length=100)
    email:   str = Field(min_length=5, max_length=200)
    message: str = Field(min_length=1, max_length=3000)

def _contact_rate_ok(ip: str) -> bool:
    """Allow max 3 contact submissions per IP per 10 minutes, backed by Redis."""
    import time
    from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
    import requests as _req

    window = 600  # 10 minutes
    key = f"contact_rate:{ip}"

    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        # No Redis — fall back to allow (don't block legitimate users)
        return True

    headers = {"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"}
    try:
        # Increment and set TTL atomically
        resp = _req.get(
            f"{UPSTASH_REDIS_REST_URL}/incr/{key}",
            headers=headers, timeout=5,
        )
        count = int(resp.json().get("result", 1))
        if count == 1:
            # First hit — set expiry
            _req.get(
                f"{UPSTASH_REDIS_REST_URL}/expire/{key}/{window}",
                headers=headers, timeout=5,
            )
        return count <= 3
    except Exception as exc:
        logger.warning(f"_contact_rate_ok Redis error: {exc}")
        return True  # Fail open for contact (non-critical path)


@app.post("/contact")
async def contact_form(req: ContactRequest, request: Request):
    """Send contact form email via Gmail SMTP. Credentials from env vars."""
    import re as _re, smtplib, threading
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Basic email format check
    if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', req.email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Per-IP rate limit
    ip = _client_ip(request)
    if not await _run(_contact_rate_ok, ip):
        raise HTTPException(status_code=429, detail="Too many contact requests. Try again later.")

    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient  = os.environ.get("CONTACT_RECIPIENT", "")

    if not gmail_user or not gmail_pass or not recipient:
        logger.warning(f"Contact form submission from {req.email} (email not configured)")
        return {"ok": True}

    _safe_name = req.name.replace('\r', '').replace('\n', '')
    _safe_email = req.email.replace('\r', '').replace('\n', '')
    _safe_msg = req.message.replace('\r\n', '\n').replace('\r', '\n')
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"RankSpy Contact: {_safe_name}"
    msg["From"] = gmail_user
    msg["To"] = recipient
    body = f"""New contact form submission from RankSpy AI:

Name: {_safe_name}
Email: {_safe_email}

Message:
{_safe_msg}""".strip()
    msg.attach(MIMEText(body, "plain"))
    raw = msg.as_string()

    def _send():
        try:
            import requests as _req
            resend_key = os.environ.get("RESEND_API_KEY", "")
            if resend_key:
                resp = _req.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                    json={"from": "RankSpy AI <contact@rankspyseo.xyz>", "to": [recipient],
                          "subject": f"RankSpy Contact: {_safe_name}",
                          "text": body},
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    logger.info(f"Contact email sent via Resend from {req.email}")
                else:
                    logger.error(f"Resend failed: {resp.status_code} {resp.text}")
            else:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(gmail_user, gmail_pass)
                    server.sendmail(gmail_user, recipient, raw)
                logger.info(f"Contact email sent via SMTP from {req.email}")
        except Exception as exc:
            logger.error(f"Contact email failed: {exc}")

    threading.Thread(target=_send, daemon=True).start()
    return {"ok": True}


# ── Legacy synchronous scan routes ────────────────────────────────────────────
# The site uses the /jobs/* endpoints. These long-running sync routes are off
# unless ENABLE_LEGACY_ENDPOINTS=1; analyze() and competitors() stay as plain
# functions the jobs call.
if os.getenv("ENABLE_LEGACY_ENDPOINTS", "") == "1":
    app.post("/analyze")(analyze)
    app.post("/competitors")(competitors)
    app.post("/compare")(compare)
    app.post("/leaderboard")(leaderboard)
    app.post("/pagespeed")(pagespeed)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log internally with full detail, never expose stack trace to client
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
