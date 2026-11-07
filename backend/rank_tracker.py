"""
Keyword rank tracker — stores URL+keyword pairs and checks SERP position via Serper.
Primary store: Supabase REST API (when SUPABASE_URL + SUPABASE_KEY are set).
Fallback store: local SQLite (works with zero config).
"""

from __future__ import annotations

import os
import sqlite3
import json
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

# /data is a Railway persistent volume mount; fall back to local dir if not mounted
_DB_PATH = "/data/rank_tracker.db" if os.path.isdir("/data") else os.path.join(os.path.dirname(__file__), "rank_tracker.db")


# ── SQLite fallback ────────────────────────────────────────────────────────────

def _get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rank_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(url, keyword)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rank_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id INTEGER REFERENCES rank_tracking(id),
            position INTEGER,
            found INTEGER DEFAULT 0,
            checked_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _sqlite_save_tracking(url: str, keyword: str) -> dict:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO rank_tracking (url, keyword) VALUES (?, ?)",
            (url, keyword),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM rank_tracking WHERE url=? AND keyword=?", (url, keyword)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def _sqlite_save_rank(tracking_id, position):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO rank_history (tracking_id, position, found) VALUES (?, ?, ?)",
            (tracking_id, position, 1 if position is not None else 0),
        )
        conn.commit()
    finally:
        conn.close()


def _sqlite_get_history(url: str) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM rank_tracking WHERE url=? ORDER BY created_at DESC", (url,)
        ).fetchall()
        result = []
        for r in rows:
            r = dict(r)
            history = conn.execute(
                "SELECT * FROM rank_history WHERE tracking_id=? ORDER BY checked_at DESC",
                (r["id"],),
            ).fetchall()
            r["rank_history"] = [dict(h) for h in history]
            result.append(r)
        return result
    finally:
        conn.close()


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _supa_headers(supabase_key: str) -> dict:
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }


def _supa_save_tracking(url: str, keyword: str, supabase_url: str, supabase_key: str) -> dict:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/rank_tracking"
    headers = {
        **_supa_headers(supabase_key),
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    resp = requests.post(endpoint, json={"url": url, "keyword": keyword}, headers=headers, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else {"url": url, "keyword": keyword}


def _supa_save_rank(tracking_id, position, supabase_url, supabase_key):
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/rank_history"
    headers = {**_supa_headers(supabase_key), "Prefer": "return=representation"}
    requests.post(endpoint, json={"tracking_id": tracking_id, "position": position, "found": position is not None}, headers=headers, timeout=10)


def _supa_get_history(url: str, supabase_url: str, supabase_key: str) -> list:
    from urllib.parse import quote
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/rank_tracking"
        f"?url=eq.{quote(url, safe='')}"
        f"&select=*,rank_history(*)"
        f"&order=created_at.desc"
    )
    resp = requests.get(endpoint, headers=_supa_headers(supabase_key), timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── Public API ─────────────────────────────────────────────────────────────────

def save_tracking(url: str, keyword: str, supabase_url: str = "", supabase_key: str = "") -> dict:
    if supabase_url and supabase_key:
        return _supa_save_tracking(url, keyword, supabase_url, supabase_key)
    return _sqlite_save_tracking(url, keyword)


SERP_DEPTH_PAGES = 3   # Serper ignores num=100 now and returns ~10 per page


def serp_organic_links(keyword: str, serper_key: str, pages: int = SERP_DEPTH_PAGES,
                       gl: str | None = None, hl: str | None = None) -> list[str]:
    """Organic result links in Google order, top ~10 x pages (1 Serper credit per page).

    Google redirect entries (google.com/...) that Serper mixes into "organic" are
    dropped so they don't take up positions.
    """
    links: list[str] = []
    payload = {"q": keyword, "gl": (gl or "us").lower()}   # US only when the country is unknown
    if hl:
        payload["hl"] = hl
    for page in range(1, pages + 1):
        resp = requests.post(
            "https://google.serper.dev/search",
            json={**payload, "page": page},
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        organic = resp.json().get("organic", [])
        if not organic:
            break
        for r in organic:
            link = r.get("link", "")
            host = (urlparse(link).hostname or "").lower()
            if host.startswith("google.") or ".google." in host:
                continue
            links.append(link)
    return links


def _site_and_path(u: str) -> tuple[str, str]:
    p = urlparse(u.lower() if "//" in u else "https://" + u.lower())
    host = p.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host, p.path.rstrip("/")


def url_matches(target: str, result: str) -> bool:
    """A search result counts for `target` only on the exact same host (www.
    ignored) and, when target has a path, under that path. No substring
    matching: "ample.com" is not "example.com", "example.com" is not "example.com.au"."""
    t_host, t_path = _site_and_path(target)
    r_host, r_path = _site_and_path(result)
    if not t_host or t_host != r_host:
        return False
    return not t_path or r_path == t_path or r_path.startswith(t_path + "/")


def check_rank(url: str, keyword: str, serper_key: str, gl: str | None = None, hl: str | None = None) -> dict:
    if gl is None:
        from location_utils import get_location_from_url
        loc = get_location_from_url(url)
        gl, hl = loc["serper_gl"], loc.get("serper_hl")
    links = serp_organic_links(keyword, serper_key, gl=gl, hl=hl)

    position = None
    for i, link in enumerate(links, start=1):
        if url_matches(url, link):
            position = i
            break

    return {
        "position": position,
        "found": position is not None,
        "url": url,
        "keyword": keyword,
        "gl": gl,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def save_rank_result(tracking_id, position, supabase_url: str = "", supabase_key: str = "") -> None:
    if supabase_url and supabase_key:
        _supa_save_rank(tracking_id, position, supabase_url, supabase_key)
    else:
        _sqlite_save_rank(tracking_id, position)


def get_tracking_history(url: str, supabase_url: str = "", supabase_key: str = "") -> list:
    if supabase_url and supabase_key:
        return _supa_get_history(url, supabase_url, supabase_key)
    return _sqlite_get_history(url)


def create_tables_sql() -> str:
    return """
CREATE TABLE IF NOT EXISTS rank_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  url TEXT NOT NULL,
  keyword TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(url, keyword)
);

CREATE TABLE IF NOT EXISTS rank_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tracking_id UUID REFERENCES rank_tracking(id),
  position INTEGER,
  found BOOLEAN DEFAULT false,
  checked_at TIMESTAMPTZ DEFAULT NOW()
);
"""
