"""Text-in-images: image picking, merging the two engines, and the fixes it reports."""
from bs4 import BeautifulSoup

import image_text as it


class _Img:
    def __init__(self, w, h):
        self.size = (w, h)


def _page(html):
    return BeautifulSoup(html, "lxml")


def _fake(monkeypatch, ocr_by_url, gem_by_index, sizes=None, gem_err=None):
    sizes = sizes or {}

    def download(c):
        w, h = sizes.get(c["url"], (1200, 600))
        return {**c, "image": _Img(w, h), "width": w, "height": h, "_url": c["url"]}

    monkeypatch.setattr(it, "_download", download)
    monkeypatch.setattr(it, "_ocr", lambda im: (ocr_by_url.get(id(im), []), None))
    # OCR is keyed by the fake image object; map URL -> object after download
    real_download = download

    def download2(c):
        d = real_download(c)
        ocr_by_url[id(d["image"])] = ocr_by_url.get(c["url"], [])
        return d

    monkeypatch.setattr(it, "_download", download2)
    monkeypatch.setattr(it, "_gemini", lambda imgs, key: (gem_by_index, gem_err))


def test_candidates_skip_svg_data_and_pixels_and_read_srcset_and_backgrounds():
    soup = _page("""
      <img src="data:image/png;base64,xx"><img src="/logo.svg">
      <img src="/px.gif" width="1" height="1">
      <img srcset="/a-400.jpg 400w, /a-1200.jpg 1200w, /a-3000.jpg 3000w" alt="Hero">
      <div style="background-image: url('/banner.jpg')"></div>""")
    urls = [c["url"] for c in it._candidate_images(soup, "https://ex.com/page")]
    assert urls == ["https://ex.com/a-1200.jpg", "https://ex.com/banner.jpg"]


def test_merge_prefers_gemini_and_adds_only_confident_new_ocr_lines():
    m = it._merge([("24/7 Emergency Plumber", 0.99), ("Free quotes today", 0.95), ("xq", 0.97)],
                  "24/7 Emergency Plumber")
    assert m["source"] == "both"
    assert "Free quotes today" in m["text"] and "xq" not in m["text"]


def test_merge_without_gemini_uses_confident_ocr_only():
    m = it._merge([("Call 0800 123 456", 0.98), ("blurry", 0.65)], None)
    assert m["source"] == "ocr" and m["text"] == "Call 0800 123 456"


def test_keyword_only_in_image_is_flagged_high(monkeypatch):
    soup = _page('<img src="/hero.jpg"><p>We fix pipes.</p>')
    _fake(monkeypatch, {"https://ex.com/hero.jpg": [("Emergency Plumber Auckland", 0.99)]},
          {0: {"text": "Emergency Plumber Auckland", "description": "banner",
               "text_is_message": True, "suggested_alt": "Emergency plumber Auckland banner"}})
    out = it.analyze_image_text(soup, "https://ex.com/", "emergency plumber auckland", "We fix pipes.", "k")
    assert out["keyword_only_in_images"] is True
    assert out["recommendations"][0]["priority"].endswith("HIGH")
    # no alt on a banner: alt fix uses Gemini's suggestion, not the raw text
    alt_rec = [r for r in out["recommendations"] if "alt text" in r["issue"]][0]
    assert "Emergency plumber Auckland banner" in alt_rec["fix"]


def test_keyword_also_in_page_text_is_not_flagged(monkeypatch):
    soup = _page('<img src="/hero.jpg" alt="Emergency plumber Auckland">')
    _fake(monkeypatch, {}, {0: {"text": "Emergency Plumber Auckland", "text_is_message": True}})
    out = it.analyze_image_text(soup, "https://ex.com/", "emergency plumber auckland",
                                "Your emergency plumber Auckland, 24/7.", "k")
    assert out["keyword_in_images"] is True and out["keyword_only_in_images"] is False
    assert out["recommendations"] == []


def test_phone_flagged_once_and_only_for_message_images_and_tel_links_count(monkeypatch):
    soup = _page('<img src="/flyer.jpg" alt="Call us"><img src="/van.jpg" alt="Our van">')
    gem = {0: {"text": "Call 0800 123 456 | 0800123456", "text_is_message": True},
           1: {"text": "0800 999 888", "text_is_message": False}}
    _fake(monkeypatch, {}, gem)
    out = it.analyze_image_text(soup, "https://ex.com/", "", "Welcome", "k")
    assert out["phones_only_in_images"] == ["0800 123 456"]
    assert out["images"][0]["issues"].count("phone_only_in_image") == 1
    assert out["images"][1]["issues"] == []

    soup2 = _page('<img src="/flyer.jpg" alt="Call us"><a href="tel:0800123456">Call</a>')
    _fake(monkeypatch, {}, {0: gem[0]})
    assert it.analyze_image_text(soup2, "https://ex.com/", "", "Welcome", "k")["phones_only_in_images"] == []


def test_photos_with_incidental_text_get_no_alt_advice(monkeypatch):
    soup = _page('<img src="/team.jpg" alt="Our team">')
    _fake(monkeypatch, {}, {0: {"text": "MR PLUMBER | 24 HOURS | CUSTOMER PARKING", "text_is_message": False}})
    out = it.analyze_image_text(soup, "https://ex.com/", "", "", "k")
    assert out["images"][0]["issues"] == [] and out["recommendations"] == []


def test_alt_mismatch_only_when_alt_shares_no_words(monkeypatch):
    soup = _page('<img src="/logo.jpg" alt="Punjabi Rasoi"><img src="/promo.jpg" alt="photo1">')
    _fake(monkeypatch, {}, {0: {"text": "Punjabi Rasoi | Authentic North Indian Kitchen", "text_is_message": True},
                            1: {"text": "Half price curries every Tuesday", "text_is_message": True}})
    out = it.analyze_image_text(soup, "https://ex.com/", "", "", "k")
    assert out["images"][0]["issues"] == []
    assert out["images"][1]["issues"] == ["alt_does_not_match"]


def test_gemini_down_still_works_with_ocr(monkeypatch):
    soup = _page('<img src="/promo.jpg">')
    _fake(monkeypatch, {"https://ex.com/promo.jpg": [("Half price curries every Tuesday night", 0.97)]},
          {}, gem_err="quota")
    out = it.analyze_image_text(soup, "https://ex.com/", "", "", "k")
    assert out["engines"]["gemini"] == "quota"
    assert out["images"][0]["source"] == "ocr"
    assert "text_without_alt" in out["images"][0]["issues"]


def test_small_images_are_skipped(monkeypatch):
    soup = _page('<img src="/icon.png">')
    _fake(monkeypatch, {}, {}, sizes={"https://ex.com/icon.png": (64, 64)})
    # the size filter lives in _download; emulate it returning None for small images
    monkeypatch.setattr(it, "_download", lambda c: None)
    out = it.analyze_image_text(soup, "https://ex.com/", "", "", "k")
    assert out["checked"] == 0 and out["note"]


def test_parse_json_tolerates_fences_and_chatter():
    assert it._parse_json('```json\n{"images": []}\n```') == {"images": []}
    assert it._parse_json('Here you go: {"images": [{"index": 1}]} hope that helps') == {"images": [{"index": 1}]}
    assert it._parse_json("not json") is None


def test_no_alt_mismatch_advice_without_gemini(monkeypatch):
    soup = _page('<img src="/menu.jpg" alt="photo1">')
    _fake(monkeypatch, {"https://ex.com/menu.jpg": [("A feast of fries and drinks raise your glass", 0.97)]},
          {}, gem_err="bad_response")
    out = it.analyze_image_text(soup, "https://ex.com/", "", "", "k")
    assert out["images"][0]["issues"] == []
