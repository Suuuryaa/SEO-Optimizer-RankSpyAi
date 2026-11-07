"""B10 — GEO accuracy: Protego per-path, search vs training bots, llms.txt weight, snippets."""
import pytest
from bs4 import BeautifulSoup

from conftest import FakeResponse


@pytest.fixture
def robots(public_dns, monkeypatch):
    import net_safety

    def set_body(text):
        monkeypatch.setattr(net_safety.requests, "get",
                            lambda url, **k: FakeResponse(200, text.encode(), {"Content-Type": "text/plain"}))
    return set_body


def _status(out, name):
    return next(c for c in out["crawlers"] if c["name"] == name)


def test_specific_group_overrides_star(robots):
    import geo_utils
    robots("User-agent: *\nDisallow: /\n\nUser-agent: GPTBot\nAllow: /\n")
    out = geo_utils.check_ai_crawlers("https://example.com/page")
    assert _status(out, "GPTBot")["status"] == "allowed"
    assert _status(out, "OAI-SearchBot")["status"] == "blocked"


def test_blocking_training_bots_costs_nothing(robots):
    import geo_utils
    robots("Sitemap: https://example.com/sitemap.xml\n"
           "User-agent: GPTBot\nDisallow: /\n\nUser-agent: ClaudeBot\nDisallow: /\n\n"
           "User-agent: Google-Extended\nDisallow: /\n")
    out = geo_utils.check_ai_crawlers("https://example.com/")
    assert out["score"] == 100
    assert _status(out, "GPTBot")["status"] == "blocked" and _status(out, "GPTBot")["category"] == "training"
    assert _status(out, "Googlebot")["category"] == "search"


def test_blank_line_between_ua_and_disallow(robots):
    import geo_utils
    robots("Sitemap: https://example.com/s.xml\nUser-agent: PerplexityBot\n\nDisallow: /\n")
    out = geo_utils.check_ai_crawlers("https://example.com/")
    assert _status(out, "PerplexityBot")["status"] == "blocked"
    assert out["score"] == 85


def test_per_path(robots):
    import geo_utils
    robots("Sitemap: https://example.com/s.xml\nUser-agent: *\nDisallow: /private/\n")
    blocked = geo_utils.check_ai_crawlers("https://example.com/private/x")
    allowed = geo_utils.check_ai_crawlers("https://example.com/public")
    assert _status(blocked, "Googlebot")["status"] == "blocked"
    assert _status(allowed, "Googlebot")["status"] == "allowed"
    # all 8 search bots blocked: 5*15 + 3*5 = 90 lost
    assert blocked["score"] == 10 and allowed["score"] == 100


def test_llmstxt_weight_zero_and_renormalised():
    import geo_utils
    a = geo_utils.calculate_geo_score(80, 80, 80, llmstxt_exists=False, has_schema=True)
    b = geo_utils.calculate_geo_score(80, 80, 80, llmstxt_exists=True, has_schema=True)
    assert a["score"] == b["score"]
    assert a["breakdown"]["llmstxt"]["weight"] == 0
    assert abs(sum(v["weight"] for v in a["breakdown"].values()) - 1) < 0.001
    assert a["geo_version"] == "1.1"
    full = geo_utils.calculate_geo_score(100, 100, 100, llmstxt_exists=False, has_schema=True)
    assert full["score"] == 100


def test_snippet_controls():
    import geo_utils
    soup = BeautifulSoup('<html><head><meta name="robots" content="max-snippet:0"></head>'
                         '<body><p data-nosnippet>x</p><span data-nosnippet>y</span></body></html>', "lxml")
    out = geo_utils.check_snippet_controls(soup, "googlebot: nosnippet")
    assert out["snippet_controls"] == {"nosnippet": True, "max_snippet": 0, "data_nosnippet_count": 2}
    assert out["recommendations"] and out["recommendations"][0]["priority"] == "HIGH"
    clean = geo_utils.check_snippet_controls(BeautifulSoup("<html></html>", "lxml"))
    assert clean["snippet_controls"] == {"nosnippet": False, "max_snippet": None, "data_nosnippet_count": 0}
    assert clean["recommendations"] == []
