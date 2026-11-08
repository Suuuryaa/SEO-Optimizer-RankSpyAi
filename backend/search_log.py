"""Private daily log of searches, for the site owner only.

One Redis list per New Zealand day (searchlog:YYYY-MM-DD). Each list deletes
itself 4 days after its first entry, so a day stays downloadable for 3 days
after it ends and nothing is kept longer. No IP address is stored.
Logging never raises: a Redis problem must not break a visitor's scan.
"""
import io
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

logger = logging.getLogger(__name__)

NZ = ZoneInfo("Pacific/Auckland")
KEEP_SECONDS = 4 * 24 * 3600
MAX_PER_DAY = 20000
_PREFIX = "searchlog:"
_BOT_WORDS = ("bot", "crawl", "spider", "slurp", "headless", "python-requests",
              "curl", "wget", "httpx", "go-http", "scrapy", "phantom", "selenium", "playwright")
COLUMNS = ["time_nz", "website", "keyword", "visitor_country", "site_country",
           "from_cache", "fresh_scan", "geo", "pagespeed", "js_crawl", "looks_like_bot", "browser"]


def _cmd(*args):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return None
    r = requests.post(UPSTASH_REDIS_REST_URL,
                      headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
                      json=list(args), timeout=5)
    return r.json().get("result")


def _day_key(day: str) -> str:
    return _PREFIX + day


def today_nz() -> str:
    return datetime.now(NZ).strftime("%Y-%m-%d")


def looks_like_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return not ua or any(w in ua for w in _BOT_WORDS)


def _browser(user_agent: str) -> str:
    ua = user_agent or ""
    for name in ("Edg", "OPR", "Firefox", "Chrome", "Safari"):
        if name in ua:
            return {"Edg": "Edge", "OPR": "Opera"}.get(name, name)
    return ua[:40] or "unknown"


def build_row(url: str, keyword: str, headers, *, cached: bool, fresh=False,
              geo=False, pagespeed=False, js=False) -> dict:
    """One log line. headers is any mapping with .get (a Starlette Headers object)."""
    from location_utils import detect_country_from_domain
    ua = headers.get("user-agent", "") if headers else ""
    try:
        site_country = detect_country_from_domain(url)[1]
    except Exception:
        site_country = ""
    return {
        "time_nz": datetime.now(NZ).strftime("%Y-%m-%d %H:%M:%S"),
        "website": url,
        "keyword": keyword or "",
        "visitor_country": (headers.get("cf-ipcountry", "") if headers else "") or "",
        "site_country": site_country,
        "from_cache": bool(cached),
        "fresh_scan": bool(fresh),
        "geo": bool(geo),
        "pagespeed": bool(pagespeed),
        "js_crawl": bool(js),
        "looks_like_bot": looks_like_bot(ua),
        "browser": _browser(ua),
    }


def record(row: dict) -> None:
    try:
        key = _day_key(row["time_nz"][:10])
        n = _cmd("RPUSH", key, json.dumps(row))
        if n == 1:
            _cmd("EXPIRE", key, KEEP_SECONDS)
        elif n and n > MAX_PER_DAY:
            _cmd("LTRIM", key, -MAX_PER_DAY, -1)
    except Exception as exc:
        logger.warning(f"search_log.record failed: {exc}")


def get_day(day: str) -> list:
    raw = _cmd("LRANGE", _day_key(day), 0, -1) or []
    rows = []
    for item in raw:
        try:
            rows.append(json.loads(item))
        except Exception:
            continue
    return rows


def available_days() -> list:
    """Days that still have a log, newest first (checks the last 5 NZ days)."""
    now = datetime.now(NZ)
    days = []
    for i in range(5):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        n = _cmd("LLEN", _day_key(d)) or 0
        if n:
            days.append({"date": d, "searches": n})
    return days


def to_xlsx(rows: list, day: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = day
    ws.append(COLUMNS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(col, "") for col in COLUMNS])
    for col, width in zip("ABCDEFGHIJKL", (20, 45, 30, 15, 18, 11, 11, 7, 10, 9, 15, 12)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
