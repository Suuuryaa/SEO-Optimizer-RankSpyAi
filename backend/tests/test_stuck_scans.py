"""A slow or blocking competitor can't stall a comparison, rivals never use the
hidden browser, and a scan that times out on our side gives the free scan back."""
import asyncio
import time
from types import SimpleNamespace


def _setup(monkeypatch, venue):
    import main
    monkeypatch.setattr(main, "check_and_consume", lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "active_keys", lambda u=None: {"serper": "s", "gemini": "", "pagespeed": "", "scraper_api": "", "zenrows": ""})
    monkeypatch.setattr(main, "_full_seo_analysis", lambda u, k, keys: {
        "title": "Mine", "seo_score": 50, "keyword_count": 1, "word_count": 400, "missing_alt": 0,
        "_soup": None, "_text": "", "_x_robots_tag": None})
    monkeypatch.setattr(main, "progressive_competitor_search", lambda *a, **k: (
        [], [{"Link": "https://slow.example/"}, {"Link": "https://fast.example/"}], ["log"], "msg"))
    monkeypatch.setattr(main, "analyze_venue", venue)
    monkeypatch.setattr(main, "generate_content_brief", lambda *a: {})
    monkeypatch.setattr(main, "_google_positions", lambda *a, **k: None)
    return main


def test_slow_competitor_is_capped_and_others_still_scored(public_dns, monkeypatch):
    calls = []

    def venue(u, k, t=False, allow_browser=True):
        calls.append(allow_browser)
        if "slow" in u:
            time.sleep(1.5)
        return {"Venue Name": u, "URL": u, "SEO Score": 60}
    main = _setup(monkeypatch, venue)
    monkeypatch.setattr(main, "_COMP_TIMEOUT", 0.3)
    from models import CompetitorsRequest
    t0 = time.time()
    out = asyncio.run(main.competitors(CompetitorsRequest(url="https://example.com/", keyword="kw"),
                                       SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"), headers={})))
    rows = {r["URL"]: r for r in out.model_dump()["competitors"]}
    assert time.time() - t0 < 1.4                       # didn't wait for the slow site
    assert rows["https://slow.example/"]["error_kind"] == "timeout"
    assert rows["https://fast.example/"]["SEO Score"] == 60
    assert calls and not any(calls)                     # rivals never use the hidden browser


def test_scan_timeout_gives_the_free_scan_back(monkeypatch):
    import main
    refunded = []
    monkeypatch.setattr(main, "_JOB_TIMEOUT", 0.05)
    monkeypatch.setattr(main, "_refund", lambda gate, exc=None: refunded.append(gate))

    async def scan():
        main._current_job.get()["gate"] = {"pooled": True, "personal": "compare"}
        await asyncio.sleep(1)
    job = {"id": "j", "status": "queued", "steps": []}
    asyncio.run(main._run_job(job, scan))
    assert job["error_kind"] == "scan_timeout" and "given back" in job["error"]
    assert refunded == [{"pooled": True, "personal": "compare"}]


def test_server_error_gives_the_free_scan_back(monkeypatch):
    import main
    refunded = []
    monkeypatch.setattr(main, "_refund", lambda gate, exc=None: refunded.append(gate))

    async def scan():
        main._current_job.get()["gate"] = {"pooled": True}
        raise RuntimeError("bug")
    job = {"id": "j", "status": "queued", "steps": []}
    asyncio.run(main._run_job(job, scan))
    assert job["status"] == "error" and refunded == [{"pooled": True}]


def test_competitor_scan_skips_browser_render(monkeypatch):
    import leaderboard_utils as lu
    from bs4 import BeautifulSoup
    seen = {}
    monkeypatch.setattr(lu, "get_page_soup", lambda u, allow_browser=True: (seen.setdefault("ab", allow_browser),
                        (BeautifulSoup("<html><title>x</title><body>hi</body></html>", "lxml"), ""))[1])
    import seo_utils
    monkeypatch.setattr(seo_utils, "render_page_html", lambda *a, **k: (_ for _ in ()).throw(AssertionError("rendered")))
    row = lu.analyze_venue("https://rival.example/", "kw", True, False)
    assert seen["ab"] is False and row.get("error_kind") == "unreadable"


def test_stealthy_fetch_no_challenge_solving():
    import inspect
    import seo_utils
    src = inspect.getsource(seo_utils._fetch_with_stealthy)
    assert "solve_cloudflare=True" not in src and "retries=1" in src and "timeout=20000" in src
