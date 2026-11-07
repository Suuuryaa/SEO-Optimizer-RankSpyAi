"""End-to-end through the HTTP API: POST /jobs/analyze then poll GET /jobs/{id}."""
import time

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from conftest import FakeResponse, fixture_html


def _poll(c, jid):
    for _ in range(200):
        out = c.get(f"/jobs/{jid}").json()
        if out["status"] in ("done", "error"):
            return out
        time.sleep(0.02)
    pytest.fail("job never finished")


@pytest.fixture
def api(public_dns, monkeypatch):
    import main
    import net_safety
    import seo_utils
    html = fixture_html("noindex_page.html")
    monkeypatch.setattr(main, "get_page_soup", lambda u: (BeautifulSoup(html, "lxml"), html))
    monkeypatch.setattr(main, "get_page_meta", lambda u: {"final_url": u, "http_status": 200,
                                                          "x_robots_tag": None, "content_type": "text/html"})
    monkeypatch.setattr(seo_utils, "robots_txt_allows", lambda u, ua="Googlebot": True)
    monkeypatch.setattr(main, "check_and_consume",
                        lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(net_safety.requests, "get", lambda url, **k: FakeResponse(
        200, b"User-agent: GPTBot\nDisallow: /\n", {"Content-Type": "text/plain"}))
    monkeypatch.setattr(main, "_JOBS", {})
    with TestClient(main.app) as c:
        yield c


def test_analyze_job_contract(api):
    r = api.post("/jobs/analyze", json={"url": "https://example.com/blog/seo-basics/", "keyword": "seo", "geo": True})
    assert r.status_code == 202
    out = _poll(api, r.json()["job_id"])
    assert out["status"] == "done", out
    res = out["result"]
    for key in ("scoring_version", "seo_score", "seo_score_uncapped", "indexability", "final_url", "http_status",
                "has_title", "has_meta_description", "keyword_stuffing", "keyword_match", "cached", "cached_at"):
        assert key in res, key
    assert res["scoring_version"] == "1.1" and res["cached"] is False
    assert res["indexability"]["indexable"] is False and res["seo_score"] <= 20
    assert "semantic" not in res and not any(k.startswith("_") for k in res)
    geo = res["geo_score"]
    assert geo["geo_version"] == "1.1" and "snippet_controls" in geo
    assert all("category" in c for c in geo["crawlers"]["crawlers"])
    assert len(geo["crawlers"]["raw_robots"]) <= 5000


def test_fetch_error_job_has_error_kind(api, monkeypatch):
    import main
    from seo_utils import FetchError

    def boom(u):
        raise FetchError("unreachable", "We couldn't find that domain.")
    monkeypatch.setattr(main, "get_page_soup", boom)
    monkeypatch.setattr(main, "refund", lambda: None)
    r = api.post("/jobs/analyze", json={"url": "https://example.com/", "keyword": "seo"})
    out = _poll(api, r.json()["job_id"])
    assert out["status"] == "error" and out["error_kind"] == "unreachable" and out["status_code"] == 422


def test_private_url_rejected_at_validation(api, dns):
    dns["evil.test"] = ["127.0.0.1"]
    for url in ("http://evil.test/", "http://169.254.169.254/", "http://[::ffff:127.0.0.1]/"):
        assert api.post("/jobs/analyze", json={"url": url}).status_code == 422
