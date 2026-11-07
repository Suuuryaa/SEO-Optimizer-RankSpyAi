"""B11 — one browser at a time, deep crawl output, HF/semantic removal, Gemini penalties."""
import asyncio
import os
import sys
import threading
import time
import types


def test_no_semantic_or_hf_warmup():
    import main
    src = open(os.path.join(os.path.dirname(main.__file__), "main.py")).read()
    assert "semantic_keyword_score" not in src
    assert "warmup" not in src.lower()
    assert not main.app.router.on_startup


def _fake_playwright(monkeypatch, state):
    class Page:
        url = "https://example.com/"
        def route(self, *a): pass
        def goto(self, *a, **k):
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
            time.sleep(0.2)
            state["now"] -= 1
        def wait_for_load_state(self, *a, **k): pass
        def content(self): return "<html><body>" + "word " * 300 + "</body></html>"

    class Browser:
        def new_context(self, **k): return types.SimpleNamespace(new_page=lambda: Page())
        def close(self): pass

    class PW:
        chromium = types.SimpleNamespace(launch=lambda **k: Browser())
        def __enter__(self): return self
        def __exit__(self, *a): return False

    mod = types.ModuleType("playwright.sync_api")
    mod.sync_playwright = lambda: PW()
    monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)


def test_render_one_browser_at_a_time(public_dns, monkeypatch):
    import seo_utils
    state = {"now": 0, "max": 0}
    _fake_playwright(monkeypatch, state)
    results = []
    threads = [threading.Thread(target=lambda u=u: results.append(seo_utils.render_page_html(u)))
               for u in ("https://example.com/a", "https://example.com/b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["max"] == 1
    assert all(results)
    assert seo_utils.page_cached("https://example.com/a")


def test_tier5_skipped_when_browser_busy(public_dns, monkeypatch):
    import seo_utils
    from conftest import FakeResponse
    monkeypatch.setattr(seo_utils, "_STEALTHY_AVAILABLE", True)
    monkeypatch.setattr(seo_utils, "_SCRAPLING_AVAILABLE", False)
    monkeypatch.setattr(seo_utils, "_fetch_with_stealthy", lambda u: (_ for _ in ()).throw(AssertionError("ran")))
    monkeypatch.setattr(seo_utils.requests, "get", lambda url, **k: FakeResponse(403, b"no"))
    assert seo_utils._BROWSER_SLOT.acquire(blocking=False)
    try:
        import pytest
        with pytest.raises(seo_utils.FetchError):
            seo_utils._fetch_page.__wrapped__("https://example.com/")
    finally:
        seo_utils._BROWSER_SLOT.release()


def test_deep_crawl_busy(monkeypatch):
    import deep_crawl
    import seo_utils
    monkeypatch.setattr(deep_crawl, "_SLOT_WAIT", 0.1)
    assert seo_utils._BROWSER_SLOT.acquire(blocking=False)
    try:
        out = asyncio.run(deep_crawl.deep_crawl("https://example.com/"))
    finally:
        seo_utils._BROWSER_SLOT.release()
    assert "busy" in out["error"]


def test_deep_crawl_output_has_no_text(monkeypatch):
    import deep_crawl

    async def fake_crawl(url, max_pages):
        return [{"url": url, "title": "T", "h1": ["H"], "h2": [], "body_text": "one two three"},
                {"url": url + "x", "title": "X", "h1": [], "h2": ["S"], "body_text": "four five"},
                {"url": url + "y", "error": "Couldn't load this page"}]
    monkeypatch.setattr(deep_crawl, "_crawl", fake_crawl)
    out = asyncio.run(deep_crawl.deep_crawl("https://example.com/"))
    assert out["total_words"] == 5
    assert "combined_text" not in out
    assert all("body_text" not in p for p in out["pages_detail"])


def test_analyze_js_mode_keeps_word_count(public_dns, monkeypatch):
    import main
    from models import AnalyzeRequest
    from types import SimpleNamespace
    monkeypatch.setattr(main, "check_and_consume", lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "_full_seo_analysis", lambda u, k, keys: {
        "word_count": 120, "technical_seo": {}, "_soup": None, "_text": ""})

    async def fake_deep(url):
        return {"pages_crawled": 2, "total_words": 5000, "_combined_text": "lots of words"}
    monkeypatch.setattr(main, "deep_crawl", fake_deep)
    monkeypatch.setattr(main, "extract_keyphrases", lambda t: ["kp"])
    out = asyncio.run(main.analyze(AnalyzeRequest(url="https://example.com/", keyword="x", crawl_mode="javascript"),
                                   SimpleNamespace(client=SimpleNamespace(host="1.1.1.1"), headers={})))
    assert out["word_count"] == 120
    assert out["deep_crawl"]["total_words"] == 5000
    assert "_combined_text" not in out["deep_crawl"] and "combined_text" not in out["deep_crawl"]
    assert "semantic" not in out


def test_gemini_penalty_ttls(monkeypatch):
    import ai.gemini as g
    from conftest import FakeResponse
    monkeypatch.setattr(g, "_bad", {})
    monkeypatch.setattr(g, "_candidates", lambda key: ["m404", "m500"])
    monkeypatch.setattr(g.requests, "post", lambda url, **k: FakeResponse(404 if "m404" in url else 503, b"x"))
    try:
        g.generate_text("AIzaKEY", "hi")
    except g.GeminiError:
        pass
    bad = g._bad[g._fp("AIzaKEY")]
    now = time.time()
    assert 5.9 * 3600 < bad["m404"] - now <= 6 * 3600
    assert 4 * 60 < bad["m500"] - now <= 5 * 60
