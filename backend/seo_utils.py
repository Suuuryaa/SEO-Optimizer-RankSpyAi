import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Scrapling setup ──────────────────────────────────────────────────────────
# Prefer local Scrapling-main/ (user's downloaded copy), fall back to PyPI
import os as _os, sys as _sys
_scrapling_local = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "Scrapling-main")
if _os.path.isdir(_scrapling_local) and _scrapling_local not in _sys.path:
    _sys.path.insert(0, _scrapling_local)

_SCRAPLING_AVAILABLE = False
_STEALTHY_AVAILABLE = False

try:
    from scrapling.fetchers import Fetcher as _Fetcher
    _SCRAPLING_AVAILABLE = True
    logger.info("Scrapling Fetcher (curl_cffi) loaded")
except Exception as _e:
    logger.warning(f"Scrapling Fetcher unavailable: {_e}")

try:
    from scrapling.fetchers import StealthyFetcher as _StealthyFetcher
    _STEALTHY_AVAILABLE = True
    logger.info("Scrapling StealthyFetcher (Playwright) loaded")
except Exception as _e:
    logger.warning(f"Scrapling StealthyFetcher unavailable: {_e}")


# Minimum HTML size — anything smaller is a JS shell with no real content
_MIN_HTML_BYTES = 500


class FetchError(Exception):
    """A definite fetch outcome the user should be told about (not retried).

    kind: not_found | server_error | unreachable | timeout | blocked
    """

    def __init__(self, kind: str, message: str, status: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


# Phrases that only appear on bot-challenge / block interstitials, not real pages
_BLOCK_MARKERS = (
    "attention required! | cloudflare", "just a moment...", "checking your browser before accessing",
    "enable javascript and cookies to continue", "verify you are a human", "are you a robot",
    "pardon our interruption", "request unsuccessful. incapsula", "px-captcha", "captcha-delivery",
    "enter the characters you see below", "to discuss automated access to amazon data",
    "access denied</title>", "you don't have permission to access", "unusual traffic from your computer",
    "sorry, you have been blocked",
)


def _looks_blocked(html: str) -> bool:
    """True when the HTML is a bot-challenge or access-denied page rather than the site."""
    head = html[:20000].lower()
    return any(m in head for m in _BLOCK_MARKERS)


def _is_public_url(url: str) -> bool:
    """True only if every address the host resolves to (IPv4 and IPv6) is public."""
    import ipaddress, socket
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True  # unresolvable here: the fetch itself will fail
    for info in infos:
        addr = ipaddress.ip_address(info[4][0].split("%")[0])
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_unspecified:
            return False
    return True


# Paid proxies: at most ONE paid attempt per scan, within a daily budget each,
# so blocked sites can't drain the free monthly credits (ScraperAPI 1,000, ZenRows 5,000).
_PROXY_BUDGETS = {
    "scraperapi": int(_os.environ.get("SCRAPERAPI_DAILY_LIMIT", "30")),
    "zenrows": int(_os.environ.get("ZENROWS_DAILY_LIMIT", "150")),
}


def _proxy_budget_ok(name: str) -> bool:
    try:
        from cache import check_ip_quota
    except Exception:
        return True
    return check_ip_quota("all", f"proxy-{name}", _PROXY_BUDGETS[name])


def _html_from_scrapling_response(resp):
    """Extract HTML string from a Scrapling Response object."""
    html = resp.html_content
    if isinstance(html, bytes):
        html = html.decode(resp.encoding or "utf-8", errors="replace")
    return str(html)


def _fetch_with_fetcher(url):
    """Tier 2: curl_cffi TLS fingerprint impersonation — bypasses Cloudflare 403s."""
    # Redirects are followed by hand so every hop gets the private-address check
    current = url
    for _ in range(6):
        if not _is_public_url(current):
            raise FetchError("blocked", "That address points to a private network and can't be scanned.")
        resp = _Fetcher.get(current, timeout=20, stealthy_headers=True, follow_redirects=False)
        if resp.status in (301, 302, 303, 307, 308):
            hdrs = {str(k).lower(): v for k, v in (getattr(resp, "headers", {}) or {}).items()}
            loc = hdrs.get("location")
            if not loc:
                break
            from urllib.parse import urljoin
            current = urljoin(current, loc)
            continue
        break
    if resp.status not in (200, 206):
        raise Exception(f"Fetcher got HTTP {resp.status}")
    html = _html_from_scrapling_response(resp)
    if len(html) < _MIN_HTML_BYTES:
        raise Exception(f"Fetcher returned near-empty page ({len(html)} chars) — JS-only SPA")
    if _looks_blocked(html):
        raise Exception("Fetcher got a bot-block page")
    return BeautifulSoup(html, "lxml"), html


def _fetch_with_stealthy(url):
    """Tier 5: Playwright + Patchright headless browser — handles JS SPAs + Cloudflare Turnstile."""
    if not _is_public_url(url):
        raise FetchError("blocked", "That address points to a private network and can't be scanned.")
    resp = _StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,       # Wait until JS finishes loading content
        timeout=45000,           # 45s — JS sites are slow
        solve_cloudflare=True,   # Auto-solve Cloudflare Turnstile challenges
        disable_resources=True,  # Skip images/fonts/css for speed
        block_ads=True,
        google_search=True,      # Set Google referer (looks more natural)
    )
    final_url = str(getattr(resp, "url", "") or url)
    if not _is_public_url(final_url):
        # The browser was redirected somewhere private: discard what it saw
        raise FetchError("blocked", "That address redirects to a private network and can't be scanned.")
    if resp.status not in (200, 206):
        raise Exception(f"StealthyFetcher got HTTP {resp.status}")
    html = _html_from_scrapling_response(resp)
    if len(html) < _MIN_HTML_BYTES:
        raise Exception(f"StealthyFetcher returned near-empty page ({len(html)} chars)")
    if _looks_blocked(html):
        raise Exception("StealthyFetcher got a bot-block page")
    return BeautifulSoup(html, "lxml"), html


_SCRAPER_API_KEY = _os.environ.get("SCRAPER_API_KEY", "")
_ZENROWS_API_KEY = _os.environ.get("ZENROWS_API_KEY", "")


def _fetch_with_scraperapi(url):
    """Tier 3: ScraperAPI residential proxy."""
    resp = requests.get("http://api.scraperapi.com",
                        params={"api_key": _SCRAPER_API_KEY, "url": url, "render": "false"}, timeout=25)
    if resp.status_code != 200:
        raise Exception(f"ScraperAPI returned HTTP {resp.status_code}")
    html = resp.text
    if len(html) < _MIN_HTML_BYTES:
        raise Exception(f"ScraperAPI returned thin page ({len(html)} chars)")
    if _looks_blocked(html):
        raise Exception("ScraperAPI got a bot-block page")
    return BeautifulSoup(html, "lxml"), html


def _fetch_with_zenrows(url):
    """Tier 4: ZenRows residential proxy — fallback if ScraperAPI fails."""
    resp = requests.get("https://api.zenrows.com/v1/",
                        params={"apikey": _ZENROWS_API_KEY, "url": url}, timeout=25)
    if resp.status_code != 200:
        raise Exception(f"ZenRows returned HTTP {resp.status_code}")
    html = resp.text
    if len(html) < _MIN_HTML_BYTES:
        raise Exception(f"ZenRows returned thin page ({len(html)} chars)")
    if _looks_blocked(html):
        raise Exception("ZenRows got a bot-block page")
    return BeautifulSoup(html, "lxml"), html


def get_page_soup(url):
    """
    5-tier fetch strategy:
    1. Plain requests
    2. Scrapling Fetcher / curl_cffi (TLS impersonation)
    3. ScraperAPI residential proxy (needs SCRAPER_API_KEY secret)
    4. ZenRows residential proxy (needs ZENROWS_API_KEY secret — fallback if ScraperAPI fails)
    5. Scrapling StealthyFetcher / Playwright
    """
    # ── Tier 1: plain requests ──────────────────────────────────────────────
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # No "br": requests can't decode Brotli without the brotli package, and
        # CDN-fronted sites then return compressed bytes we'd parse as junk.
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    tier1_blocked = False
    _t0 = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=False, stream=True)
        # Enforce 5 MB response size cap before reading body
        raw = b""
        for chunk in resp.iter_content(chunk_size=65536):
            raw += chunk
            if len(raw) > 5 * 1024 * 1024:
                resp.close()
                raise Exception("Response exceeds 5 MB size cap")
        resp._content = raw
        # Follow redirects manually, validating each hop
        max_redirects = 5
        hops = 0
        while resp.is_redirect and hops < max_redirects:
            location = resp.headers.get("Location", "")
            from urllib.parse import urljoin as _urljoin
            next_url = _urljoin(url, location)
            from urllib.parse import urlparse as _up2
            import ipaddress as _ipa2, socket as _sock2
            _host = _up2(next_url).hostname or ""
            try:
                _resolved = _sock2.gethostbyname(_host)
                _addr = _ipa2.ip_address(_resolved)
                if _addr.is_private or _addr.is_loopback or _addr.is_link_local:
                    raise Exception(f"Redirect to private IP blocked: {next_url}")
            except OSError:
                pass
            resp = requests.get(next_url, headers=headers, timeout=20, allow_redirects=False, stream=True)
            raw = b""
            for chunk in resp.iter_content(chunk_size=65536):
                raw += chunk
                if len(raw) > 5 * 1024 * 1024:
                    resp.close()
                    raise Exception("Redirect response exceeds 5 MB size cap")
            resp._content = raw
            hops += 1
        code = resp.status_code
        if code in (401, 403, 429, 503):
            tier1_blocked = True
            logger.info(f"Tier1 got {code} from {url} — escalating to Fetcher")
        elif code in (404, 410):
            raise FetchError("not_found", f"The page returned {code} Not Found.", code)
        elif code >= 500:
            raise FetchError("server_error", f"The site returned a server error ({code}).", code)
        elif code >= 400:
            raise FetchError("not_found", f"The page returned HTTP {code}.", code)
        else:
            # No charset in the header → requests assumes Latin-1 and garbles UTF-8 ("â\x80\x94")
            if "charset" in resp.headers.get("Content-Type", "").lower():
                html = resp.text
            else:
                html = resp.content.decode(resp.apparent_encoding or "utf-8", errors="replace")
            if _looks_blocked(html):
                tier1_blocked = True
                logger.info(f"Tier1 got a bot-block page from {url} — escalating to Fetcher")
            elif len(html) >= _MIN_HTML_BYTES:
                return BeautifulSoup(html, "lxml"), html
            else:
                # Too small — may need JS render
                tier1_blocked = True
                logger.info(f"Tier1 got thin page ({len(html)} chars) — escalating to Fetcher")
    except FetchError:
        raise
    except requests.exceptions.Timeout:
        # A site that is slow for us is slow for every tier: fail fast instead of a 60s chain
        raise FetchError("timeout", "The site took longer than 20 seconds to respond.")
    except requests.exceptions.ConnectionError as e:
        msg = str(e)
        if any(s in msg for s in ("Name or service not known", "nodename nor servname", "NameResolutionError",
                                  "getaddrinfo failed", "No address associated", "Temporary failure in name resolution")):
            raise FetchError("unreachable", "We couldn't find that domain. Check the URL is spelled correctly.")
        tier1_blocked = True
        logger.info(f"Tier1 connection error for {url}: {e} — escalating to Fetcher")
    except requests.RequestException as e:
        tier1_blocked = True
        logger.info(f"Tier1 request error for {url}: {e} — escalating to Fetcher")

    if not tier1_blocked:
        return BeautifulSoup("", "lxml"), ""

    # ── Tier 2: Scrapling Fetcher (curl_cffi) ───────────────────────────────
    if _SCRAPLING_AVAILABLE:
        try:
            logger.info(f"Tier2 Fetcher fetching {url}")
            return _fetch_with_fetcher(url)
        except Exception as e:
            logger.info(f"Tier2 Fetcher failed for {url}: {e} — escalating to StealthyFetcher")

    # ── Tiers 3–4: ONE paid proxy attempt (first provider with budget left) ─
    paid = [("scraperapi", _SCRAPER_API_KEY, _fetch_with_scraperapi),
            ("zenrows", _ZENROWS_API_KEY, _fetch_with_zenrows)]
    if time.time() - _t0 < 20:
        for name, key, fetch in paid:
            if not key or not _proxy_budget_ok(name):
                continue
            try:
                logger.info(f"Paid tier {name} fetching {url}")
                return fetch(url)
            except Exception as e:
                logger.info(f"Paid tier {name} failed for {url}: {e} — no further paid attempts")
            break

    # ── Tier 5: StealthyFetcher (Playwright headless + Cloudflare solver) ───
    if _STEALTHY_AVAILABLE and time.time() - _t0 < 20:
        try:
            logger.info(f"Tier5 StealthyFetcher fetching {url}")
            return _fetch_with_stealthy(url)
        except Exception as e:
            logger.info(f"Tier5 StealthyFetcher failed for {url}: {e}")

    raise FetchError("blocked", "This site blocked our scanner, so we couldn't read the page.")


# Keep tenacity retry on top for transient network errors
get_page_soup = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_not_exception_type(FetchError),
    reraise=True
)(get_page_soup)


# One scan = one fetch: /analyze, then the meta, schema and local-SEO panels all
# ask for the same URL within a minute. Single replica, so a process cache is enough.
_PAGE_CACHE: dict = {}
_PAGE_TTL = 15 * 60
_PAGE_CACHE_MAX = 64
_fetch_page_uncached = get_page_soup


def get_page_soup(url):
    """Cached wrapper: returns a fresh soup (callers mutate it) from cached HTML."""
    now = time.time()
    hit = _PAGE_CACHE.get(url)
    if hit and now - hit[0] < _PAGE_TTL:
        return BeautifulSoup(hit[1], "lxml"), hit[1]
    soup, html = _fetch_page_uncached(url)
    if html:
        if len(_PAGE_CACHE) >= _PAGE_CACHE_MAX:
            _PAGE_CACHE.pop(min(_PAGE_CACHE, key=lambda k: _PAGE_CACHE[k][0]), None)
        _PAGE_CACHE[url] = (now, html)
    return soup, html


def _safe_text(value: str, max_len: int = 500) -> str:
    """Strip HTML tags and limit length.

    Not HTML-escaped: the React frontend escapes all text it renders, so escaping
    here showed "&amp;" to users and counted entity characters in title length.
    """
    import re as _re
    # Remove any HTML tags that survived BeautifulSoup extraction
    clean = _re.sub(r'<[^>]+>', '', value)
    return clean.strip()[:max_len]


def get_title(soup):
    """Extract page title."""
    if soup.title:
        return _safe_text(soup.title.get_text(strip=True), max_len=300)
    return "No title found"


def get_meta_description(soup):
    """Extract meta description."""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        return _safe_text(meta_tag["content"], max_len=500)
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
