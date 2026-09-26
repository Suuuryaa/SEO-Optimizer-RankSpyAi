"""
Redis-based global rate limiter backed by Upstash REST API.

The pool is shared across ALL users — the same logic as in the Streamlit app.
When users supply their own API keys the pool is bypassed (user-keyed calls
are counted separately with key "user_keyed:uses", never capped).
"""

import logging
import requests

from config import (
    UPSTASH_REDIS_REST_URL,
    UPSTASH_REDIS_REST_TOKEN,
    GLOBAL_LIMIT,
)

logger = logging.getLogger(__name__)

_GLOBAL_KEY    = "global:uses"
_USER_KEY      = "user_keyed:uses"
_TIMEOUT       = 5          # seconds for Upstash HTTP calls


# ── Low-level Upstash helpers ─────────────────────────────────────────────────

def _redis_get(key: str) -> int:
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return 0
    try:
        resp = requests.get(
            f"{UPSTASH_REDIS_REST_URL}/get/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
            timeout=_TIMEOUT,
        )
        val = resp.json().get("result")
        return int(val) if val else 0
    except Exception as exc:
        logger.warning(f"rate_limiter._redis_get({key}) failed: {exc}")
        return 0


def _redis_incr(key: str) -> int:
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return 1
    try:
        resp = requests.get(
            f"{UPSTASH_REDIS_REST_URL}/incr/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
            timeout=_TIMEOUT,
        )
        return int(resp.json().get("result", 1))
    except Exception as exc:
        logger.warning(f"rate_limiter._redis_incr({key}) failed: {exc}")
        return 1


# ── Public API ────────────────────────────────────────────────────────────────

def get_global_uses() -> int:
    """Return current number of uses from the shared pool."""
    return _redis_get(_GLOBAL_KEY)


def get_remaining() -> int:
    """Return uses remaining in the shared pool."""
    return max(0, GLOBAL_LIMIT - get_global_uses())


def increment_global_uses() -> int:
    """Increment and return the new total uses count."""
    return _redis_incr(_GLOBAL_KEY)


def check_and_consume(user_has_own_keys: bool = False) -> dict:
    """
    Gate a single API call through the rate limiter.

    Args:
        user_has_own_keys: When True the global pool is NOT consumed —
            the call still proceeds and only the user_keyed counter increments.

    Returns:
        dict with:
          allowed  (bool)   — whether the call should proceed
          uses     (int)    — pool uses so far (or 0 for user-keyed calls)
          remaining (int)   — uses left in pool
          message  (str)    — human-readable status
    """
    if user_has_own_keys:
        _redis_incr(_USER_KEY)
        return {
            "allowed":   True,
            "uses":      0,
            "remaining": GLOBAL_LIMIT,
            "message":   "User-supplied keys — pool not consumed.",
        }

    uses = get_global_uses()
    if uses >= GLOBAL_LIMIT:
        return {
            "allowed":   False,
            "uses":      uses,
            "remaining": 0,
            "message":   (
                f"Global usage pool exhausted ({uses}/{GLOBAL_LIMIT}). "
                "Supply your own API keys for unlimited use."
            ),
        }

    new_uses = increment_global_uses()
    return {
        "allowed":   True,
        "uses":      new_uses,
        "remaining": max(0, GLOBAL_LIMIT - new_uses),
        "message":   f"OK — pool use {new_uses}/{GLOBAL_LIMIT}.",
    }
