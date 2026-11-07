from urllib.parse import urlparse
import json
import re
import time


def _extract_json_list(text):
    """Robustly extract a JSON array from messy LLM output."""
    text = text.strip()

    # 1. Try parsing the whole thing directly
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences: ```json ... ``` or ``` ... ```
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            result = json.loads(fence.group(1).strip())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 3. Find first [ ... ] spanning the whole array
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 4. Try to collect individual {...} objects inside the text
    objects = re.findall(r'\{[^{}]*\}', text, re.DOTALL)
    if objects:
        try:
            result = json.loads(f"[{','.join(objects)}]")
            if isinstance(result, list) and result:
                return result
        except json.JSONDecodeError:
            pass

    return None


def _get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""


def _same_site(domain, primary_domain):
    """True for the primary domain itself and any of its subdomains (discuss.python.org)."""
    if not domain or not primary_domain:
        return False
    return (domain == primary_domain
            or domain.endswith("." + primary_domain)
            or primary_domain.endswith("." + domain))


def classify_competitor(url, title="", primary_domain=""):
    """
    Classify a SERP result. Returns one of:
      Primary Venue, Social, Encyclopedia, Forum, Directory,
      Institutional, Marketplace, Content, Direct Competitor
    """
    url_lower = url.lower()
    title_lower = title.lower() if title else ""

    # Primary venue — matched dynamically against the user's URL
    if primary_domain and _same_site(_get_domain(url), primary_domain):
        return "Primary Venue"

    # Search-engine redirect / tracking links (google.com/goto?url=..., /url?q=...)
    host = _get_domain(url)
    if (host.startswith("google.") or ".google." in host or host in ("bing.com", "duckduckgo.com")
            or "/goto?" in url_lower or "/url?" in url_lower):
        return "Directory"

    # ========== NON-BUSINESS FILTERS (Strict) ==========
    
    # Wikipedia and encyclopedias
    if any(x in url_lower for x in ["wikipedia.org", "wikia.com", "fandom.com", "britannica.com"]):
        return "Encyclopedia"
    
    # Forums and Q&A sites
    if any(x in url_lower for x in ["reddit.com", "quora.com", "stackexchange.com", "answers.com", "forum"]):
        return "Forum"
    
    # Social media platforms
    if any(x in url_lower for x in ["facebook.com", "instagram.com", "tiktok.com", "twitter.com", "linkedin.com", "pinterest.com"]):
        return "Social"
    
    # Video platforms
    if any(x in url_lower for x in ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com"]):
        return "Social"
    
    # Business profile / directory / data aggregator sites
    if any(x in url_lower for x in [
        "tripadvisor", "yelp", "zomato", "foursquare", "trustpilot",
        "google.com/maps", "newzealand.com", "aucklandnz.com",
        "booking.com", "expedia",
        # B2B / company profile directories
        "zoominfo.com", "crunchbase.com", "pitchbook.com", "owler.com",
        "dnb.com", "craft.co", "similarweb.com", "semrush.com",
        "glassdoor.com", "indeed.com", "clutch.co", "g2.com",
        "capterra.com", "getapp.com", "softwareadvice.com",
        "bloomberg.com", "reuters.com", "businesswire.com", "prnewswire.com",
        "globenewswire.com", "accesswire.com",
        "cbinsights.com", "marketing91.com", "growjo.com", "macrotrends.net",
        "comparably.com", "stockanalysis.com", "wisesheets.io",
    ]):
        return "Directory"

    # News and blog platforms
    if any(x in url_lower for x in [
        "medium.com", "wordpress.com", "blogger.com", "tumblr.com",
        "/blog/", "/news/", "/article/", "/press-release/", "/partner",
        "/glossary", "/ref/", "/articles/", "/posts/", "/guides/", "/reviews/",
        "alternative", "-vs-", "/compare",
        "nzherald", "stuff.co.nz", "techcrunch.com", "forbes.com",
        "businessinsider.com", "wsj.com", "ft.com", "economist.com",
    ]):
        return "Content"

    # E-commerce platforms
    if any(x in url_lower for x in ["amazon.", "ebay.", "trademe.co.nz", "etsy."]):
        return "Marketplace"

    # Gaming / esports / unrelated platforms
    if any(x in url_lower for x in [
        "steampowered.com", "steam.com", "epicgames.com", "xbox.com",
        "playstation.com", "nintendo.com", "twitch.tv", "discord.com",
        "esports", "gaming", "tokopedia", "shopee.", "lazada.", "aliexpress.",
        "flipkart.", "myntra.", "ajio.", "meesho.",
    ]):
        return "Marketplace"

    # Maintenance / error pages in title
    if any(x in title_lower for x in [
        "down for maintenance", "403 forbidden", "404 not found",
        "access denied", "site unavailable", "coming soon",
    ]):
        return "Content"

    # Government and education sites
    if any(x in url_lower for x in [".gov", ".edu", ".ac.nz"]):
        return "Institutional"

    # ========== BUSINESS VALIDATION ==========
    
    # Check if it looks like a real business website
    # Real businesses typically have:
    # - Their own domain (not subdomains of platforms)
    # - Business-related keywords in title
    # - Not generic listing pages
    
    # Filter out listicles, press releases, partnership announcements
    if any(x in title_lower for x in [
        "top 10", "best ", "guide to", "how to find", "vs ", "comparison",
        "partners with", "fund partners", "raises ", "acquires ", "launches ",
        "overview, news", "company profile", "valuation, funding",
        "jobs (now hiring)", "jobs near you",
    ]):
        return "Content"
    
    # At this point, it's likely a direct competitor
    return "Direct Competitor"


def get_domain(url):
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def build_full_serp_table(results, primary_url=""):
    """Build table with all SERP results"""
    primary_domain = _get_domain(primary_url) if primary_url else ""
    rows = []
    for i, item in enumerate(results, start=1):
        comp_type = classify_competitor(item["link"], item.get("title", ""), primary_domain)
        rows.append({
            "SERP Rank": i,
            "Title": item.get("title", ""),
            "Link": item.get("link", ""),
            "Type": comp_type,
            "Snippet": item.get("snippet", "")
        })
    return rows


def filter_direct_competitors(results, primary_url=""):
    """Direct competitors only (real businesses), one entry per domain.

    The primary site and its subdomains are excluded — /competitors analyses the
    primary separately, so keeping it here listed the user's own site as a rival.
    """
    primary_domain = _get_domain(primary_url) if primary_url else ""
    filtered = []
    seen_domains = set()
    direct_rank = 1
    for i, item in enumerate(results, start=1):
        comp_type = classify_competitor(item["link"], item.get("title", ""), primary_domain)
        if comp_type == "Direct Competitor":
            domain = _get_domain(item.get("link", ""))
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            filtered.append({
                "Direct Rank": direct_rank,
                "SERP Rank": i,
                "Title": item.get("title", ""),
                "Link": item.get("link", ""),
                "Type": comp_type,
                "Snippet": item.get("snippet", ""),
                "Domain": get_domain(item.get("link", ""))
            })
            direct_rank += 1
    return filtered


def get_top_n_external_direct_competitors(results, n=3, primary_url=""):
    """Get top N direct competitors, excluding the primary venue's own domain"""
    primary_domain = _get_domain(primary_url) if primary_url else ""
    external = []
    for i, item in enumerate(results, start=1):
        comp_type = classify_competitor(item["link"], item.get("title", ""), primary_domain)
        if comp_type == "Direct Competitor":
            external.append({
                "SERP Rank": i,
                "Title": item.get("title", ""),
                "Link": item.get("link", ""),
                "Type": comp_type,
                "Snippet": item.get("snippet", ""),
                "Domain": get_domain(item.get("link", ""))
            })
    return external[:n]


def get_primary_result(results, primary_url=""):
    """Find the primary venue in SERP results by matching domain"""
    primary_domain = _get_domain(primary_url) if primary_url else ""
    for i, item in enumerate(results, start=1):
        comp_type = classify_competitor(item["link"], item.get("title", ""), primary_domain)
        if comp_type == "Primary Venue":
            return {
                "SERP Rank": i,
                "Title": item.get("title", ""),
                "Link": item.get("link", ""),
                "Type": comp_type,
                "Snippet": item.get("snippet", ""),
                "Domain": get_domain(item.get("link", ""))
            }
    return None


def get_competitors_via_gemini(url, keyword, gemini_api_key, location=None, serp_results=None):
    """
    Use Gemini REST API directly to identify real direct competitor brands.
    serp_results: optional list of pre-filtered SERP items (direct competitors only).
    Returns a list of dicts: [{"name": "...", "domain": "...", "website": "..."}]
    """
    import requests as _req

    domain = _get_domain(url)

    # ── Geography — prefer geolocation data, fall back to TLD ──
    tld = domain.split(".")[-1].lower()
    tld_country_map = {
        "co.nz": "New Zealand", "nz": "New Zealand",
        "com.au": "Australia",  "au": "Australia",
        "co.uk": "United Kingdom", "uk": "United Kingdom",
        "ca": "Canada", "ie": "Ireland", "sg": "Singapore",
        "co.in": "India", "in": "India",
    }
    two_part = ".".join(domain.split(".")[-2:])
    country = tld_country_map.get(two_part) or tld_country_map.get(tld) or ""
    city = ""
    if location:
        country = location.get("country_name") or country
        city    = location.get("city") or ""

    geo_line = ""
    if city and country:
        geo_line = f"Market: {city}, {country}"
    elif country:
        geo_line = f"Market: {country}"

    # ── Keyword intent classification ──
    _informational_signals = ["how", "what", "why", "guide", "tips", "ideas", "best", "top", "review"]
    _keyword_lower = keyword.lower()
    _is_informational = any(w in _keyword_lower for w in _informational_signals)
    intent_note = (
        "NOTE: The keyword appears informational. Focus on brands whose WEBSITES compete "
        "for this keyword (e.g. content-heavy brands with blog/resource sections), "
        "not just transactional e-commerce competitors."
        if _is_informational else
        "NOTE: The keyword is commercial/transactional. Focus on brands that sell "
        "directly to customers and would bid on or rank for this keyword."
    )

    from ai.gemini import sanitize_for_prompt, untrusted_block
    safe_kw = sanitize_for_prompt(keyword)
    safe_domain = sanitize_for_prompt(domain, 100)
    geo_line = sanitize_for_prompt(geo_line)

    # ── SERP context — filtered direct competitors only ──
    serp_section = ""
    if serp_results:
        filtered = [r for r in serp_results if classify_competitor(
            r.get("link",""), r.get("title",""), domain
        ) == "Direct Competitor"][:12]
        if filtered:
            serp_lines = "\n".join(
                f"  {i+1}. {sanitize_for_prompt(r.get('title',''), 120)} — {sanitize_for_prompt(r.get('link',''), 200)}"
                for i, r in enumerate(filtered)
            )
            serp_section = f"""
GOOGLE SERP — sites currently ranking for "{safe_kw}" (direct business competitors only, noise already removed):
{serp_lines}

These are CONFIRMED ranking competitors — include all of them plus any other known direct competitors you are aware of.
"""

    data = f"""BUSINESS: {sanitize_for_prompt(url)}
DOMAIN: {safe_domain}
TARGET KEYWORD: "{safe_kw}"
{geo_line}
{serp_section}"""

    prompt = f"""You are a senior competitive intelligence analyst. Your task is to identify DIRECT BRAND competitors for the business below with maximum accuracy.

{untrusted_block(data)}

{intent_note}

WHAT COUNTS AS A DIRECT COMPETITOR:
- A real company with its own website that sells the same/very similar products or services
- Targets the same customers in the same geographic market
- Would appear on the same search results page for the target keyword
- Has meaningful market presence (not a one-person blog or hobby site)

STRICT EXCLUSIONS — do NOT include:
- The business itself ({safe_domain})
- Wikipedia, Reddit, Quora, forums, Q&A sites
- YouTube, TikTok, Instagram, Facebook, any social media
- News sites, press releases, media publications
- Directories: Yelp, TripAdvisor, Google Maps, Yellow Pages, Trustpilot
- Job boards, analyst reports, financial data sites
- Brands that do NOT actively operate in {country or "the target market"}

OUTPUT RULES:
- Include ALL direct competitors you can identify — do not cap the list
- Prefer country-specific domains where they exist (e.g. nz.brand.com over brand.com for NZ market)
- If a SERP list is provided above, all those sites must be in your output
- Return ONLY a single-line compact JSON array, no explanation, no markdown:

[{{"name":"BrandName","domain":"example.com","website":"https://example.com"}}]"""

    from ai.gemini import generate_text, GeminiError
    try:
        text = generate_text(gemini_api_key, prompt, temperature=0.1,
                             max_output_tokens=8192, timeout=30)
    except GeminiError as e:
        # serp_utils.progressive_competitor_search catches RuntimeError and
        # falls back to plain SERP search — keep the old error prefixes.
        prefix = {"invalid_key": "INVALID_API_KEY", "quota": "QUOTA_429", "billing": "BILLING_402"}.get(e.kind, "ALL_FAILED")
        raise RuntimeError(f"{prefix}||{e}") from e

    competitors = _extract_json_list(text)
    if competitors is None:
        raise RuntimeError(f"ALL_FAILED||Could not extract JSON list. Raw: {text[:300]}")
    return competitors
