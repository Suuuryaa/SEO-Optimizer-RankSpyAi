"""Competitors = the business's own main rivals (not whoever ranks for the keyword)."""
import json


def _reply(monkeypatch, obj):
    import ai.gemini as g
    monkeypatch.setattr(g, "generate_text", lambda *a, **k: json.dumps(obj))


def test_marketplace_rivals_kept_and_dead_sites_dropped(monkeypatch):
    import competitor_utils as cu
    _reply(monkeypatch, {"business": "Indian online marketplace", "home_country": "IN", "competitors": [
        {"name": "Amazon India", "domain": "amazon.in"},
        {"name": "Meesho", "domain": "www.meesho.com"},
        {"name": "Craftsvilla", "domain": "craftsvilla.com"},        # dead
        {"name": "Flipkart", "domain": "flipkart.com"},              # the site itself
        {"name": "Wikipedia", "domain": "wikipedia.org"},            # not a business
        {"name": "Snapdeal", "domain": "snapdeal.com"},
    ]})
    monkeypatch.setattr(cu, "_site_alive", lambda d: d != "craftsvilla.com")
    rivals, home = cu.find_brand_rivals("https://www.flipkart.com/", "key", "Flipkart", "")
    assert home == "IN"
    assert [r["domain"] for r in rivals] == ["amazon.in", "meesho.com", "snapdeal.com"]
    assert rivals[0]["link"] == "https://amazon.in/"


def test_limit_and_bad_reply(monkeypatch):
    import competitor_utils as cu
    monkeypatch.setattr(cu, "_site_alive", lambda d: True)
    _reply(monkeypatch, {"home_country": "US", "competitors": [{"name": f"B{i}", "domain": f"b{i}.com"} for i in range(12)]})
    rivals, _ = cu.find_brand_rivals("https://reebok.com/", "key")
    assert len(rivals) == 8
    import ai.gemini as g
    monkeypatch.setattr(g, "generate_text", lambda *a, **k: "not json")
    assert cu.find_brand_rivals("https://reebok.com/", "key") == ([], None)
    assert cu.find_brand_rivals("https://reebok.com/", "") == ([], None)


def test_home_country_location():
    from location_utils import location_for_country, country_is_from_domain
    loc = location_for_country("IN")
    assert loc["serper_gl"] == "in" and loc["country_name"] == "India"
    assert location_for_country("ZZ") is None
    assert country_is_from_domain("https://shop.co.nz/") is True
    assert country_is_from_domain("https://www.flipkart.com/") is False


def test_google_seo_check_parses_and_fails_soft(monkeypatch):
    import google_check

    class R:
        def __init__(self, code, body): self.status_code, self._b = code, body
        def json(self): return self._b
    body = {"lighthouseResult": {"finalDisplayedUrl": "https://www.nike.in/",
                                 "categories": {"seo": {"score": 0.92}},
                                 "audits": {"document-title": {"score": 1}, "meta-description": {"score": 0},
                                            "is-crawlable": {"score": 1}}}}
    monkeypatch.setattr(google_check.requests, "get", lambda *a, **k: R(200, body))
    out = google_check.google_seo_check("https://www.nike.com/", "k")
    assert out == {"seo_score": 92, "checked_url": "https://www.nike.in/", "title_ok": True,
                   "meta_ok": False, "crawlable": True}
    monkeypatch.setattr(google_check.requests, "get", lambda *a, **k: R(400, {"error": {}}))
    assert google_check.google_seo_check("https://www.adidas.com/", "k") is None
    assert google_check.google_seo_check("https://x.com/", "") is None


def test_local_seo_phone_formats():
    from bs4 import BeautifulSoup
    from ai.local_seo import _has_phone
    assert _has_phone(None, "Call 07 834 9293 today")
    assert _has_phone(None, "(02) 9876 5432") and _has_phone(None, "555-123-4567")
    assert _has_phone(BeautifulSoup('<a href="tel:078349293">Call</a>', "lxml"), "")
    assert not _has_phone(None, "Awards 2022 2023 2024, $1,234.56, 2022-04-06, order #12345678")


def test_h1_keeps_spaces_between_parts():
    from bs4 import BeautifulSoup
    from seo_utils import get_h1_tags
    assert get_h1_tags(BeautifulSoup("<h1>Emergency Dental<br>Services<span>in Hamilton</span></h1>", "lxml")) == \
        ["Emergency Dental Services in Hamilton"]


def test_meta_suggestions_use_gemini_and_fall_back(monkeypatch):
    import ai.gemini as g
    from ai import meta_gen
    monkeypatch.setattr(meta_gen, "_hf_summarize", lambda *a, **k: None)
    monkeypatch.setattr(g, "generate_text", lambda *a, **k: json.dumps({
        "title": "Emergency Dentist Hamilton | City Dental",
        "description": "Same-day emergency dental care in Hamilton, open 7 days. Call our team for fast relief from tooth pain and broken teeth."}))
    out = meta_gen.generate_meta_suggestions("Home", "", ["Welcome"], "Menu Skip to main content. We fix teeth.",
                                             "emergency dentist hamilton", "https://x.co.nz/", "key")
    assert out["ai_written"] and out["suggested_title"].startswith("Emergency Dentist Hamilton")
    assert "Skip to" not in out["suggested_meta"]
    # no key: rule-based, and menu text is skipped
    out = meta_gen.generate_meta_suggestions("Home", "", [], "Menu Skip to main content and more navigation here. "
                                             "We repair broken teeth the same day across Hamilton.", "dentist", "https://x.co.nz/")
    assert not out["ai_written"] and "Skip to" not in out["suggested_meta"]


def test_meta_title_never_cut_mid_word():
    from ai.meta_gen import _fit
    assert _fit("Emergency Dentist Hamilton | Hamilton Dental Emergency Centre", 60) == "Emergency Dentist Hamilton"
    assert _fit("Short title", 60) == "Short title"
    out = _fit("A very long description that keeps going and going past the limit here", 40)
    assert len(out) <= 40 and not out.endswith("goin")
