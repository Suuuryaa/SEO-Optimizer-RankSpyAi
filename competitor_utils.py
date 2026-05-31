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


def classify_competitor(url, title="", primary_domain=""):
    """
    Classify a SERP result. Returns one of:
      Primary Venue, Social, Encyclopedia, Forum, Directory,
      Institutional, Marketplace, Content, Direct Competitor
    """
    url_lower = url.lower()
    title_lower = title.lower() if title else ""

    # Primary venue — matched dynamically against the user's URL
    if primary_domain and _get_domain(url) == primary_domain:
        return "Primary Venue"

    # ========== NON-BUSINESS FILTERS (Strict) ==========
    
    # Wikipedia and encyclopedias
    if any(x in url_lower for x in [
        "wikipedia.org", "wikia.com", "fandom.com", "britannica.com",
        "dictionary.com", "merriam-webster.com", "dictionary.cambridge.org",
        "oxfordlearnersdictionaries.com", "thefreedictionary.com",
        "collinsdictionary.com", "macmillandictionary.com",
    ]):
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

    # Gaming and entertainment platforms
    if any(x in url_lower for x in [
        "store.steampowered.com", "steampowered.com", "epicgames.com",
        "itch.io", "gog.com", "humblebundle.com", "origin.com",
        "gamespot.com", "ign.com", "pcgamer.com",
    ]):
        return "Content"
    
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
        "nzherald", "stuff.co.nz", "techcrunch.com", "forbes.com",
        "businessinsider.com", "wsj.com", "ft.com", "economist.com",
    ]):
        return "Content"

    # E-commerce platforms
    if any(x in url_lower for x in ["amazon.", "ebay.", "trademe.co.nz", "etsy."]):
        return "Marketplace"

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
    """Filter to show only direct competitors (real businesses)"""
    primary_domain = _get_domain(primary_url) if primary_url else ""
    filtered = []
    direct_rank = 1
    for i, item in enumerate(results, start=1):
        comp_type = classify_competitor(item["link"], item.get("title", ""), primary_domain)
        if comp_type in ["Direct Competitor", "Primary Venue"]:
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

    # ── SERP context — all results, Gemini decides what's relevant ──
    serp_section = ""
    if serp_results:
        serp_lines = "\n".join(
            f"  {i+1}. {r.get('title','').strip()} — {r.get('link','')}"
            for i, r in enumerate(serp_results[:15])
        )
        serp_section = f"""
GOOGLE SERP — raw results currently ranking for "{keyword}":
{serp_lines}

Review these results. Include any that are genuine direct business competitors of {domain}. Ignore dictionaries, forums, social media, gaming sites, news articles, and any non-business pages.
"""

    prompt = f"""You are a senior competitive intelligence analyst. Identify DIRECT competitors for the business below.

BUSINESS URL: {url}
DOMAIN: {domain}
TARGET KEYWORD: "{keyword}"
{geo_line}

{serp_section}
{intent_note}

STEP 1 — Understand the business:
Look at {domain} and determine: what industry/category is this business in? What does it sell or offer?
Use this to anchor your competitor search — only return brands in the SAME industry.

STEP 2 — A site qualifies as a DIRECT COMPETITOR only if ALL of these are true:
✓ It is a real company with its own website (not a platform, directory, or aggregator)
✓ It sells the same or very similar products/services as {domain}
✓ It targets the same type of customer in the same geographic market
✓ It has a working, indexable website with meaningful content
✓ You are confident the domain is correct and the site is live

STEP 3 — HARD EXCLUSIONS — reject immediately, no exceptions:
✗ {domain} itself
✗ Dictionaries, encyclopedias (Wikipedia, Merriam-Webster, Cambridge Dictionary, etc.)
✗ Forums, Q&A, Reddit, Quora
✗ Social media (Facebook, Instagram, TikTok, LinkedIn, Pinterest, YouTube)
✗ Gaming platforms (Steam, Epic Games, etc.)
✗ News, media, press release sites
✗ Review/directory sites (Yelp, TripAdvisor, Trustpilot, Google Maps)
✗ Job boards, financial data, analyst reports
✗ Any site that does NOT sell products/services in the same category as {domain}
✗ Any domain you are not confident exists and is correct

OUTPUT RULES:
- Aim for 6–12 genuine competitors; fewer is better than including noise
- Prefer country-specific domains (e.g. nz.brand.com, brand.co.nz for NZ market)
- If unsure whether a site belongs, exclude it
- Return ONLY a compact single-line JSON array, no explanation, no markdown:

[{{"name":"BrandName","domain":"example.com","website":"https://example.com"}}]"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }

    # Discover available models for this API key — also validates the key early
    available_models = []
    for api_ver in ["v1beta", "v1"]:
        try:
            list_resp = _req.get(
                f"https://generativelanguage.googleapis.com/{api_ver}/models?key={gemini_api_key}",
                timeout=15
            )
            if list_resp.status_code == 401:
                raise RuntimeError(
                    "INVALID_API_KEY_401: Gemini API key is invalid or not authorised. "
                    "Check that GEMINI_API_KEY is correctly set in Streamlit Cloud secrets."
                )
            if list_resp.status_code == 403:
                raise RuntimeError(
                    "FORBIDDEN_403: Generative Language API not enabled for this key/project. "
                    "Enable it at console.cloud.google.com → APIs & Services."
                )
            if list_resp.status_code == 200:
                all_models = list_resp.json().get("models", [])
                available_models = [
                    m["name"].replace("models/", "")
                    for m in all_models
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                    and "gemini" in m.get("name", "").lower()
                ]
                if available_models:
                    available_models.sort(key=lambda x: (
                        0 if "flash" in x else 1,
                        0 if "2.0" in x else (1 if "1.5" in x else 2)
                    ))
                    break
        except RuntimeError:
            raise
        except Exception:
            pass

    # Fallback list if discovery network-fails (gemini-pro bare alias excluded — needs OAuth on v1)
    if not available_models:
        available_models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]

    last_error = None
    quota_errors = []

    for model in available_models[:8]:
        for api_ver in ["v1beta", "v1"]:
            endpoint = (
                f"https://generativelanguage.googleapis.com/{api_ver}"
                f"/models/{model}:generateContent?key={gemini_api_key}"
            )
            try:
                resp = _req.post(endpoint, json=payload, timeout=30)

                if resp.status_code == 429:
                    # Don't give up — record the error and try the next model
                    quota_errors.append(f"{model}/{api_ver}: {resp.text[:200]}")
                    last_error = f"QUOTA_429||{resp.text[:400]}"
                    break  # break inner (api_ver) loop, try next model

                if resp.status_code in (401, 403):
                    # Key-level failure — no point trying more models
                    raise RuntimeError(
                        f"INVALID_API_KEY_{resp.status_code}||"
                        f"Gemini key rejected ({resp.status_code}): {resp.text[:200]}"
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    competitors = _extract_json_list(text)
                    if competitors is not None:
                        return competitors
                    last_error = f"{model}/{api_ver} → could not extract JSON list. Raw: {text[:300]}"
                    continue

                last_error = f"{model}/{api_ver} → HTTP {resp.status_code}: {resp.text[:200]}"

            except RuntimeError:
                raise
            except Exception as e:
                last_error = f"{model}/{api_ver} → {e}"

    # All models exhausted — raise with the most useful error
    if last_error and last_error.startswith("QUOTA_429||"):
        raise RuntimeError(last_error)
    raise RuntimeError(f"ALL_FAILED||Models tried: {available_models[:5]}. Last error: {last_error}")
