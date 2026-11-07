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
