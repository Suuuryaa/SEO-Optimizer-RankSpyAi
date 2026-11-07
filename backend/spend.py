"""
Daily spend cap for free usage.

Every paid API call made with the SERVER's keys (Gemini, Serper, proxies) adds its
estimated cost to a per-UTC-day counter. When the day's total passes
FREE_DAILY_USD_CAP, free scans are refused until the next UTC day, so a bad day
(bots, a viral post, a pricing surprise) can never turn into a big bill.
Calls made with a visitor's own keys are not counted.

Costs are estimates on the high side; reconcile against the Google Cloud and
Serper bills. Stored in micro-dollars (integers) so Redis INCRBY works.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FREE_DAILY_USD_CAP = float(os.getenv("FREE_DAILY_USD_CAP", "1.0"))
# Conservative per-1M-token prices (newest Flash list price; Flash-Lite is cheaper)
GEMINI_USD_PER_M_IN = float(os.getenv("GEMINI_USD_PER_M_IN", "0.75"))
GEMINI_USD_PER_M_OUT = float(os.getenv("GEMINI_USD_PER_M_OUT", "3.75"))
SERPER_USD_PER_QUERY = float(os.getenv("SERPER_USD_PER_QUERY", "0.001"))
PROXY_USD_PER_FETCH = float(os.getenv("PROXY_USD_PER_FETCH", "0.01"))

_local: dict[str, int] = {}
_lock = threading.Lock()
_alerted: set[str] = set()


def _key() -> str:
    return "spend:usd_micro:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def add(usd: float, what: str = "") -> None:
    micro = max(0, int(round(usd * 1_000_000)))
    if not micro:
        return
    key = _key()
    total = None
    try:
        from cache import _redis_cmd
        total = _redis_cmd("INCRBY", key, micro)
        if total is not None and int(total) == micro:
            _redis_cmd("EXPIRE", key, 3 * 24 * 3600)
    except Exception:
        total = None
    with _lock:
        _local[key] = _local.get(key, 0) + micro
        if total is None:
            total = _local[key]
    if int(total) / 1_000_000 >= FREE_DAILY_USD_CAP and key not in _alerted:
        _alerted.add(key)
        logger.warning(f"SPEND CAP reached: US${int(total) / 1_000_000:.3f} today (cap {FREE_DAILY_USD_CAP}) "
                       f"— free scans paused until 00:00 UTC")


def today_usd() -> float:
    key = _key()
    val = None
    try:
        from cache import _redis_cmd
        val = _redis_cmd("GET", key)
    except Exception:
        val = None
    if val is None:
        with _lock:
            return _local.get(key, 0) / 1_000_000
    try:
        return int(val) / 1_000_000
    except (TypeError, ValueError):
        return 0.0


def over_cap() -> bool:
    return today_usd() >= FREE_DAILY_USD_CAP


# ── Hooks used by the API clients ────────────────────────────────────────────
def _is_server_key(key: str, env_name: str) -> bool:
    server = os.getenv(env_name, "")
    return bool(key) and bool(server) and key == server


def gemini_call(api_key: str, usage: dict | None) -> None:
    if not _is_server_key(api_key, "GEMINI_API_KEY"):
        return
    usage = usage or {}
    tin = int(usage.get("promptTokenCount") or 0)
    tout = int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
    if not (tin or tout):
        tin, tout = 3000, 1500          # no usage reported: assume a typical call
    add(tin / 1e6 * GEMINI_USD_PER_M_IN + tout / 1e6 * GEMINI_USD_PER_M_OUT, "gemini")


def serper_call(api_key: str) -> None:
    if _is_server_key(api_key, "SERPER_API_KEY"):
        add(SERPER_USD_PER_QUERY, "serper")


def proxy_call() -> None:
    add(PROXY_USD_PER_FETCH, "proxy")
