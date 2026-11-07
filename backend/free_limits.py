"""
Per-visitor free allowance.

One "visitor" = one IPv4 address or one IPv6 /64 (see net_safety.visitor_bucket).
- FREE_SCANS_PER_DAY page scans per visitor per UTC day (cache hits are free).
- FREE_RESCANS_PER_PAGE "rescan after fixing" runs per page per visitor per day:
  a fresh scan of a URL+keyword this visitor already scanned in the last 24 h
  costs nothing, so the scan → fix → check-again loop never hits the limit.
- FREE_COMPARISONS_PER_DAY competitor comparisons per visitor per day.

The global pool in rate_limiter.py stays as a site-wide circuit breaker on top.
Counters live in Upstash Redis; when Redis is down an in-process counter is used
(fail closed, never unlimited).
"""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timedelta, timezone

FREE_SCANS_PER_DAY = int(os.getenv("FREE_SCANS_PER_DAY", "3"))
FREE_RESCANS_PER_PAGE = int(os.getenv("FREE_RESCANS_PER_PAGE", "2"))
FREE_COMPARISONS_PER_DAY = int(os.getenv("FREE_COMPARISONS_PER_DAY", "1"))

_DAY_TTL = 2 * 24 * 3600
_SEEN_TTL = 24 * 3600

_local: dict[str, int] = {}
_local_lock = threading.Lock()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resets_at() -> str:
    """Next UTC midnight, ISO 8601 — the frontend shows it in the visitor's own time."""
    now = datetime.now(timezone.utc)
    nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.isoformat().replace("+00:00", "Z")


def _cmd(*args):
    from cache import _redis_cmd
    try:
        return _redis_cmd(*args)
    except Exception:
        return None


def _incr(key: str, ttl: int) -> int:
    val = _cmd("INCR", key)
    if val is None:
        with _local_lock:
            _local[key] = _local.get(key, 0) + 1
            return _local[key]
    val = int(val)
    if val == 1:
        _cmd("EXPIRE", key, ttl)
    return val


def _decr(key: str) -> None:
    val = _cmd("DECR", key)
    if val is None:
        with _local_lock:
            _local[key] = max(0, _local.get(key, 0) - 1)
    elif int(val) < 0:
        _cmd("SET", key, "0")


def _get(key: str) -> int:
    val = _cmd("GET", key)
    if val is None:
        with _local_lock:
            return _local.get(key, 0)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _page_id(url: str, keyword: str) -> str:
    from cache import _cache_key
    return _cache_key(url, keyword).rsplit(":", 1)[-1]


# ── Scans ────────────────────────────────────────────────────────────────────
def _scan_key(bucket: str, kind: str) -> str:
    return f"free:{kind}:{bucket}:{_today()}"


def _limit(kind: str) -> int:
    return FREE_COMPARISONS_PER_DAY if kind == "compare" else FREE_SCANS_PER_DAY


def used(bucket: str, kind: str = "scan") -> int:
    return min(_get(_scan_key(bucket, kind)), _limit(kind))


def consume(bucket: str, kind: str = "scan") -> bool:
    """Take one free scan (or comparison). False when today's allowance is used up."""
    key = _scan_key(bucket, kind)
    if _incr(key, _DAY_TTL) > _limit(kind):
        _decr(key)
        return False
    return True


def give_back(bucket: str, kind: str = "scan") -> None:
    _decr(_scan_key(bucket, kind))


# ── Rescan after fixing ──────────────────────────────────────────────────────
def mark_seen(bucket: str, url: str, keyword: str) -> None:
    """This visitor has seen a result for this page — rescans of it are free for 24 h."""
    from cache import _redis_set_ex
    key = f"free:seen:{bucket}:{_page_id(url, keyword)}"
    try:
        _redis_set_ex(key, "1", _SEEN_TTL)
    except Exception:
        pass
    with _local_lock:
        _local[key] = 1


def take_free_rescan(bucket: str, url: str, keyword: str) -> bool:
    """True (and one rescan used) when this is a free 'rescan after fixing'."""
    pid = _page_id(url, keyword)
    if not (_get(f"free:seen:{bucket}:{pid}") or _local.get(f"free:seen:{bucket}:{pid}")):
        return False
    key = f"free:rescan:{bucket}:{pid}:{_today()}"
    if _incr(key, _DAY_TTL) > FREE_RESCANS_PER_PAGE:
        _decr(key)
        return False
    return True


def rescans_left(bucket: str, url: str, keyword: str) -> int:
    pid = _page_id(url, keyword)
    return max(0, FREE_RESCANS_PER_PAGE - _get(f"free:rescan:{bucket}:{pid}:{_today()}"))


def give_back_rescan(bucket: str, url: str, keyword: str) -> None:
    _decr(f"free:rescan:{bucket}:{_page_id(url, keyword)}:{_today()}")


def status(bucket: str) -> dict:
    scans = used(bucket, "scan")
    comps = used(bucket, "compare")
    return {
        "scans_used": scans, "scans_limit": FREE_SCANS_PER_DAY,
        "scans_remaining": max(0, FREE_SCANS_PER_DAY - scans),
        "comparisons_used": comps, "comparisons_limit": FREE_COMPARISONS_PER_DAY,
        "comparisons_remaining": max(0, FREE_COMPARISONS_PER_DAY - comps),
        "free_rescans_per_page": FREE_RESCANS_PER_PAGE,
        "resets_at": resets_at(),
    }


def page_fingerprint(url: str, keyword: str) -> str:
    """Short stable id for logs."""
    return hashlib.sha1(f"{url}|{keyword}".encode()).hexdigest()[:10]
