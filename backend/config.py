"""
Configuration — loads env vars from .env or environment.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API keys ──────────────────────────────────────────────────────────────────
SERPER_API_KEY    = os.getenv("SERPER_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")
SCRAPER_API_KEY   = os.getenv("SCRAPER_API_KEY", "")
ZENROWS_API_KEY   = os.getenv("ZENROWS_API_KEY", "")

# ── Auth ──────────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# ── Upstash Redis (rate limiting) ─────────────────────────────────────────────
UPSTASH_REDIS_REST_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# ── Rate limit ────────────────────────────────────────────────────────────────
GLOBAL_LIMIT = int(os.getenv("GLOBAL_LIMIT", "30"))


def active_keys(user_api_keys: dict | None = None) -> dict:
    """
    Return the effective set of API keys.

    Priority:
      1. User-supplied keys (per-request)
      2. Server-level keys from env vars

    Args:
        user_api_keys: Optional dict that may contain:
            serper_key, gemini_key, pagespeed_key, scraper_api_key, zenrows_api_key

    Returns:
        Dict with keys: serper, gemini, pagespeed, scraper_api, zenrows
    """
    u = user_api_keys or {}
    return {
        "serper":      u.get("serper_key")      or SERPER_API_KEY,
        "gemini":      u.get("gemini_key")       or GEMINI_API_KEY,
        "pagespeed":   u.get("pagespeed_key")    or PAGESPEED_API_KEY,
        "scraper_api": u.get("scraper_api_key")  or SCRAPER_API_KEY,
        "zenrows":     u.get("zenrows_api_key")  or ZENROWS_API_KEY,
    }
