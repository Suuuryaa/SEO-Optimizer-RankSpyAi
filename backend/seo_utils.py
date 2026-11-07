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


# ONE headless browser at a time across the JS renderer, the Tier-5 stealthy
# fetcher and deep crawl: Chromium needs 200-300 MB and Railway allows 0.5 GB.
import threading as _thr
_BROWSER_SLOT = _thr.BoundedSemaphore(1)

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
    """True only if every address the host resolves to (IPv4 and IPv6) is public.

    False when the host can't be resolved (fail closed).
    """
    from net_safety import url_is_public
    return url_is_public(url)


def _assert_public(url: str, redirected: bool = False) -> None:
    """Raise FetchError unless url's host resolves only to public addresses."""
    from net_safety import url_hosts_public, HostLookupError
    try:
        ok = url_hosts_public(url)
    except HostLookupError:
        raise FetchError("unreachable", "We couldn't find that domain. Check the URL is spelled correctly.")
    if not ok:
        if redirected:
            raise FetchError("blocked", "The page redirected to a private address.")
        raise FetchError("blocked", "That address points to a private network and can't be scanned.")


# Paid proxies: at most ONE paid attempt per scan, within a daily budget each,
# so blocked sites can't drain the free monthly credits (ScraperAPI 1,000, ZenRows 5,000).
_PROXY_FALLBACK = _os.environ.get("PROXY_FALLBACK", "").lower() in ("1", "true", "on")
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
    if not _is_public_url(url):
        raise FetchError("blocked", "That address points to a private network and can't be scanned.")
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
    if not _is_public_url(url):
        raise FetchError("blocked", "That address points to a private network and can't be scanned.")
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


_HTML_TYPES = ("text/html", "application/xhtml+xml")
_MAX_PAGE_BYTES = 5 * 1024 * 1024


def _read_capped(resp) -> bytes:
    raw = b""
    for chunk in resp.iter_content(chunk_size=65536):
        raw += chunk
        if len(raw) > _MAX_PAGE_BYTES:
            resp.close()
            raise FetchError("not_html", "That URL returned more than 5 MB, which is too large to scan.")
    return raw


def _fetch_page(url):
    """
    5-tier fetch strategy. Returns (soup, html, meta) where meta is
    {final_url, http_status, x_robots_tag, content_type}.
    1. Plain requests (every redirect hop checked against private addresses)
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
    other_meta = {"final_url": url, "http_status": None, "x_robots_tag": None, "content_type": None}

    tier1_blocked = False
    _t0 = time.time()
    try:
        # Redirects are followed by hand; every hop (the first URL too) must be public
        current = url
        max_redirects = 5
        for hop in range(max_redirects + 1):
            _assert_public(current, redirected=hop > 0)
            resp = requests.get(current, headers=headers, timeout=20, allow_redirects=False, stream=True)
            if resp.is_redirect and hop < max_redirects:
                location = resp.headers.get("Location", "")
                resp.close()
                if not location:
                    break
                current = urljoin(current, location)   # relative to THIS hop, not the original URL
                continue
            break
        resp._content = _read_capped(resp)
        code = resp.status_code
        content_type = resp.headers.get("Content-Type", "")
        meta = {"final_url": current, "http_status": code,
                "x_robots_tag": resp.headers.get("X-Robots-Tag"), "content_type": content_type or None}
        if code in (401, 403, 429, 503):
            tier1_blocked = True
            logger.info(f"Tier1 got {code} from {url} — escalating to Fetcher")
        elif code in (404, 410):
            raise FetchError("not_found", f"The page returned {code} Not Found.", code)
        elif code >= 500:
            raise FetchError("server_error", f"The site returned a server error ({code}).", code)
        elif code >= 400:
            raise FetchError("not_found", f"The page returned HTTP {code}.", code)
        elif 300 <= code < 400:
            tier1_blocked = True
            logger.info(f"Tier1 too many redirects for {url} — escalating to Fetcher")
        else:
            ctype = content_type.split(";")[0].strip().lower()
            if ctype and ctype not in _HTML_TYPES:
                raise FetchError("not_html", f"That URL isn't a web page (it returned {ctype}).")
            # No charset in the header → requests assumes Latin-1 and garbles UTF-8 ("â\x80\x94")
            if "charset" in content_type.lower():
                html = resp.text
            else:
                html = resp.content.decode(resp.apparent_encoding or "utf-8", errors="replace")
            if _looks_blocked(html):
                tier1_blocked = True
                logger.info(f"Tier1 got a bot-block page from {url} — escalating to Fetcher")
            elif len(html) >= _MIN_HTML_BYTES:
                return BeautifulSoup(html, "lxml"), html, meta
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
        return BeautifulSoup("", "lxml"), "", other_meta

    # ── Tier 2: Scrapling Fetcher (curl_cffi) ───────────────────────────────
    if _SCRAPLING_AVAILABLE:
        try:
            logger.info(f"Tier2 Fetcher fetching {url}")
            return (*_fetch_with_fetcher(url), other_meta)
        except Exception as e:
            logger.info(f"Tier2 Fetcher failed for {url}: {e} — escalating to StealthyFetcher")

    # ── Tiers 3–4: ONE paid proxy attempt (first provider with budget left) ─
    # Off unless PROXY_FALLBACK=on: proxies cost money per page, and routing around a
    # site's blocks is the riskiest thing for a payment provider's review.
    paid = [("scraperapi", _SCRAPER_API_KEY, _fetch_with_scraperapi),
            ("zenrows", _ZENROWS_API_KEY, _fetch_with_zenrows)]
    used_proxy = False
    if _PROXY_FALLBACK and time.time() - _t0 < 20 and _is_public_url(url):
        for name, key, fetch in paid:
            if not key or not _proxy_budget_ok(name):
                continue
            used_proxy = True
            try:
                import spend
                spend.proxy_call()
            except Exception:
                pass
            try:
                logger.info(f"Paid tier {name} fetching {url}")
                return (*fetch(url), other_meta)
            except Exception as e:
                logger.info(f"Paid tier {name} failed for {url}: {e} — no further paid attempts")
            break

    # ── Tier 5: StealthyFetcher (Playwright headless + Cloudflare solver) ───
    # Shares the single browser slot with the JS renderer and deep crawl; skipped when busy.
    if _STEALTHY_AVAILABLE and time.time() - _t0 < 20:
        if _BROWSER_SLOT.acquire(blocking=False):
            try:
                logger.info(f"Tier5 StealthyFetcher fetching {url}")
                return (*_fetch_with_stealthy(url), other_meta)
            except Exception as e:
                logger.info(f"Tier5 StealthyFetcher failed for {url}: {e}")
            finally:
                _BROWSER_SLOT.release()
        else:
            logger.info(f"Tier5 skipped (browser busy): {url}")

    err = FetchError("blocked", "This site blocked our scanner, so we couldn't read the page.")
    err.used_proxy = used_proxy      # a paid proxy was spent: the scan isn't refunded
    raise err


# Keep tenacity retry on top for transient network errors
_fetch_page = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_not_exception_type(FetchError),
    reraise=True
)(_fetch_page)


# One scan = one fetch: /analyze, then the meta, schema and local-SEO panels all
# ask for the same URL within a minute. Single replica, so a process cache is enough.
# LRU by total HTML size (24 MB); pages over 2 MB are never cached.
import threading as _threading
from collections import OrderedDict as _OrderedDict

_PAGE_CACHE: "_OrderedDict" = _OrderedDict()   # key -> (time, html, meta)
_PAGE_CACHE_LOCK = _threading.Lock()
_PAGE_TTL = 15 * 60
_PAGE_CACHE_MAX_BYTES = 24 * 1024 * 1024
_PAGE_CACHE_ITEM_MAX = 2 * 1024 * 1024
_page_cache_bytes = 0


def _cache_get(key):
    with _PAGE_CACHE_LOCK:
        hit = _PAGE_CACHE.get(key)
        if not hit:
            return None
        if time.time() - hit[0] >= _PAGE_TTL:
            _cache_drop(key)
            return None
        _PAGE_CACHE.move_to_end(key)
        return hit


def _cache_drop(key):
    global _page_cache_bytes
    old = _PAGE_CACHE.pop(key, None)
    if old:
        _page_cache_bytes -= len(old[1])


def _cache_put(key, html, meta=None):
    global _page_cache_bytes
    if not html or len(html) > _PAGE_CACHE_ITEM_MAX:
        return
    with _PAGE_CACHE_LOCK:
        _cache_drop(key)
        _PAGE_CACHE[key] = (time.time(), html, meta)
        _page_cache_bytes += len(html)
        while _page_cache_bytes > _PAGE_CACHE_MAX_BYTES and _PAGE_CACHE:
            _cache_drop(next(iter(_PAGE_CACHE)))


def get_page_soup(url):
    """Cached wrapper: returns a fresh soup from cached HTML, fetching on a miss."""
    hit = _cache_get(url)
    if hit:
        return BeautifulSoup(hit[1], "lxml"), hit[1]
    soup, html, meta = _fetch_page(url)
    _cache_put(url, html, meta)
    return soup, html


def get_page_meta(url):
    """{final_url, http_status, x_robots_tag, content_type} from the last fetch of url, or None."""
    hit = _cache_get(url)
    return hit[2] if hit else None


def page_cached(url) -> bool:
    """True when the raw or rendered page is in the 15-minute cache."""
    return _cache_get(url) is not None or _cache_get((url, "rendered")) is not None


# ── JS rendering for thin pages ──────────────────────────────────────────────
# Google runs JavaScript before indexing. When the plain HTML has almost no text
# (Airbnb served 3 words), render the page in headless Chromium and analyse the
# rendered DOM instead. One render at a time: Chromium needs 200-300 MB and the
# Railway free plan allows 0.5 GB per service.
THIN_PAGE_WORDS = 150
_RENDER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def render_page_html(url: str, timeout_ms: int = 15000):
    """Rendered HTML of `url`, or None if rendering is unavailable, busy, blocked or private."""
    if not _is_public_url(url):
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    hit = _cache_get((url, "rendered"))
    if hit:
        return hit[1]
    if not _BROWSER_SLOT.acquire(timeout=20):
        logger.info(f"render skipped (busy): {url}")
        return None
    host_ok: dict = {}

    def _allowed(u: str) -> bool:
        from urllib.parse import urlparse
        h = urlparse(u).hostname or ""
        if h not in host_ok:
            host_ok[h] = _is_public_url(u)
        return host_ok[h]

    def _route(route):
        req = route.request
        if req.resource_type in ("image", "media", "font"):
            return route.abort()          # not needed for text; <img> tags stay in the DOM
        if req.url.startswith(("http://", "https://")) and not _allowed(req.url):
            return route.abort()          # SSRF: nothing private, at any hop
        return route.continue_()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = browser.new_context(user_agent=_RENDER_UA, viewport={"width": 1280, "height": 900}).new_page()
                page.route("**/*", _route)
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                if not _allowed(page.url):
                    return None
                html = page.content()
            finally:
                browser.close()
    except Exception as exc:
        logger.info(f"render failed for {url}: {exc}")
        return None
    finally:
        _BROWSER_SLOT.release()
    if not html or _looks_blocked(html):
        return None
    _cache_put((url, "rendered"), html)
    return html


# ── Indexability ─────────────────────────────────────────────────────────────
_ROBOTS_CACHE: dict = {}          # origin -> (time, Protego parser | None)
_ROBOTS_LOCK = _threading.Lock()
_ROBOTS_TTL = 15 * 60


def robots_txt_allows(url: str, ua: str = "Googlebot") -> bool:
    """True unless the site's robots.txt disallows `ua` for this URL's path.

    Fetched with per-hop SSRF checks, cached per origin for 15 minutes.
    Any fetch or parse failure counts as allowed (indexable).
    """
    p = urlparse(url)
    origin = f"{p.scheme}://{p.netloc}"
    now = time.time()
    with _ROBOTS_LOCK:
        hit = _ROBOTS_CACHE.get(origin)
    if hit and now - hit[0] < _ROBOTS_TTL:
        parser = hit[1]
    else:
        parser = None
        try:
            from net_safety import safe_get
            from protego import Protego
            resp = safe_get(origin + "/robots.txt", max_bytes=500_000, timeout=8)
            if resp is not None and resp.status_code == 200:
                parser = Protego.parse(resp.text)
        except Exception as exc:
            logger.info(f"robots.txt check failed for {origin}: {exc}")
        with _ROBOTS_LOCK:
            if len(_ROBOTS_CACHE) > 500:
                _ROBOTS_CACHE.clear()
            _ROBOTS_CACHE[origin] = (now, parser)
    if parser is None:
        return True
    try:
        return bool(parser.can_fetch(url, ua))
    except Exception:
        return True


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
    """Page title, or "" when the page has none."""
    if soup.title:
        return _safe_text(soup.title.get_text(strip=True), max_len=300)
    return ""


def get_meta_description(soup):
    """Meta description, or "" when the page has none."""
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_tag and meta_tag.get("content"):
        return _safe_text(meta_tag["content"], max_len=500)
    return ""


def get_h1_tags(soup):
    """Extract all H1 tags."""
    return [tag.get_text(strip=True) for tag in soup.find_all("h1")]


_INVISIBLE_PARENTS = frozenset({"script", "style", "noscript", "template", "head"})


def get_text_content(soup):
    """Visible page text. Does NOT modify the soup (JSON-LD scripts must survive
    for the schema check that runs afterwards)."""
    from bs4.element import NavigableString, Comment, Declaration, Doctype, ProcessingInstruction, CData
    skip_types = (Comment, Declaration, Doctype, ProcessingInstruction, CData)
    parts = []
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString) or isinstance(node, skip_types):
            continue
        if any(p.name in _INVISIBLE_PARENTS for p in node.parents):
            continue
        t = node.strip()
        if t:
            parts.append(t)
    return " ".join(parts)


# ── Keyword matching (v1.1) ──────────────────────────────────────────────────
import unicodedata as _ud

# Scripts written without spaces between words: Han, Hiragana, Katakana, Thai.
_NOSPACE_RE = re.compile(r"[぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿฀-๿]")


def _normalise(text: str) -> str:
    """NFKC + casefold; punctuation, hyphens and underscores become spaces."""
    text = _ud.normalize("NFKC", text or "").casefold()
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


def _token_pattern(tok: str) -> str:
    """A keyword token that also matches its simple plural/singular (s / es)."""
    forms = {tok}
    if len(tok) > 3 and tok.endswith("es"):
        forms.add(tok[:-2])
    if len(tok) > 2 and tok.endswith("s"):
        forms.add(tok[:-1])
    alts = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return rf"(?:{alts})(?:es|s)?"


def _phrase_regex(kw_norm: str):
    tokens = kw_norm.split()
    body = r"\s+".join(_token_pattern(t) for t in tokens)
    return re.compile(rf"(?<!\w){body}(?!\w)")


def match_keyword(text, keyword):
    """How the keyword appears in text: "exact" (whole phrase, word boundaries,
    plural-tolerant), "all_tokens" (every word present, not as one phrase) or None.

    Text and keyword are NFKC-normalised and casefolded; punctuation and
    hyphens count as spaces, so "e-commerce" matches "e commerce". Keywords in
    Chinese/Japanese/Thai script match as substrings.
    """
    kw = _normalise(keyword)
    tx = _normalise(text)
    if not kw or not tx:
        return None
    if _NOSPACE_RE.search(kw):
        if kw.replace(" ", "") in tx.replace(" ", ""):
            return "exact"
        toks = kw.split()
        if len(toks) > 1 and all(t in tx for t in toks):
            return "all_tokens"
        return None
    if _phrase_regex(kw).search(tx):
        return "exact"
    toks = kw.split()
    if len(toks) > 1 and all(re.search(rf"(?<!\w){_token_pattern(t)}(?!\w)", tx) for t in toks):
        return "all_tokens"
    return None


def count_words(text):
    """Words in text: whitespace-separated tokens, plus Chinese/Japanese/Thai
    characters at 2 characters per word (those scripts don't use spaces)."""
    if not text:
        return 0
    nospace_chars = len(_NOSPACE_RE.findall(text))
    other = _NOSPACE_RE.sub(" ", text)
    tokens = [t for t in other.split() if any(ch.isalnum() for ch in t)]
    return len(tokens) + (nospace_chars + 1) // 2


def count_keyword(text, keyword):
    """Whole-phrase keyword occurrences (word boundaries, plural-tolerant, case-insensitive)."""
    kw = _normalise(keyword)
    tx = _normalise(text)
    if not kw or not tx:
        return 0
    if _NOSPACE_RE.search(kw):
        return tx.replace(" ", "").count(kw.replace(" ", ""))
    return len(_phrase_regex(kw).findall(tx))


def keyword_density(text, keyword):
    """Share of the page's words taken up by the keyword phrase, in %."""
    total_words = count_words(text)
    if total_words == 0:
        return 0
    words_in_kw = max(1, count_words(keyword))
    return round((count_keyword(text, keyword) * words_in_kw / total_words) * 100, 2)


def _host_key(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def get_links(soup, base_url):
    """
    Categorize all links as internal or external. www. and bare hosts count as
    the same site; pass the page's final URL (after redirects) as base_url.

    Returns:
        tuple: (list of internal links, list of external links)
    """
    internal_links = []
    external_links = []
    domain = _host_key(base_url)

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # Skip non-http links
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue

        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            continue
        if _host_key(full_url) == domain:
            internal_links.append(full_url)
        else:
            external_links.append(full_url)

    return list(set(internal_links)), list(set(external_links))


def get_images_missing_alt(soup):
    """Images with NO alt attribute.

    alt="" is correct HTML for decorative images (Lighthouse and WCAG accept it),
    so it is not counted. Images hidden from assistive tech and 1x1 tracking
    pixels are skipped too.
    """
    missing_alt = []

    for img in soup.find_all("img"):
        if img.has_attr("alt"):
            continue
        if img.get("role") == "presentation" or img.get("aria-hidden") == "true":
            continue
        if str(img.get("width", "")).strip() in ("0", "1") and str(img.get("height", "")).strip() in ("0", "1"):
            continue
        missing_alt.append(img.get("src", "No src"))

    return missing_alt


def keyword_in_title(title, keyword):
    """True when the keyword phrase, or all of its words, appear in the title."""
    return match_keyword(title, keyword) is not None


def keyword_in_meta(meta_description, keyword):
    """True when the keyword phrase, or all of its words, appear in the meta description."""
    return match_keyword(meta_description, keyword) is not None


def best_h1_match(h1_tags, keyword):
    """Best keyword match level across all H1s: "exact" > "all_tokens" > None."""
    best = None
    for h1 in h1_tags or []:
        m = match_keyword(h1, keyword)
        if m == "exact":
            return m
        best = best or m
    return best


def keyword_in_h1(h1_tags, keyword):
    """True when any H1 contains the keyword phrase or all of its words."""
    return best_h1_match(h1_tags, keyword) is not None


# ── Indexability gate ────────────────────────────────────────────────────────

def _norm_for_compare(url: str) -> str:
    """Scheme, www., trailing slash and fragment don't make a different page."""
    p = urlparse(url.strip())
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or ""
    return f"{host}{(':' + str(p.port)) if p.port else ''}{path}" + (f"?{p.query}" if p.query else "")


def _robots_tokens(content: str) -> set:
    out = set()
    for token in (content or "").lower().split(","):
        token = token.strip()
        if ":" in token and not token.startswith(("max-", "unavailable_after")):
            token = token.split(":", 1)[1].strip()        # "googlebot: noindex"
        out.add(token)
    return out


def check_indexability(url, soup, meta=None):
    """Can Google index this page? Returns {indexable, reasons, canonical_url}.

    Reasons: meta robots noindex, X-Robots-Tag noindex, robots.txt blocking
    Googlebot for this path, or a canonical pointing at a different URL.
    """
    meta = meta or {}
    final_url = meta.get("final_url") or url
    reasons = []

    for tag in soup.find_all("meta", attrs={"name": re.compile(r"^(robots|googlebot)$", re.I)}):
        if _robots_tokens(tag.get("content")) & {"noindex", "none"}:
            reasons.append({"code": "meta_noindex",
                            "detail": f'The page has <meta name="{tag.get("name")}" content="{tag.get("content")}">.'})
            break

    xrt = meta.get("x_robots_tag")
    if xrt and _robots_tokens(xrt) & {"noindex", "none"}:
        reasons.append({"code": "x_robots_noindex", "detail": f"The server sends X-Robots-Tag: {xrt}."})

    if not robots_txt_allows(final_url, "Googlebot"):
        reasons.append({"code": "robots_txt_blocked",
                        "detail": "The site's robots.txt blocks Googlebot from this page."})

    canonical_url = None
    link = soup.find("link", rel=lambda v: v and "canonical" in (v if isinstance(v, list) else str(v).split()))
    if link and link.get("href"):
        canonical_url = urljoin(final_url, link["href"].strip())
        if _norm_for_compare(canonical_url) != _norm_for_compare(final_url):
            reasons.append({"code": "canonical_elsewhere",
                            "detail": f"The canonical tag points to a different page: {canonical_url}"})

    return {"indexable": not reasons, "reasons": reasons, "canonical_url": canonical_url}


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

def _jsonld_types(data, out: list) -> None:
    """Collect every @type from a JSON-LD value: top-level lists and @graph are flattened."""
    if isinstance(data, list):
        for item in data:
            _jsonld_types(item, out)
        return
    if not isinstance(data, dict):
        return
    t = data.get("@type")
    if isinstance(t, str):
        out.append(t)
    elif isinstance(t, list):
        out.extend(str(x) for x in t if isinstance(x, (str, int)))
    if "@graph" in data:
        _jsonld_types(data["@graph"], out)


def detect_schema_markup(soup):
    """
    Detect structured data (JSON-LD, Microdata, RDFa).

    Each JSON-LD block is parsed on its own, so one broken block doesn't hide
    the others or the microdata/RDFa found on the page.

    Returns:
        dict: Schema types found in each format
    """
    schemas = {
        'json_ld': [],
        'microdata': [],
        'rdfa': []
    }

    for script in soup.find_all('script', attrs={'type': lambda t: t and 'ld+json' in t.lower()}):
        try:
            raw = script.string if script.string is not None else script.get_text()
            if not raw or not raw.strip():
                continue
            data = json.loads(raw)
            types: list = []
            _jsonld_types(data, types)
            schemas['json_ld'].extend(types or ['Unknown'])
        except Exception:
            continue

    try:
        schemas['microdata'] = [tag.get('itemtype') for tag in soup.find_all(attrs={'itemtype': True})]
    except Exception as e:
        logger.warning(f"Error detecting microdata: {e}")
    try:
        schemas['rdfa'] = [tag.get('typeof') for tag in soup.find_all(attrs={'typeof': True})]
    except Exception as e:
        logger.warning(f"Error detecting RDFa: {e}")

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
        checks['error'] = "Technical check failed"
    
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
