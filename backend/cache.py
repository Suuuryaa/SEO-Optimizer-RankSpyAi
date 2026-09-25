"""
Redis result cache backed by Upstash.

Keys
----
  result:{hash}        — cached /analyze response (TTL 24h)
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

_TIMEOUT   = 5
_RESULT_TTL = 86400   # 24 h
_RATE_TTL   = 90000   # 25 h  (slight padding so midnight resets cleanly)

DAILY_FREE_LIMIT = 3


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


# ── Result caching ────────────────────────────────────────────────────────────

def _cache_key(url: str, keyword: str) -> str:
    raw = f"{url.lower().strip()}|{keyword.lower().strip()}"
    h = hashlib.md5(raw.encode()).hexdigest()
    return f"result:{h}"


def get_cached(url: str, keyword: str):
    """Return cached result dict or None."""
    key = _cache_key(url, keyword)
    raw = _redis(f"/get/{key}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def set_cached(url: str, keyword: str, data: dict):
    """Store result dict with 24h TTL. Strips large internal fields."""
    key = _cache_key(url, keyword)
    # Don't cache internal soup/text fields
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    clean["_cached"] = True
    try:
        payload = json.dumps(clean, default=str)
        # SET key value EX ttl
        _redis(f"/set/{key}/ex/{_RESULT_TTL}", method="POST",
               body={"pipeline": [[f"SET {key} {payload} EX {_RESULT_TTL}"]]})
        # Simpler: use pipeline endpoint
        _redis_set_ex(key, payload, _RESULT_TTL)
    except Exception as exc:
        logger.warning(f"cache.set_cached failed: {exc}")


def _redis_set_ex(key: str, value: str, ttl: int):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return
    try:
        requests.get(
            f"{UPSTASH_REDIS_REST_URL}/set/{key}/{value}/ex/{ttl}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
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
