import requests
import time

def get_serp_results(keyword, api_key, location_params=None, max_retries=3):
    """
    Fetch SERP results from SERPER API with optional geo-targeting.
    
    Args:
        keyword: Search keyword
        api_key: SERPER API key
        location_params: Optional dict with 'gl' and 'location' for geo-targeting
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of search results
    """
    url = "https://google.serper.dev/search"
    
    # Base payload
    payload = {
        "q": keyword,
        "num": 10  # Top 10 results
    }
    
    # Add geo-targeting if provided
    if location_params:
        if 'gl' in location_params:
            payload['gl'] = location_params['gl']  # Country code
        if location_params.get('hl'):
            payload['hl'] = location_params['hl']  # Interface language
        if 'location' in location_params:
            payload['location'] = location_params['location']  # City, Country
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    # Retry only what can succeed on a second try: 429, 5xx, timeouts and
    # connection drops. Other errors (400 bad key/query, 403) fail at once.
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

        if response.status_code == 200:
            return response.json().get("organic", [])
        if response.status_code == 429 or response.status_code >= 500:
            last_error = Exception(f"SERPER API error: {response.status_code}")
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
            continue
        raise Exception(f"SERPER API error: {response.status_code}")

    raise Exception(f"Failed to fetch SERP results after {max_retries} attempts: {last_error}")


def _extract_domain(url):
    """Extract bare domain from URL for use in search queries."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path
        return netloc.replace("www.", "").split("/")[0]
    except Exception:
        return ""


def progressive_competitor_search(url, keyword, api_key, filter_func, min_competitors=5, gemini_api_key=None):
    """
    Find real business competitors for the given URL/keyword.

    Strategy (every search uses the site's country, gl/hl):
      0. Gemini names rivals (when a key is available)
      1. "{brand} competitors {country}"
      2. "{brand} alternatives"

    Returns:
        Tuple of (all_results, direct_competitors, search_log, location_msg)
    """
    from location_utils import get_location_from_url

    domain = _extract_domain(url) if url else ""
    domain_hint = domain.split(".")[0] if domain else ""

    location = get_location_from_url(url) if url else None
    location_params = ({'gl': location['serper_gl'], 'hl': location.get('serper_hl')}
                       if location else {'gl': 'us'})
    search_log = []
    all_results = []
    direct_competitors = []

    # LEVEL 0: Gemini AI — asks LLM to identify real local competitors by name/domain
    if not gemini_api_key:
        search_log.append("⚠️ No Gemini API key configured — using search-based discovery")

    if gemini_api_key:
        from competitor_utils import get_competitors_via_gemini
        search_log.append(f"🤖 Asking AI: who are local competitors of {domain} for '{keyword}'?")
        try:
            gemini_competitors = get_competitors_via_gemini(url, keyword, gemini_api_key, location)
        except RuntimeError as e:
            search_log.append(f"⚠️ AI lookup unavailable (quota/rate limit), falling back to search...")
            gemini_competitors = []
        except Exception as e:
            search_log.append(f"⚠️ AI lookup failed ({e}), falling back to search...")
            gemini_competitors = []

        if gemini_competitors:
            # Build synthetic SERP-style entries directly from Gemini — no extra API calls
            for comp in gemini_competitors:
                comp_domain = comp.get("domain", "")
                comp_name = comp.get("name", "")
                if not comp_domain:
                    continue
                all_results.append({
                    "title": comp_name,
                    "link": comp.get("website", f"https://{comp_domain}"),
                    "snippet": f"Direct competitor identified by AI for '{keyword}'.",
                })

            direct_competitors = filter_func(all_results, primary_url=url)
            if len(direct_competitors) >= min_competitors:
                return all_results, direct_competitors, search_log, f"🤖 AI-identified competitors for {domain}"

            search_log.append(f"⚠️ AI found {len(direct_competitors)} competitors, supplementing with search...")

    # LEVEL 2: "{brand} competitors {country}" — domain-contextual, ignores misleading keyword
    if domain_hint:
        country_str = location['country_name'] if location and location.get('country_name') else ""
        search_query = f"{domain_hint} competitors {country_str}".strip()
        search_log.append(f"🔄 Searching: {search_query}")

        results2 = get_serp_results(search_query, api_key, location_params)
        seen = {r["link"] for r in all_results}
        for r in results2:
            if r["link"] not in seen:
                all_results.append(r)
                seen.add(r["link"])

        direct_competitors = filter_func(all_results, primary_url=url)
        if len(direct_competitors) >= min_competitors:
            return all_results, direct_competitors, search_log, f"🌐 Competitors of {domain}"

        search_log.append(f"⚠️ Still only {len(direct_competitors)} found, expanding...")

    # LEVEL 3: "{brand} alternatives" global
    if domain_hint:
        search_query = f"{domain_hint} alternatives"
        search_log.append(f"🔄 Searching: {search_query}")
        results3 = get_serp_results(search_query, api_key, location_params)
        seen = {r["link"] for r in all_results}
        for r in results3:
            if r["link"] not in seen:
                all_results.append(r)
                seen.add(r["link"])
        direct_competitors = filter_func(all_results, primary_url=url)
        if len(direct_competitors) >= min_competitors:
            return all_results, direct_competitors, search_log, f"🌍 Global competitors of {domain}"

    direct_competitors = filter_func(all_results, primary_url=url)
    return all_results, direct_competitors, search_log, "🌍 Global results"
