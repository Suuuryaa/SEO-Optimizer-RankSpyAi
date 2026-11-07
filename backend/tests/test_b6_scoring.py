"""B6 — keyword matching and scoring correctness pack (v1.1)."""
import pytest

from seo_utils import match_keyword, count_keyword, count_words, keyword_density


def test_matcher_word_boundaries():
    assert match_keyword("Best restaurants in Seoul", "seo") is None
    assert count_keyword("Seoul seoul SEOUL", "seo") == 0


def test_matcher_plural_and_case():
    assert match_keyword("The Best Coffee Shop in Town", "coffee shops") == "exact"
    assert match_keyword("Coffee shops near me", "coffee shop") == "exact"


def test_matcher_all_tokens():
    assert match_keyword("Best Pizza in London", "best pizza london") == "all_tokens"
    assert match_keyword("Best Pizza in Paris", "best pizza london") is None


def test_matcher_hyphen_equals_space():
    # Documented behaviour: punctuation and hyphens are treated as spaces.
    assert match_keyword("Grow your e commerce store", "e-commerce") == "exact"
    assert match_keyword("Grow your e-commerce store", "e commerce") == "exact"


def test_matcher_cjk_substring():
    assert match_keyword("東京のおすすめラーメン店", "東京") == "exact"
    assert count_keyword("東京と東京", "東京") == 2


def test_matcher_nfkc():
    assert match_keyword("ＳＥＯ guide", "seo") == "exact"     # full-width letters


def test_count_words_cjk():
    assert count_words("hello world") == 2
    assert count_words("東京都") == 2          # 3 chars / 2, rounded up
    assert count_words("SEO 東京 guide") == 3
    assert count_words("— | hello") == 1      # punctuation-only tokens don't count


def test_density_multiword():
    text = " ".join(["pizza london"] + ["word"] * 98)   # 100 words, 2 of them keyword
    assert keyword_density(text, "pizza london") == 2.0


def test_stuffing_flag_and_zero_points(analyse):
    out = analyse("stuffed_page.html", url="https://example.com/shoes", keyword="cheap shoes")
    assert out["keyword_density"] > 3.5
    assert out["keyword_stuffing"] is True
    assert any("stuffing" in r["issue"] for r in out["recommendations"])


def test_missing_title_and_meta(analyse):
    out = analyse("no_title.html", url="https://example.com/bakery", keyword="sourdough bread")
    assert out["title"] == "" and out["has_title"] is False
    assert out["meta_description"] == "" and out["has_meta_description"] is False
    assert out["keyword_in_title"] is False
    issues = {r["issue"]: r["priority"] for r in out["recommendations"]}
    assert "CRITICAL" in issues["Missing title"]
    assert "HIGH" in issues["Missing meta description"]
    assert "Target keyword missing from title" not in issues


def test_missing_h1_one_task(analyse):
    out = analyse("no_title.html", url="https://example.com/bakery", keyword="sourdough bread")
    h1_issues = [r for r in out["recommendations"] if "H1" in r["issue"]]
    assert len(h1_issues) == 1 and h1_issues[0]["issue"] == "No H1 heading found"


def test_word_count_severity():
    from scoring import calculate_seo_score

    def prio(wc):
        _, recs, _, _ = calculate_seo_score("t" * 40, "m" * 130, ["h"], 5, wc, 0, True, True, True, 40, 130,
                                            internal_links_count=5, has_schema=True, keyword_density_pct=1.0)
        r = [x for x in recs if "words" in x["issue"] or "content" in x["issue"].lower()]
        return r[0]["priority"] if r else None

    assert "HIGH" in prio(100)
    assert "MEDIUM" in prio(200)
    assert "LOW" in prio(400) and "LOW" in prio(1200)
    assert prio(2000) is None
    for wc in (10, 100, 200, 400):
        assert "CRITICAL" not in (prio(wc) or "")


def test_density_points():
    from scoring import calculate_seo_score

    def run(d, kc=10):
        score, recs, _, stuffing = calculate_seo_score("t" * 40, "m" * 130, ["h"], kc, 2000, 0, True, True, True,
                                                       40, 130, internal_links_count=5, has_schema=True,
                                                       keyword_density_pct=d)
        return score, stuffing

    assert run(1.0) == (100, False)
    assert run(3.0) == (97, False)
    assert run(13.0) == (92, True)       # 0 density points


def test_all_tokens_half_points():
    from scoring import calculate_seo_score
    full, *_ = calculate_seo_score("t" * 40, "m" * 130, ["h"], 10, 2000, 0, "exact", "exact", "exact", 40, 130,
                                   internal_links_count=5, has_schema=True, keyword_density_pct=1.0)
    half, *_ = calculate_seo_score("t" * 40, "m" * 130, ["h"], 10, 2000, 0, "all_tokens", "all_tokens", "all_tokens",
                                   40, 130, internal_links_count=5, has_schema=True, keyword_density_pct=1.0)
    assert full - half == (15 - 7) + (8 - 4) + (10 - 5)


def test_sanitize_input_not_escaped():
    import main
    assert main._sanitize_input("fish & chips <b>x</b>\x07") == "fish & chips x"


def test_jp_page_no_render_needed(analyse):
    called = []
    out = analyse("jp_page.html", url="https://example.jp/", keyword="東京 ラーメン",
                  render=lambda u: called.append(u))
    assert out["word_count"] > 150 and not called
    assert out["keyword_in_title"] is True


# Golden scores for scoring v1.1. If scoring changes on purpose, bump
# SCORING_VERSION and update these numbers.
GOLDEN = [
    ("local_service.html", "https://example.com/plumber-leeds", "emergency plumber", None),
    ("yoast_blog.html", "https://example.com/blog/seo-basics/", "seo", None),
    ("jp_page.html", "https://example.jp/", "東京 ラーメン", None),
    ("stuffed_page.html", "https://example.com/shoes", "cheap shoes", None),
    ("no_title.html", "https://example.com/bakery", "sourdough bread", None),
]
GOLDEN_SCORES = {
    "local_service.html": 90,
    "yoast_blog.html": 91,
    "jp_page.html": 59,
    "stuffed_page.html": 68,
    "no_title.html": 20,
}


@pytest.mark.parametrize("name,url,kw,_", GOLDEN)
def test_golden(analyse, name, url, kw, _):
    out = analyse(name, url=url, keyword=kw)
    assert out["scoring_version"] == "1.1"
    assert out["seo_score"] == GOLDEN_SCORES[name]
