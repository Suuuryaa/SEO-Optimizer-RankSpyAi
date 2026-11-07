"""B8 — error kinds, user-safe errors, body size cap."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import main
    return TestClient(main.app, raise_server_exceptions=False)


def test_bad_content_length_400(client):
    r = client.post("/jobs/analyze", content=b"{}", headers={"Content-Length": "abc", "Content-Type": "application/json"})
    assert r.status_code == 400


def test_declared_too_large_413(client):
    r = client.post("/jobs/analyze", content=b"{}", headers={"Content-Length": "2000000", "Content-Type": "application/json"})
    assert r.status_code == 413


def test_chunked_too_large_413(client):
    def gen():
        for _ in range(32):
            yield b"x" * 65536          # 2 MB, no Content-Length
    r = client.post("/jobs/analyze", content=gen(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def _run_job(main, coro_factory):
    async def scenario():
        out = main._start_job("analyze", coro_factory, "5.5.5.5")
        for _ in range(50):
            await asyncio.sleep(0.01)
            if main._JOBS[out["job_id"]]["status"] in ("done", "error"):
                break
        return main._JOBS[out["job_id"]]
    return asyncio.run(scenario())


@pytest.mark.parametrize("exc_factory,status,kind", [
    (lambda m: m.FetchError("blocked", "This site blocked our scanner."), 422, "blocked"),
    (lambda m: m._analysis_http_error(m.FetchError("not_html", "Not a page.")), 422, "not_html"),
    (lambda m: m.HTTPException(status_code=429, detail="Pool used up"), 429, "rate_limited"),
    (lambda m: m.HTTPException(status_code=503, detail="Busy"), 503, "busy"),
    (lambda m: RuntimeError("secret internal detail /etc/passwd"), 500, "internal"),
])
def test_job_error_kinds(monkeypatch, exc_factory, status, kind):
    import main
    monkeypatch.setattr(main, "_JOBS", {})
    exc = exc_factory(main)

    async def fail():
        raise exc
    job = _run_job(main, fail)
    assert job["status"] == "error" and job["status_code"] == status and job["error_kind"] == kind
    assert "secret internal detail" not in job["error"]


def test_job_status_exposes_error_kind(monkeypatch):
    import main
    monkeypatch.setattr(main, "_JOBS", {"j1": {"id": "j1", "kind": "analyze", "status": "error", "step": "",
                                               "steps": [], "created": 0, "finished": 1, "error": "x",
                                               "status_code": 422, "error_kind": "timeout", "ip": "a"}})
    out = asyncio.run(main.job_status("j1"))
    assert out["error_kind"] == "timeout" and "ip" not in out


def test_gemini_failure_no_exception_text(monkeypatch):
    import ai.gemini as gemini
    import summary_utils

    def boom(*a, **k):
        raise gemini.GeminiError("all_failed", "models/x: HTTP 500 internal SECRETDETAIL")
    monkeypatch.setattr(gemini, "generate_text", boom)
    out = summary_utils.generate_ai_executive_summary("AIzaFAKE", "Site", "kw", 3, 50, "Rival", [], [], [])
    assert out is None


def test_competitor_row_error_is_user_safe(public_dns, monkeypatch):
    import leaderboard_utils
    from seo_utils import FetchError

    def boom(u):
        raise FetchError("blocked", "raw internal text")
    monkeypatch.setattr(leaderboard_utils, "get_page_soup", boom)
    row = leaderboard_utils.analyze_venue("https://example.com/", "kw")
    assert row["error"] == "Couldn't scan this site, it blocked our crawler." and row["error_kind"] == "blocked"

    def boom2(u):
        raise ValueError("Traceback secret")
    monkeypatch.setattr(leaderboard_utils, "get_page_soup", boom2)
    row = leaderboard_utils.analyze_venue("https://example.com/", "kw")
    assert "secret" not in row["error"] and row["error_kind"] == "internal"


def test_competitors_ai_failure_and_rows(public_dns, monkeypatch):
    """Competitors: AI failure → ai_summary None + ai_summary_error; search_location present."""
    import main
    from models import CompetitorsRequest
    monkeypatch.setattr(main, "check_and_consume", lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "active_keys", lambda u=None: {"serper": "s", "gemini": "g", "pagespeed": "", "scraper_api": "", "zenrows": ""})
    monkeypatch.setattr(main, "_full_seo_analysis", lambda u, k, keys: {
        "title": "Mine", "seo_score": 50, "keyword_count": 1, "word_count": 400, "missing_alt": 0,
        "_soup": None, "_text": "", "_x_robots_tag": None})
    monkeypatch.setattr(main, "progressive_competitor_search",
                        lambda *a, **k: ([], [{"Link": "https://rival.com/"}], ["log"], "msg"))
    monkeypatch.setattr(main, "analyze_venue", lambda u, k, t=False: {"Venue Name": "Rival", "URL": u, "SEO Score": 60})
    monkeypatch.setattr(main, "generate_content_brief", lambda *a: {})
    monkeypatch.setattr(main, "_google_positions", lambda *a: None)

    def boom(*a):
        raise RuntimeError("Gemini exploded with SECRET")
    monkeypatch.setattr(main, "generate_ai_executive_summary", boom)
    req = CompetitorsRequest(url="https://example.com/", keyword="kw")
    out = asyncio.run(main.competitors(req, SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"), headers={})))
    d = out.model_dump()
    assert d["ai_summary"] is None and d["ai_summary_error"] == "unavailable"
    assert d["search_location"] == {"gl": "us", "hl": "en", "label": "United States"}
    assert "_x_robots_tag" not in d["primary"] and "SECRET" not in str(d)
    assert d["competitors"][0]["SERP Rank"] == "unknown"


def test_security_headers_still_sent(client):
    r = client.get("/jobs/does-not-exist")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"
