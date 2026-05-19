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
        if 'location' in location_params:
            payload['location'] = location_params['location']  # City, Country
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("organic", [])
            
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = (attempt + 1) * 2
                time.sleep(wait_time)
                continue
            
            else:
                raise Exception(f"SERPER API error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                raise Exception("SERPER API timeout after multiple retries")
        
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                raise e
    
    raise Exception("Failed to fetch SERP results after all retries")


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

    Strategy:
      1. related:{domain} — Google's own "find similar sites" signal
      2. keyword + domain name hint — contextual keyword search
      3. Raw keyword global fallback

    Returns:
        Tuple of (all_results, direct_competitors, search_log, location_msg)
    """
    from location_utils import get_location_from_url

    domain = _extract_domain(url) if url else ""
    domain_hint = domain.split(".")[0] if domain else ""

    location = get_location_from_url(url) if url else None
    search_log = []
    all_results = []
    direct_competitors = []

    # LEVEL 0: Gemini AI — asks LLM to identify real competitors by name/domain
    if gemini_api_key:
        from competitor_utils import get_competitors_via_gemini
        search_log.append(f"🤖 Using AI to identify competitors for {domain}...")
        gemini_competitors = get_competitors_via_gemini(url, keyword, gemini_api_key, location)

        if gemini_competitors:
            # Search SERP for each competitor domain to get live data
            for comp in gemini_competitors:
                comp_domain = comp.get("domain", "")
                comp_name = comp.get("name", "")
                if not comp_domain:
                    continue
                try:
                    results = get_serp_results(f"site:{comp_domain}", api_key)
                    if results:
                        # Take the top result for this domain
                        all_results.append(results[0])
                    else:
                        # No SERP data — build a synthetic entry from Gemini data
                        all_results.append({
                            "title": comp_name,
                            "link": comp.get("website", f"https://{comp_domain}"),
                            "snippet": f"Competitor identified by AI: {comp_name}",
                        })
                except Exception:
                    all_results.append({
                        "title": comp_name,
                        "link": comp.get("website", f"https://{comp_domain}"),
                        "snippet": f"Competitor identified by AI: {comp_name}",
                    })

            direct_competitors = filter_func(all_results, primary_url=url)
            if len(direct_competitors) >= min_competitors:
                return all_results, direct_competitors, search_log, f"🤖 AI-identified competitors for {domain}"

            search_log.append(f"⚠️ AI found {len(direct_competitors)} competitors, supplementing with search...")

    # LEVEL 1: related:{domain} — finds genuinely similar websites
    if domain:
        search_query = f"related:{domain}"
        search_log.append(f"🔍 Searching: {search_query}")
        all_results = get_serp_results(search_query, api_key)
        direct_competitors = filter_func(all_results, primary_url=url)

        if len(direct_competitors) >= min_competitors:
            return all_results, direct_competitors, search_log, f"🌐 Sites similar to {domain}"

        search_log.append(f"⚠️ Only {len(direct_competitors)} found via related search, expanding...")

    # LEVEL 2: keyword + domain hint (e.g. "data leader parrotanalytics alternatives")
    if domain_hint:
        search_query = f"{keyword} {domain_hint} alternatives competitors"
        search_log.append(f"🔄 Searching: {search_query}")

        location_params = {}
        if location:
            location_params = {'gl': location['serper_gl']}

        results2 = get_serp_results(search_query, api_key, location_params or None)
        # Merge, deduplicate by link
        seen = {r["link"] for r in all_results}
        for r in results2:
            if r["link"] not in seen:
                all_results.append(r)
                seen.add(r["link"])

        direct_competitors = filter_func(all_results, primary_url=url)

        if len(direct_competitors) >= min_competitors:
            return all_results, direct_competitors, search_log, f"🌐 Competitors of {domain}"

        search_log.append(f"⚠️ Still only {len(direct_competitors)} found, trying keyword search...")

    # LEVEL 3: Geo-aware keyword search
    if location and location.get('country_name'):
        search_query = f"{keyword} {location['country_name']}"
        search_log.append(f"🔄 Expanding to: {location['country_name']}")
        location_params = {'gl': location['serper_gl']}
        results3 = get_serp_results(search_query, api_key, location_params)
        seen = {r["link"] for r in all_results}
        for r in results3:
            if r["link"] not in seen:
                all_results.append(r)
                seen.add(r["link"])
        direct_competitors = filter_func(all_results, primary_url=url)
        if len(direct_competitors) >= min_competitors:
            return all_results, direct_competitors, search_log, f"🌍 {location['country_name']} (country-wide)"

    # LEVEL 4: Raw global keyword fallback
    search_log.append(f"🔄 Global keyword search: {keyword}")
    results4 = get_serp_results(keyword, api_key)
    seen = {r["link"] for r in all_results}
    for r in results4:
        if r["link"] not in seen:
            all_results.append(r)
            seen.add(r["link"])

    direct_competitors = filter_func(all_results, primary_url=url)
    return all_results, direct_competitors, search_log, "🌍 Global results"
