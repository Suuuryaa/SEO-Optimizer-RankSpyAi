"""B5 — indexability gate, final URL, non-HTML responses."""
import pytest
from bs4 import BeautifulSoup

from conftest import FakeResponse


def test_noindex_caps_score(analyse):
    out = analyse("noindex_page.html", url="https://example.com/blog/seo-basics/")
    assert out["indexability"]["indexable"] is False
    assert [r["code"] for r in out["indexability"]["reasons"]] == ["meta_noindex"]
    assert out["seo_score"] <= 20
    assert out["seo_score_uncapped"] > 20
    assert "CRITICAL" in out["recommendations"][0]["priority"]
    assert "noindex" in out["recommendations"][0]["issue"]


def test_indexable_page(analyse):
    out = analyse("yoast_blog.html", url="https://example.com/blog/seo-basics/")
    assert out["indexability"] == {"indexable": True, "reasons": [],
                                   "canonical_url": "https://example.com/blog/seo-basics/"}
    assert out["seo_score"] == out["seo_score_uncapped"]


def test_canonical_normalisation_and_elsewhere(analyse):
    # http + www + no trailing slash is the same page as the canonical
    out = analyse("yoast_blog.html", url="http://www.example.com/blog/seo-basics")
    assert out["indexability"]["indexable"] is True
    out = analyse("yoast_blog.html", url="https://example.com/other-page/")
    assert [r["code"] for r in out["indexability"]["reasons"]] == ["canonical_elsewhere"]


def test_x_robots_and_robots_txt(analyse):
    out = analyse("yoast_blog.html", url="https://example.com/blog/seo-basics/",
                  meta={"final_url": "https://example.com/blog/seo-basics/", "http_status": 200,
                        "x_robots_tag": "googlebot: noindex", "content_type": "text/html"},
                  robots_allows=False)
    codes = [r["code"] for r in out["indexability"]["reasons"]]
    assert codes == ["x_robots_noindex", "robots_txt_blocked"]
    assert out["http_status"] == 200


def test_www_internal_links_counted(analyse):
    # yoast fixture links to https://www.example.com/blog/ and relative paths
    out = analyse("yoast_blog.html", url="https://example.com/blog/seo-basics/")
    assert out["internal_links"] == 5
    assert out["external_links"] == 1


def test_https_from_final_url(analyse):
    out = analyse("yoast_blog.html", url="http://example.com/blog/seo-basics/",
                  meta={"final_url": "https://example.com/blog/seo-basics/", "http_status": 200,
                        "x_robots_tag": None, "content_type": "text/html"})
    assert out["technical_seo"]["https_enabled"] is True
    assert out["final_url"] == "https://example.com/blog/seo-basics/"


def test_robots_txt_allows_with_protego(public_dns, monkeypatch):
    import net_safety
    import seo_utils
    seo_utils._ROBOTS_CACHE.clear()
    monkeypatch.setattr(net_safety.requests, "get", lambda url, **k: FakeResponse(
        200, b"User-agent: Googlebot\nDisallow: /private/\n", {"Content-Type": "text/plain"}))
    assert seo_utils.robots_txt_allows("https://example.com/private/x") is False
    assert seo_utils.robots_txt_allows("https://example.com/public") is True
    seo_utils._ROBOTS_CACHE.clear()


def test_robots_fetch_failure_is_indexable(public_dns, monkeypatch):
    import net_safety
    import seo_utils
    seo_utils._ROBOTS_CACHE.clear()

    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(net_safety.requests, "get", boom)
    assert seo_utils.robots_txt_allows("https://example.com/x") is True
    seo_utils._ROBOTS_CACHE.clear()


def test_non_html_is_fetch_error(public_dns, monkeypatch):
    import seo_utils
    monkeypatch.setattr(seo_utils.requests, "get",
                        lambda url, **k: FakeResponse(200, b"%PDF-1.4" + b"x" * 1000, {"Content-Type": "application/pdf"}))
    with pytest.raises(seo_utils.FetchError) as ei:
        seo_utils._fetch_page.__wrapped__("https://example.com/file.pdf")
    assert ei.value.kind == "not_html" and "application/pdf" in str(ei.value)


def test_page_meta_cached(public_dns, monkeypatch):
    import seo_utils
    html = b"<html><head><title>t</title></head><body>" + b"word " * 200 + b"</body></html>"
    monkeypatch.setattr(seo_utils.requests, "get", lambda url, **k: FakeResponse(
        200, html, {"Content-Type": "text/html; charset=utf-8", "X-Robots-Tag": "noindex"}))
    seo_utils.get_page_soup("https://example.com/m")
    meta = seo_utils.get_page_meta("https://example.com/m")
    assert meta == {"final_url": "https://example.com/m", "http_status": 200,
                    "x_robots_tag": "noindex", "content_type": "text/html; charset=utf-8"}
    assert seo_utils.page_cached("https://example.com/m")
