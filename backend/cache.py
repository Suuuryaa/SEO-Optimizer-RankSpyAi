"""
Redis result cache backed by Upstash.

Keys
----
  result:v{SCORING_VERSION}:{hash} — cached /analyze response (TTL 6h)
  rate:{ip}:{date}     — per-IP daily request counter (TTL 25h)

All values are JSON-serialised strings.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import requests

from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

logger = logging.getLogger(__name__)

_TIMEOUT    = 5
_RESULT_TTL = 21600  # 6 h

# Per-endpoint TTLs — use these when caching specific API call results
CACHE_TTL = {
    "analyze":        86400,  # 24h — page content changes slowly
    "competitors":     3600,  # 1h  — SERP shifts hourly
    "pagespeed":       3600,  # 1h
    "gemini_summary": 86400,  # 24h — same URL+keyword = same AI output
    "serper_search":   1800,  # 30m — search results
    "leaderboard":     3600,  # 1h
}

_RATE_TTL   = 90000  # 25 h  (slight padding so midnight resets cleanly)

DAILY_FREE_LIMIT = 10  # demo mode — global pool of 10 is the real cap


def _headers() -> dict:
    return {"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"}


def _redis(path: str, method: str = "GET", body=None):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return None
    url = f"{UPSTASH_REDIS_REST_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=_headers(), timeout=_TIMEOUT)
        else:
            r = requests.post(url, headers=_headers(), json=body, timeout=_TIMEOUT)
        return r.json().get("result")
    except Exception as exc:
        logger.warning(f"cache._redis({path}) failed: {exc}")
        return None


def _redis_cmd(*args):
    """Run one Redis command via Upstash's JSON body API (POST ["CMD", arg, ...]).

    Values travel in the JSON body, so '/', '?', '#' and spaces are safe.
    Returns the result, or None when Redis is unconfigured or the call fails.
    """
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return None
    try:
        r = requests.post(UPSTASH_REDIS_REST_URL, headers=_headers(), json=[str(a) for a in args], timeout=_TIMEOUT)
        return r.json().get("result")
    except Exception as exc:
        logger.warning(f"cache._redis_cmd({args[0] if args else ''}) failed: {exc}")
        return None


# ── Result caching ────────────────────────────────────────────────────────────

def _cache_key(url: str, keyword: str) -> str:
    from scoring import SCORING_VERSION
    # Only scheme and host are case-insensitive: /Page and /page can be different pages
    from urllib.parse import urlsplit, urlunsplit
    u = urlsplit(url.strip())
    url = urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path, u.query, u.fragment))
    raw = f"{url}|{keyword.lower().strip()}"
    h = hashlib.md5(raw.encode()).hexdigest()
    return f"result:v{SCORING_VERSION}:{h}"


def get_cached(url: str, keyword: str):
    """Return cached result dict or None."""
    raw = _redis_cmd("GET", _cache_key(url, keyword))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def set_cached(url: str, keyword: str, data: dict):
    """Store result dict for 6 h with its UTC cache time. Strips internal "_" fields."""
    key = _cache_key(url, keyword)
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    clean["cached_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        payload = json.dumps(clean, default=str)
        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            return
        requests.post(UPSTASH_REDIS_REST_URL, headers=_headers(),
                      json=["SET", key, payload, "EX", _RESULT_TTL], timeout=_TIMEOUT)
    except Exception as exc:
        logger.warning(f"cache.set_cached failed: {exc}")


def _redis_set_ex(key: str, value: str, ttl: int):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return
    try:
        requests.post(UPSTASH_REDIS_REST_URL, headers=_headers(),
                      json=["SET", key, str(value), "EX", int(ttl)], timeout=_TIMEOUT)
    except Exception as exc:
        logger.warning(f"cache._redis_set_ex failed: {exc}")


# ── Per-IP rate limiting ──────────────────────────────────────────────────────

def _ip_key(ip: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"rate:{ip}:{today}"


def check_ip_rate_limit(ip: str) -> dict:
    """
    Increment the per-IP daily counter and return whether the request is allowed.
    Returns: { allowed: bool, used: int, remaining: int }
    """
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        # No Redis — allow all (fail open)
        return {"allowed": True, "used": 0, "remaining": DAILY_FREE_LIMIT}

    key = _ip_key(ip)
    try:
        # INCR atomically
        r = requests.get(
            f"{UPSTASH_REDIS_REST_URL}/incr/{key}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        count = int(r.json().get("result", 1))

        # Set TTL on first use
        if count == 1:
            requests.get(
                f"{UPSTASH_REDIS_REST_URL}/expire/{key}/{_RATE_TTL}",
                headers=_headers(),
                timeout=_TIMEOUT,
            )

        allowed   = count <= DAILY_FREE_LIMIT
        remaining = max(0, DAILY_FREE_LIMIT - count)

        if not allowed:
            # Decrement back so the counter stays accurate
            requests.get(
                f"{UPSTASH_REDIS_REST_URL}/decrby/{key}/1",
                headers=_headers(),
                timeout=_TIMEOUT,
            )

        return {"allowed": allowed, "used": count, "remaining": remaining}

    except Exception as exc:
        logger.warning(f"check_ip_rate_limit failed: {exc} — allowing request")
        return {"allowed": True, "used": 0, "remaining": DAILY_FREE_LIMIT}


def get_ip_usage(ip: str) -> dict:
    """Return current usage without incrementing."""
    key = _ip_key(ip)
    raw = _redis(f"/get/{key}")
    used = int(raw) if raw else 0
    return {"used": used, "remaining": max(0, DAILY_FREE_LIMIT - used)}


# In-process fallback counters, used when Redis is unconfigured or failing, so
# per-IP limits still hold on our single replica. {(bucket, ip, day): count}
import threading as _threading
_LOCAL_QUOTA: dict = {}
_LOCAL_LOCK = _threading.Lock()


def _local_quota(ip: str, bucket: str, limit: int, today: str) -> bool:
    with _LOCAL_LOCK:
        if len(_LOCAL_QUOTA) > 50_000:
            for k in [k for k in _LOCAL_QUOTA if k[2] != today]:
                _LOCAL_QUOTA.pop(k, None)
        key = (bucket, ip, today)
        _LOCAL_QUOTA[key] = _LOCAL_QUOTA.get(key, 0) + 1
        return _LOCAL_QUOTA[key] <= limit


def check_ip_quota(ip: str, bucket: str, limit: int) -> bool:
    """
    Per-IP daily counter for a named bucket (e.g. "helpers", "track").
    Used for endpoints that do real work (scraping, SERP calls) but don't draw
    from the global pool. When Redis is unavailable the limit is enforced
    in-process instead of failing open.
    """
    from net_safety import visitor_bucket
    ip = visitor_bucket(ip)          # IPv6: count the /64, not each address
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"quota:{bucket}:{ip}:{today}"
    try:
        count = _redis_cmd("INCR", key)
        if count is None:
            return _local_quota(ip, bucket, limit, today)
        count = int(count)
        if count == 1:
            _redis_cmd("EXPIRE", key, _RATE_TTL)
        return count <= limit
    except Exception as exc:
        logger.warning(f"check_ip_quota({bucket}) failed: {exc} — using in-process counter")
        return _local_quota(ip, bucket, limit, today)
