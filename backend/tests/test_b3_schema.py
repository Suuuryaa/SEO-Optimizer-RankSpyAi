"""B3 — JSON-LD / structured data detection and non-mutating text extraction."""
from bs4 import BeautifulSoup

from conftest import fixture_html


def test_get_text_content_does_not_mutate():
    import seo_utils
    html = fixture_html("yoast_blog.html")
    soup = BeautifulSoup(html, "lxml")
    before = len(soup.find_all("script"))
    text = seo_utils.get_text_content(soup)
    assert len(soup.find_all("script")) == before
    assert "@graph" not in text           # script content is not page text
    assert "SEO Basics: A Beginner" not in text   # <head> title is not body text
    assert "Why SEO matters" in text


def test_yoast_graph_types():
    import seo_utils
    s = seo_utils.detect_schema_markup(BeautifulSoup(fixture_html("yoast_blog.html"), "lxml"))
    for t in ("WebPage", "Organization", "Article", "BlogPosting", "BreadcrumbList"):
        assert t in s["json_ld"]


def test_full_analysis_has_schema_yoast(analyse):
    out = analyse("yoast_blog.html")
    assert out["technical_seo"]["has_schema"] is True
    assert "WebPage" in out["technical_seo"]["schema_types"]["json_ld"]
    assert "Organization" in out["technical_seo"]["schema_types"]["json_ld"]
    assert not any("structured data" in r["issue"] for r in out["recommendations"])


def test_full_analysis_has_schema_list_shaped(analyse):
    out = analyse("list_jsonld.html", keyword="food")
    assert out["technical_seo"]["has_schema"] is True
    assert out["technical_seo"]["schema_types"]["json_ld"] == ["Restaurant", "Menu"]


def test_invalid_jsonld_keeps_microdata(analyse):
    out = analyse("invalid_jsonld_microdata.html", keyword="shop")
    assert out["technical_seo"]["has_schema"] is True
    assert out["technical_seo"]["schema_types"]["microdata"] == ["https://schema.org/Store"]


def test_leaderboard_row_sees_schema(public_dns, monkeypatch):
    import leaderboard_utils
    html = fixture_html("yoast_blog.html")
    monkeypatch.setattr(leaderboard_utils, "get_page_soup", lambda u: (BeautifulSoup(html, "lxml"), html))
    row = leaderboard_utils.analyze_venue("https://example.com/blog/seo-basics/", "seo")
    assert row["Schema"] == "✓"
