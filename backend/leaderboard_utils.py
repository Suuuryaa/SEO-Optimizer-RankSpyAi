from seo_utils import (
    get_page_soup,
    get_title,
    get_meta_description,
    get_h1_tags,
    get_text_content,
    count_words,
    count_keyword,
    keyword_density,
    get_links,
    get_images_missing_alt,
    keyword_in_title,
    keyword_in_meta,
    keyword_in_h1,
    title_length,
    meta_description_length,
    check_technical_seo,
    has_schema_markup,
    get_page_meta,
    match_keyword,
    best_h1_match,
    FetchError,
)
from scoring import calculate_seo_score, get_score_band, SCORING_VERSION
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def get_venue_name(url, title):
    """Extract clean brand name from URL domain."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    # Strip www. and country TLDs to get core brand
    domain = domain.replace("www.", "")
    brand = domain.split(".")[0]
    # Capitalize nicely
    brand = brand.replace("-", " ").replace("_", " ").title()
    return brand


# User-safe messages for a competitor page we couldn't scan, by FetchError kind
ROW_ERRORS = {
    "blocked":      "Couldn't scan this site, it blocked our crawler.",
    "not_found":    "Couldn't scan this site, the page returned 'not found'.",
    "server_error": "Couldn't scan this site, it returned a server error.",
    "timeout":      "Couldn't scan this site, it took too long to respond.",
    "unreachable":  "Couldn't scan this site, we couldn't reach it.",
    "not_html":     "Couldn't scan this site, the link isn't a web page.",
    "internal":     "Couldn't scan this site.",
}


def row_error(exc) -> tuple:
    """(user-safe message, error_kind) for an exception raised while scanning a row."""
    kind = getattr(exc, "kind", None) if isinstance(exc, FetchError) else None
    kind = kind if kind in ROW_ERRORS else "internal"
    return ROW_ERRORS[kind], kind


def analyze_venue(url, keyword, include_text=False):
    """
    Comprehensive venue analysis with enhanced scoring.

    Args:
        url (str): Venue URL to analyze
        keyword (str): Target keyword

    Returns:
        dict: Analysis results with all metrics. On failure the row carries a
        user-safe `error` and an `error_kind`.
    """
    try:
        soup, raw_html = get_page_soup(url)
        final_url = (get_page_meta(url) or {}).get("final_url") or url

        title = get_title(soup)
        meta = get_meta_description(soup)
        h1 = get_h1_tags(soup)

        text = get_text_content(soup)

        wc = count_words(text)
        kc = count_keyword(text, keyword)
        kd = keyword_density(text, keyword)

        internal, external = get_links(soup, final_url)
        missing_alt = get_images_missing_alt(soup)

        title_match = match_keyword(title, keyword)
        meta_match = match_keyword(meta, keyword)
        h1_match = best_h1_match(h1, keyword)

        title_len = title_length(title)
        meta_len = meta_description_length(meta)

        # Technical SEO checks (HTTPS judged on the final URL after redirects)
        tech_seo = check_technical_seo(final_url, soup)
        has_schema = tech_seo.get("has_schema", False)

        score, recs, _uncapped, stuffing = calculate_seo_score(
            title,
            meta,
            h1,
            kc,
            wc,
            len(missing_alt),
            title_match,
            meta_match,
            h1_match,
            title_len,
            meta_len,
            internal_links_count=len(internal),
            external_links_count=len(external),
            has_schema=has_schema,
            https_enabled=tech_seo.get('https_enabled', False),
            mobile_viewport=tech_seo.get('mobile_viewport', False),
            keyword_density_pct=kd,
        )

        row = {
            "Venue Name": get_venue_name(url, title),
            "URL": url,
            "SEO Score": score,
            "Score Band": get_score_band(score),
            "Word Count": wc,
            "Keyword Count": kc,
            "Keyword Density": kd,
            "Keyword Stuffing": stuffing,
            "Keyword In Title": title_match is not None,
            "Keyword In H1": h1_match is not None,
            "Internal Links": len(internal),
            "External Links": len(external),
            "Images Missing ALT": len(missing_alt),
            "HTTPS": "✓" if tech_seo.get('https_enabled') else "✗",
            "Schema": "✓" if has_schema else "✗",
            "scoring_version": SCORING_VERSION,
        }
        if include_text:
            row["_text"] = text[:20000]   # internal only — caller must pop before responding
        return row

    except Exception as e:
        logger.error(f"Error analyzing {url}: {e}")
        message, kind = row_error(e)
        return {
            "Venue Name": get_venue_name(url, urlparse(url).netloc or url),
            "URL": url,
            "SEO Score": 0,
            "Score Band": "Blocked",
            "Word Count": 0,
            "Keyword Count": 0,
            "Keyword Density": 0,
            "Internal Links": 0,
            "External Links": 0,
            "Images Missing ALT": 0,
            "HTTPS": "✗",
            "Schema": "✗",
            "error": message,
            "error_kind": kind,
        }
