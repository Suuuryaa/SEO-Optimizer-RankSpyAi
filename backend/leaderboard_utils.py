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
    has_schema_markup
)
from scoring import calculate_seo_score, get_score_band
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


def analyze_venue(url, keyword):
    """
    Comprehensive venue analysis with enhanced scoring.
    
    Args:
        url (str): Venue URL to analyze
        keyword (str): Target keyword
        
    Returns:
        dict: Analysis results with all metrics
    """
    try:
        soup, raw_html = get_page_soup(url)

        title = get_title(soup)
        meta = get_meta_description(soup)
        h1 = get_h1_tags(soup)

        text = get_text_content(soup)

        wc = count_words(text)
        kc = count_keyword(text, keyword)
        kd = keyword_density(text, keyword)

        internal, external = get_links(soup, url)
        missing_alt = get_images_missing_alt(soup)

        title_has_keyword = keyword_in_title(title, keyword)
        meta_has_keyword = keyword_in_meta(meta, keyword)
        h1_has_keyword = keyword_in_h1(h1, keyword)

        title_len = title_length(title)
        meta_len = meta_description_length(meta)
        
        # Technical SEO checks
        tech_seo = check_technical_seo(url, soup)
        has_schema = has_schema_markup(soup)

        # Enhanced scoring with technical factors
        score, recs = calculate_seo_score(
            title,
            meta,
            h1,
            kc,
            wc,
            len(missing_alt),
            title_has_keyword,
            meta_has_keyword,
            h1_has_keyword,
            title_len,
            meta_len,
            internal_links_count=len(internal),
            external_links_count=len(external),
            has_schema=has_schema,
            https_enabled=tech_seo.get('https_enabled', False),
            mobile_viewport=tech_seo.get('mobile_viewport', False)
        )

        return {
            "Venue Name": get_venue_name(url, title),
            "URL": url,
            "SEO Score": score,
            "Score Band": get_score_band(score),
            "Word Count": wc,
            "Keyword Count": kc,
            "Keyword Density": kd,
            "Internal Links": len(internal),
            "External Links": len(external),
            "Images Missing ALT": len(missing_alt),
            "HTTPS": "✓" if tech_seo.get('https_enabled') else "✗",
            "Schema": "✓" if has_schema else "✗"
        }
    
    except Exception as e:
        logger.error(f"Error analyzing {url}: {e}")
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
            "Schema": "✗"
        }