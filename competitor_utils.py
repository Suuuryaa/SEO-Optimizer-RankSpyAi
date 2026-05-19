from urllib.parse import urlparse
import json


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


def get_competitors_via_gemini(url, keyword, gemini_api_key, location=None):
    """
    Use Gemini to identify real competitor brands/domains for a given URL.
    Returns a list of dicts: [{"name": "...", "domain": "...", "website": "..."}]
    """
    try:
        from google import genai

        country_hint = ""
        if location and location.get("country_name"):
            country_hint = f"The business operates in {location['country_name']}. Prioritise competitors active in that market with local domains where possible."

        domain = _get_domain(url)

        prompt = f"""You are a competitive intelligence analyst.

Given this business website: {url} (domain: {domain})
Target keyword context: "{keyword}"
{country_hint}

Identify 6-8 DIRECT competitor businesses — companies that sell similar products/services and compete for the same customers.
Do NOT include: directories, review sites, news sites, social media, analyst platforms (CBInsights, Crunchbase, G2), or the business itself.

Return ONLY a valid JSON array with no markdown fences or explanation:
[
  {{"name": "Brand Name", "domain": "example.com", "website": "https://example.com"}},
  ...
]"""

        client = genai.Client(api_key=gemini_api_key)

        # Try models in order of preference
        for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                break
            except Exception:
                continue
        else:
            return []

        text = response.text.strip()
        # Strip markdown code fences if present
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        competitors = json.loads(text)
        return competitors if isinstance(competitors, list) else []

    except Exception as e:
        # Return error info so caller can surface it
        raise RuntimeError(f"Gemini competitor lookup failed: {e}")
