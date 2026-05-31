import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Scrapling — try local Scrapling-main first, then fall back to PyPI install
import os as _os, sys as _sys
_scrapling_local = _os.path.join(_os.path.dirname(__file__), "Scrapling-main")
if _os.path.isdir(_scrapling_local) and _scrapling_local not in _sys.path:
    _sys.path.insert(0, _scrapling_local)

try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
    _SCRAPLING_AVAILABLE = True
except Exception:
    _SCRAPLING_AVAILABLE = False


def _scrapling_fetch(url):
    """Use Scrapling (curl_cffi TLS impersonation) to bypass Cloudflare/bot walls."""
    resp = _ScraplingFetcher.get(url, timeout=30, stealthy_headers=True)
    if resp.status not in (200, 206):
        raise Exception(f"Scrapling got HTTP {resp.status} from {url}")
    html = resp.html_content  # Scrapling Response uses .html_content not .content
    if not html or len(html) < 200:
        raise Exception(f"Scrapling returned near-empty page ({len(html or '')} chars) — site may be JS-only")
    return BeautifulSoup(html, "lxml"), html


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    reraise=True
)
def get_page_soup(url):
    """Fetch page with plain requests; fall back to Scrapling (curl_cffi) if blocked."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        # Treat 403/429/503 as blocked — try Scrapling fallback
        if resp.status_code in (403, 429, 503) and _SCRAPLING_AVAILABLE:
            logger.info(f"Got {resp.status_code} from {url}, retrying with Scrapling")
            return _scrapling_fetch(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml"), resp.text

    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout(f"Timed out fetching {url}.")
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        # Try Scrapling for any HTTP error if available
        if _SCRAPLING_AVAILABLE:
            logger.info(f"HTTP {code} from {url}, trying Scrapling fallback")
            try:
                return _scrapling_fetch(url)
            except Exception as se:
                raise Exception(f"Blocked ({code}): {url} — even stealth fetch failed: {se}")
        raise Exception(f"HTTP {code} from {url} — site blocks automated access.")
    except requests.RequestException as e:
        if _SCRAPLING_AVAILABLE:
            try:
                return _scrapling_fetch(url)
            except Exception:
                pass
        raise


def get_title(soup):
    """Extract page title."""
    if soup.title:
        return soup.title.get_text(strip=True)
    return "No title found"


def get_meta_description(soup):
    """Extract meta description."""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        return meta_tag["content"].strip()
    return "No meta description found"


def get_h1_tags(soup):
    """Extract all H1 tags."""
    return [tag.get_text(strip=True) for tag in soup.find_all("h1")]


def get_text_content(soup):
    """Extract visible text content from page."""
    # Remove script and style elements
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    
    return soup.get_text(separator=" ", strip=True)


def count_words(text):
    """Count total words in text."""
    if not text:
        return 0
    return len(text.split())


def count_keyword(text, keyword):
    """Count exact keyword matches (case-insensitive)."""
    if not text or not keyword:
        return 0
    return text.lower().count(keyword.lower())


def keyword_density(text, keyword):
    """Calculate keyword density as percentage."""
    total_words = count_words(text)
    if total_words == 0:
        return 0
    keyword_count = count_keyword(text, keyword)
    return round((keyword_count / total_words) * 100, 2)


def get_links(soup, base_url):
    """
    Categorize all links as internal or external.
    
    Returns:
        tuple: (list of internal links, list of external links)
    """
    internal_links = []
    external_links = []
    domain = urlparse(base_url).netloc

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        
        # Skip non-http links
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
            
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        if parsed_url.netloc == domain:
            internal_links.append(full_url)
        elif parsed_url.netloc:  # Only add if it has a domain
            external_links.append(full_url)

    return list(set(internal_links)), list(set(external_links))


def get_images_missing_alt(soup):
    """Find all images without alt attributes."""
    missing_alt = []

    for img in soup.find_all("img"):
        alt = img.get("alt", "").strip()
        if not alt:
            missing_alt.append(img.get("src", "No src"))

    return missing_alt


def keyword_in_title(title, keyword):
    """Check if keyword appears in title."""
    if not title or not keyword:
        return False
    return keyword.lower() in title.lower()


def keyword_in_meta(meta_description, keyword):
    """Check if keyword appears in meta description."""
    if not meta_description or not keyword:
        return False
    return keyword.lower() in meta_description.lower()


def keyword_in_h1(h1_tags, keyword):
    """Check if keyword appears in any H1 tag."""
    if not keyword:
        return False
    for h1 in h1_tags:
        if keyword.lower() in h1.lower():
            return True
    return False


def title_length(title):
    """Get character length of title."""
    return len(title) if title else 0


def meta_description_length(meta_description):
    """Get character length of meta description."""
    return len(meta_description) if meta_description else 0


def get_keyword_tokens(keyword):
    """Split keyword into individual tokens."""
    if not keyword:
        return []
    return [token.strip().lower() for token in keyword.split() if token.strip()]


def count_partial_keyword_matches(text, keyword):
    """
    Count individual keyword token occurrences.
    
    Returns:
        tuple: (dict of token counts, total matches)
    """
    if not text or not keyword:
        return {}, 0
        
    text_lower = text.lower()
    tokens = get_keyword_tokens(keyword)

    token_counts = {}
    total_partial_matches = 0

    for token in tokens:
        matches = len(re.findall(rf"\b{re.escape(token)}\b", text_lower))
        token_counts[token] = matches
        total_partial_matches += matches

    return token_counts, total_partial_matches


def keyword_token_coverage(text, keyword):
    """
    Calculate percentage of keyword tokens present in text.
    
    Returns:
        float: Percentage (0-100)
    """
    if not text or not keyword:
        return 0
        
    text_lower = text.lower()
    tokens = get_keyword_tokens(keyword)

    if len(tokens) == 0:
        return 0

    present_tokens = 0
    for token in tokens:
        if re.search(rf"\b{re.escape(token)}\b", text_lower):
            present_tokens += 1

    return round((present_tokens / len(tokens)) * 100, 2)


# ==================== ENHANCED FEATURES ====================

def detect_schema_markup(soup):
    """
    Detect structured data (JSON-LD, Microdata, RDFa).
    
    Returns:
        dict: Schema types found in each format
    """
    schemas = {
        'json_ld': [],
        'microdata': [],
        'rdfa': []
    }
    
    try:
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    schema_type = data.get('@type', 'Unknown')
                    schemas['json_ld'].append(schema_type)
                except json.JSONDecodeError:
                    pass
        
        # Microdata
        microdata = soup.find_all(attrs={'itemtype': True})
        schemas['microdata'] = [tag.get('itemtype') for tag in microdata]
        
        # RDFa
        rdfa = soup.find_all(attrs={'typeof': True})
        schemas['rdfa'] = [tag.get('typeof') for tag in rdfa]
        
    except Exception as e:
        logger.warning(f"Error detecting schema markup: {e}")
    
    return schemas


def has_schema_markup(soup):
    """Check if page has any structured data."""
    schemas = detect_schema_markup(soup)
    return any(schemas.values())


def check_technical_seo(url, soup):
    """
    Comprehensive technical SEO audit.
    
    Returns:
        dict: Technical SEO indicators
    """
    checks = {}
    
    try:
        # HTTPS
        checks['https_enabled'] = url.startswith('https://')
        
        # Robots meta tag
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        checks['robots_meta'] = robots_meta.get('content') if robots_meta else None
        checks['robots_noindex'] = 'noindex' in (checks['robots_meta'] or '').lower()
        checks['robots_nofollow'] = 'nofollow' in (checks['robots_meta'] or '').lower()
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        checks['canonical_url'] = canonical.get('href') if canonical else None
        checks['has_canonical'] = canonical is not None
        
        # Mobile viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        checks['mobile_viewport'] = viewport is not None
        checks['viewport_content'] = viewport.get('content') if viewport else None
        
        # Language
        html_tag = soup.find('html')
        checks['lang_attribute'] = html_tag.get('lang') if html_tag else None
        checks['has_lang'] = checks['lang_attribute'] is not None
        
        # Open Graph tags
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        checks['og_tags_count'] = len(og_tags)
        checks['has_og_title'] = soup.find('meta', property='og:title') is not None
        checks['has_og_description'] = soup.find('meta', property='og:description') is not None
        checks['has_og_image'] = soup.find('meta', property='og:image') is not None
        
        # Twitter Card
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        checks['twitter_card_count'] = len(twitter_tags)
        checks['has_twitter_card'] = soup.find('meta', attrs={'name': 'twitter:card'}) is not None
        
        # Schema markup
        schemas = detect_schema_markup(soup)
        checks['has_schema'] = any(schemas.values())
        checks['schema_types'] = schemas
        
        # Heading structure
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))
        
        checks['h1_count'] = h1_count
        checks['h2_count'] = h2_count
        checks['h3_count'] = h3_count
        checks['proper_h1_usage'] = h1_count == 1
        checks['has_heading_hierarchy'] = h2_count > 0
        
    except Exception as e:
        logger.error(f"Error in technical SEO check: {e}")
        checks['error'] = str(e)
    
    return checks


def analyze_content_quality(text):
    """
    Analyze readability and content quality metrics.
    
    Returns:
        dict: Content quality indicators
    """
    try:
        import textstat
        
        if not text or len(text.strip()) < 100:
            return {
                'flesch_reading_ease': 0,
                'flesch_kincaid_grade': 0,
                'readability_rating': 'N/A - Insufficient content',
                'avg_sentence_length': 0,
                'unique_words_ratio': 0
            }
        
        flesch_score = textstat.flesch_reading_ease(text)
        
        # Readability rating
        if flesch_score >= 90:
            rating = "Very Easy"
        elif flesch_score >= 80:
            rating = "Easy"
        elif flesch_score >= 70:
            rating = "Fairly Easy"
        elif flesch_score >= 60:
            rating = "Standard"
        elif flesch_score >= 50:
            rating = "Fairly Difficult"
        elif flesch_score >= 30:
            rating = "Difficult"
        else:
            rating = "Very Difficult"
        
        words = text.split()
        unique_ratio = len(set(w.lower() for w in words)) / len(words) if words else 0
        
        return {
            'flesch_reading_ease': round(flesch_score, 1),
            'flesch_kincaid_grade': round(textstat.flesch_kincaid_grade(text), 1),
            'readability_rating': rating,
            'avg_sentence_length': round(textstat.avg_sentence_length(text), 1),
            'unique_words_ratio': round(unique_ratio * 100, 1)
        }
        
    except ImportError:
        logger.warning("textstat not installed - skipping readability analysis")
        return {}
    except Exception as e:
        logger.error(f"Error analyzing content quality: {e}")
        return {}


def get_heading_structure(soup):
    """
    Extract complete heading hierarchy.
    
    Returns:
        dict: Heading counts and samples
    """
    structure = {}
    
    for level in range(1, 7):
        headings = soup.find_all(f'h{level}')
        structure[f'h{level}'] = {
            'count': len(headings),
            'samples': [h.get_text(strip=True)[:60] for h in headings[:3]]
        }
    
    return structure
