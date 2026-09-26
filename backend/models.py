"""
Pydantic request/response models for the SEO Dashboard API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator

import ipaddress as _ipaddress
import re as _re_mod
import socket as _socket
from urllib.parse import urlparse as _urlparse_shared

# Blocked cloud metadata and internal hostnames
_BLOCKED_HOSTS = frozenset({
    "169.254.169.254", "metadata.google.internal", "metadata.internal",
    "localhost", "0.0.0.0",
})

def _is_private_ip(host: str) -> bool:
    try:
        addr = _ipaddress.ip_address(host)
        return (addr.is_private or addr.is_loopback or
                addr.is_link_local or addr.is_reserved or addr.is_unspecified)
    except ValueError:
        return False

def _validate_url(v: str) -> str:
    """Shared hardened URL validator used by all request models."""
    # Strip control characters
    v = _re_mod.sub(r'[\x00-\x1f\x7f]', '', v).strip()
    if not v.startswith(("http://", "https://")):
        if _re_mod.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*:', v):
            raise ValueError("URL scheme must be http or https")
        v = "https://" + v
    parsed = _urlparse_shared(v)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL scheme must be http or https")
    if not parsed.netloc or "." not in parsed.netloc:
        raise ValueError("Invalid domain in URL")
    if _re_mod.search(r'[\x00-\x1f]', parsed.netloc + parsed.path):
        raise ValueError("URL contains invalid characters")
    host = parsed.hostname or ""
    # Block raw private IPs
    if _is_private_ip(host):
        raise ValueError("Private/internal IP addresses are not allowed")
    # Block known metadata endpoints by hostname
    if host.lower() in _BLOCKED_HOSTS:
        raise ValueError("Blocked host")
    # DNS pre-resolution to catch SSRF via public-looking hostnames
    try:
        resolved = _socket.gethostbyname(host)
        if _is_private_ip(resolved):
            raise ValueError("URL resolves to a private IP address")
    except OSError:
        pass  # DNS failure — let downstream handle it
    return v


# ── Shared sub-models ─────────────────────────────────────────────────────────

class UserApiKeys(BaseModel):
    """Optional per-request API key overrides."""
    serper_key:      Optional[str] = None
    gemini_key:      Optional[str] = None
    pagespeed_key:   Optional[str] = None
    scraper_api_key: Optional[str] = None
    zenrows_api_key: Optional[str] = None


class Recommendation(BaseModel):
    priority: str
    issue:    str
    fix:      str
    impact:   str


class TechnicalSeo(BaseModel):
    https_enabled:      Optional[bool] = None
    robots_meta:        Optional[str]  = None
    robots_noindex:     Optional[bool] = None
    robots_nofollow:    Optional[bool] = None
    canonical_url:      Optional[str]  = None
    has_canonical:      Optional[bool] = None
    mobile_viewport:    Optional[bool] = None
    viewport_content:   Optional[str]  = None
    lang_attribute:     Optional[str]  = None
    has_lang:           Optional[bool] = None
    og_tags_count:      Optional[int]  = None
    has_og_title:       Optional[bool] = None
    has_og_description: Optional[bool] = None
    has_og_image:       Optional[bool] = None
    twitter_card_count: Optional[int]  = None
    has_twitter_card:   Optional[bool] = None
    has_schema:         Optional[bool] = None
    schema_types:       Optional[Dict[str, Any]] = None
    h1_count:           Optional[int]  = None
    h2_count:           Optional[int]  = None
    h3_count:           Optional[int]  = None
    proper_h1_usage:    Optional[bool] = None
    has_heading_hierarchy: Optional[bool] = None


class ContentQuality(BaseModel):
    flesch_reading_ease:  Optional[float] = None
    flesch_kincaid_grade: Optional[float] = None
    readability_rating:   Optional[str]   = None
    avg_sentence_length:  Optional[float] = None
    unique_words_ratio:   Optional[float] = None


class GeoBreakdownItem(BaseModel):
    score:    int
    weight:   float
    weighted: float


class GeoScore(BaseModel):
    score:     int
    band:      str
    breakdown: Dict[str, GeoBreakdownItem] = {}


class PageSpeedData(BaseModel):
    performance_score:       Optional[float] = None
    accessibility_score:     Optional[float] = None
    best_practices_score:    Optional[float] = None
    seo_score:               Optional[float] = None
    first_contentful_paint:  Optional[str]   = None
    largest_contentful_paint: Optional[str]  = None
    speed_index:             Optional[str]   = None
    total_blocking_time:     Optional[str]   = None
    cumulative_layout_shift: Optional[str]   = None


class SeoSummary(BaseModel):
    overall_status:  str
    top_issue:       str
    strongest_area:  str
    priority_action: str


# ── /health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str = "ok"
    pool_uses: int
    pool_limit: int
    remaining: int


# ── /analyze ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url:           str
    keyword:       str = Field(default="", max_length=200)
    pagespeed:     bool = False
    geo:           bool = False
    strategy:      str  = "mobile"   # pagespeed strategy: mobile | desktop
    crawl_mode:    str  = "standard" # standard | javascript
    user_api_keys: Optional[UserApiKeys] = None

    @field_validator("url")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        return _validate_url(v)


class AnalyzeResponse(BaseModel):
    url:              str
    keyword:          str
    title:            str
    meta_description: str
    h1_tags:          List[str]
    word_count:       int
    keyword_count:    int
    keyword_density:  float
    internal_links:   int
    external_links:   int
    missing_alt:      int
    keyword_in_title: bool
    keyword_in_meta:  bool
    keyword_in_h1:    bool
    title_length:     int
    meta_length:      int
    seo_score:        int
    score_band:       str
    recommendations:  List[Dict[str, str]]
    technical_seo:    Dict[str, Any]
    content_quality:  Dict[str, Any]
    summary:          SeoSummary
    geo_score:        Optional[Dict[str, Any]] = None
    pagespeed:        Optional[Dict[str, Any]] = None
    pool_uses:        int
    pool_remaining:   int


# ── /competitors ──────────────────────────────────────────────────────────────

class CompetitorsRequest(BaseModel):
    url:           str
    keyword:       str = Field(default="", max_length=200)
    user_api_keys: Optional[UserApiKeys] = None

    @field_validator("url")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        return _validate_url(v)


class CompetitorResult(BaseModel):
    venue_name:     str
    url:            str
    seo_score:      int
    score_band:     str
    word_count:     int
    keyword_count:  int
    keyword_density: float
    internal_links: int
    external_links: int
    missing_alt:    int
    https:          str
    schema:         str
    role:           str = "Direct Competitor"


class CompetitorsResponse(BaseModel):
    primary:        Dict[str, Any]
    competitors:    List[Dict[str, Any]]
    search_log:     List[str]
    location_msg:   str
    ai_summary:     Optional[str] = None
    pool_uses:      int
    pool_remaining: int


# ── /compare ─────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    url1:          str
    url2:          str
    keyword:       str
    user_api_keys: Optional[UserApiKeys] = None

    @field_validator("url1", "url2")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        return _validate_url(v)


class CompareResponse(BaseModel):
    site1:          Dict[str, Any]
    site2:          Dict[str, Any]
    comparison:     Dict[str, str]   # metric -> winner label
    pool_uses:      int
    pool_remaining: int


# ── /leaderboard ─────────────────────────────────────────────────────────────

class LeaderboardRequest(BaseModel):
    urls:          List[str]
    keyword:       str
    user_api_keys: Optional[UserApiKeys] = None

    @field_validator("urls")
    @classmethod
    def ensure_schemes(cls, urls: List[str]) -> List[str]:
        if len(urls) > 10:
            raise ValueError("Maximum 10 URLs allowed")
        return [_validate_url(u) for u in urls]


class LeaderboardResponse(BaseModel):
    rows:           List[Dict[str, Any]]
    pool_uses:      int
    pool_remaining: int


# ── /pagespeed ────────────────────────────────────────────────────────────────

class PageSpeedRequest(BaseModel):
    url:           str
    strategy:      str = "mobile"
    user_api_keys: Optional[UserApiKeys] = None

    @field_validator("url")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        return _validate_url(v)


class PageSpeedResponse(BaseModel):
    url:            str
    strategy:       str
    data:           Dict[str, Any]
    pool_uses:      int
    pool_remaining: int
