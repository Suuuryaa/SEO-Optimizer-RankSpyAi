"""B9 — Serper accuracy: country targeting, exact host matching, retry policy."""
import pytest

from conftest import FakeResponse


def test_url_matches_host_exact():
    from rank_tracker import url_matches
    assert not url_matches("ample.com", "https://example.com/")
    assert not url_matches("example.com", "https://example.com.au/")
    assert url_matches("example.com", "https://www.example.com/a")
    assert url_matches("https://example.com/shop", "https://example.com/shop/item")
    assert not url_matches("https://example.com/shop", "https://example.com/shopping")
    assert not url_matches("example.com", "https://sub.example.com/")


def test_check_rank_sends_gl_and_finds_position(monkeypatch):
    import rank_tracker
    payloads = []

    def fake_post(url, json=None, headers=None, timeout=None):
        payloads.append(json)
        organic = [{"link": "https://example.com.au/"}, {"link": "https://ample.com/"},
                   {"link": "https://www.example.co.nz/page"}] if json["page"] == 1 else []
        return FakeResponse(200, json_data={"organic": organic})

    monkeypatch.setattr(rank_tracker.requests, "post", fake_post)
    out = rank_tracker.check_rank("https://example.co.nz/", "kw", "key")
    assert out["position"] == 3
    assert payloads[0]["gl"] == "nz" and payloads[0]["hl"] == "en"


def test_serp_links_default_gl_us(monkeypatch):
    import rank_tracker
    payloads = []
    monkeypatch.setattr(rank_tracker.requests, "post",
                        lambda url, json=None, **k: payloads.append(json) or FakeResponse(200, json_data={"organic": []}))
    rank_tracker.serp_organic_links("kw", "key")
    assert payloads[0]["gl"] == "us" and "hl" not in payloads[0]


def test_get_serp_results_no_retry_on_400(monkeypatch):
    import serp_utils
    calls = []
    monkeypatch.setattr(serp_utils.requests, "post",
                        lambda *a, **k: calls.append(k.get("json")) or FakeResponse(400, b"bad"))
    with pytest.raises(Exception):
        serp_utils.get_serp_results("q", "key", {"gl": "gb", "hl": "en"})
    assert len(calls) == 1 and calls[0]["gl"] == "gb" and calls[0]["hl"] == "en"


def test_get_serp_results_retries_5xx(monkeypatch):
    import serp_utils
    calls = []
    monkeypatch.setattr(serp_utils.time, "sleep", lambda s: None)
    seq = [FakeResponse(503), FakeResponse(200, json_data={"organic": [{"link": "x"}]})]
    monkeypatch.setattr(serp_utils.requests, "post", lambda *a, **k: calls.append(1) or seq.pop(0))
    assert serp_utils.get_serp_results("q", "key") == [{"link": "x"}]
    assert len(calls) == 2


def test_no_related_query(monkeypatch):
    import serp_utils
    queries = []
    monkeypatch.setattr(serp_utils, "get_serp_results",
                        lambda q, key, loc=None, **k: queries.append((q, loc)) or [])
    serp_utils.progressive_competitor_search("https://shop.co.uk/", "kw", "key", lambda r, primary_url: [], 3, None)
    assert queries and not any(q.startswith("related:") for q, _ in queries)
    assert all(loc["gl"] == "gb" for _, loc in queries)


def test_country_detection_uses_host_ending():
    from location_utils import get_location_from_url
    assert get_location_from_url("https://www.indeed.com/jobs")["serper_gl"] == "us"
    assert get_location_from_url("https://shop.co.nz/x")["serper_gl"] == "nz"
    assert get_location_from_url("https://example.de/")["serper_hl"] == "de"


def test_google_positions_passes_gl(monkeypatch):
    import main
    import rank_tracker
    seen = {}

    def fake_links(keyword, key, pages=3, gl=None, hl=None):
        seen.update(gl=gl, hl=hl)
        return ["https://www.example.com/", "https://rival.com/"]
    monkeypatch.setattr(rank_tracker, "serp_organic_links", fake_links)
    out = main._google_positions("kw", ["https://example.com/a", "https://ample.com/"], "key", "gb", "en")
    assert seen == {"gl": "gb", "hl": "en"}
    assert out == {"https://example.com/a": 1, "https://ample.com/": None}
