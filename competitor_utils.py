from urllib.parse import urlparse


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
    
    # Review/directory sites (not actual competitors)
    if any(x in url_lower for x in ["tripadvisor", "yelp", "zomato", "foursquare", "trustpilot", 
                                     "google.com/maps", "newzealand.com", "aucklandnz.com", 
                                     "booking.com", "expedia"]):
        return "Directory"
    
    # News and blog platforms
    if any(x in url_lower for x in ["medium.com", "wordpress.com", "blogger.com", "tumblr.com",
                                     "/blog/", "/news/", "/article/", "nzherald", "stuff.co.nz"]):
        return "Content"
    
    # E-commerce platforms (unless they ARE the business)
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
    
    # Filter out generic "best of" or "top 10" listicles
    if any(x in title_lower for x in ["top 10", "best", "guide to", "how to find", "vs", "comparison"]):
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
