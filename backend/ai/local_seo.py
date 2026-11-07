"""
Local SEO analyzer — checks NAP consistency, local schema, and geo signals.
"""

import re
import json

# Top 20 world cities for geo signal detection
_CITIES = [
    "new york", "london", "paris", "tokyo", "dubai", "sydney", "toronto",
    "berlin", "singapore", "amsterdam", "chicago", "los angeles", "miami",
    "barcelona", "rome", "seoul", "mumbai", "shanghai", "mexico city", "dubai",
]

_COUNTRIES = [
    "united states", "usa", "united kingdom", "uk", "australia", "canada",
    "germany", "france", "japan", "india", "china", "brazil", "spain",
    "italy", "netherlands", "singapore", "new zealand", "south africa",
]

_LOCAL_BUSINESS_TYPES = {
    "localbusiness", "restaurant", "store", "cafe", "hotel", "bar",
    "gym", "dentist", "doctor", "hospital", "school", "plumber",
    "electrician", "lawyer", "realestateagent", "foodestablishment",
    "medicalorganization", "autodealer", "bankortypeof", "beautysalon",
}


_DATE_RE = re.compile(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b")
# A number written the way businesses show phones: optional +country code, then
# groups of digits split by spaces, dashes, dots or brackets — 8 to 15 digits in all.
_PHONE_RE = re.compile(r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{1,5}\)?[\s.-]?){2,5}\d{2,5}(?!\w)")


def _has_phone(soup, page_text: str) -> bool:
    """Tap-to-call links, or a phone-shaped number in the text (any country format:
    NZ "07 834 9293", AU "(02) 9876 5432", US "555-123-4567", "+44 20 7946 0958")."""
    try:
        if soup is not None and soup.select_one('a[href^="tel:"]'):
            return True
    except Exception:
        pass
    text = _DATE_RE.sub(" ", page_text or "")
    for m in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        raw = m.group(0).strip()
        if not (8 <= len(digits) <= 15 and re.search(r"[\s.()-]", raw)):
            continue
        # Local/international formats start with 0, + or a bracketed area code;
        # US numbers have the 3-3-4 shape. Years and prices ("2022 2023 2024") don't.
        if raw[0] in "0+(" or re.fullmatch(r"\d{3}[\s.-]\d{3}[\s.-]\d{4}", raw):
            return True
    return False


def analyze_local_seo(url: str, soup, page_text: str) -> dict:
    """
    Returns:
    {
        local_score: int (0-100),
        nap: { phone_found: bool, address_found: bool, business_name_found: bool },
        local_schema: { has_local_business: bool, has_geo: bool, schema_types: list },
        geo_signals: { has_location_keyword: bool, city_mentions: list, country_mentions: list },
        google_maps_embed: bool,
        local_checks: list of { label, pass, importance }
        quick_fixes: list of str
    }
    """
    text_lower = page_text.lower()

    # ── NAP Detection ─────────────────────────────────────────────────────────
    phone_found = _has_phone(soup, page_text)

    address_pattern = r'\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Blvd|Boulevard|Way|Court|Ct)\b'
    address_found = bool(re.search(address_pattern, page_text, re.IGNORECASE))

    # Business name: title/H1 has >3 meaningful words (not all generic)
    title_tag = soup.find("title")
    h1_tags = soup.find_all("h1")
    business_name_text = ""
    if title_tag:
        business_name_text = title_tag.get_text(" ", strip=True)
    elif h1_tags:
        business_name_text = h1_tags[0].get_text(" ", strip=True)

    generic_words = {"home", "welcome", "index", "page", "website", "site", "the", "a", "an"}
    name_words = [w for w in business_name_text.lower().split() if w not in generic_words and len(w) > 2]
    business_name_found = len(name_words) >= 3

    nap = {
        "phone_found": phone_found,
        "address_found": address_found,
        "business_name_found": business_name_found,
    }

    # ── Local Schema Detection ─────────────────────────────────────────────────
    schema_types = []
    has_local_business = False
    has_geo = False

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle both single object and @graph arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                t = item.get("@type", "")
                types = t if isinstance(t, list) else [t]
                for typ in types:
                    if typ:
                        schema_types.append(typ)
                        if typ.lower() in _LOCAL_BUSINESS_TYPES:
                            has_local_business = True
                if "geo" in item or "latitude" in item or "longitude" in item:
                    has_geo = True
                # nested @graph
                if "@graph" in item:
                    for node in item["@graph"]:
                        node_type = node.get("@type", "")
                        ntypes = node_type if isinstance(node_type, list) else [node_type]
                        for nt in ntypes:
                            if nt:
                                schema_types.append(nt)
                                if nt.lower() in _LOCAL_BUSINESS_TYPES:
                                    has_local_business = True
                        if "geo" in node or "latitude" in node:
                            has_geo = True
        except Exception:
            pass

    local_schema = {
        "has_local_business": has_local_business,
        "has_geo": has_geo,
        "schema_types": list(set(schema_types)),
    }

    # ── Geo Signals ──────────────────────────────────────────────────────────
    city_mentions = [city for city in _CITIES if city in text_lower]
    country_mentions = [country for country in _COUNTRIES if country in text_lower]

    location_keywords = ["near me", "nearby", "local", "serving", "in the area", "our location", "visit us", "find us"]
    has_location_keyword = any(kw in text_lower for kw in location_keywords)

    geo_signals = {
        "has_location_keyword": has_location_keyword,
        "city_mentions": city_mentions,
        "country_mentions": country_mentions,
    }

    # ── Google Maps Embed ────────────────────────────────────────────────────
    google_maps_embed = False
    for tag in soup.find_all(["iframe", "a"]):
        src = tag.get("src", "") or tag.get("href", "") or ""
        if "maps.google.com" in src or "google.com/maps" in src:
            google_maps_embed = True
            break

    # ── Build Checks ─────────────────────────────────────────────────────────
    local_checks = [
        {"label": "Phone number on page",        "pass": phone_found,           "importance": "HIGH"},
        {"label": "Street address on page",      "pass": address_found,         "importance": "HIGH"},
        {"label": "Business name identifiable",  "pass": business_name_found,   "importance": "MEDIUM"},
        {"label": "LocalBusiness schema markup", "pass": has_local_business,    "importance": "HIGH"},
        {"label": "Geo coordinates in schema",   "pass": has_geo,               "importance": "MEDIUM"},
        {"label": "Google Maps embed/link",      "pass": google_maps_embed,     "importance": "MEDIUM"},
        {"label": "Location keyword signals",    "pass": has_location_keyword,  "importance": "LOW"},
        {"label": "City mentioned on page",      "pass": len(city_mentions) > 0,"importance": "MEDIUM"},
    ]

    # ── Score ─────────────────────────────────────────────────────────────────
    weights = {
        "HIGH": 20,
        "MEDIUM": 12,
        "LOW": 6,
    }
    total_weight = sum(weights[c["importance"]] for c in local_checks)
    earned = sum(weights[c["importance"]] for c in local_checks if c["pass"])
    local_score = round((earned / total_weight) * 100) if total_weight else 0

    # ── Quick Fixes ──────────────────────────────────────────────────────────
    quick_fixes = []
    if not phone_found:
        quick_fixes.append("Add a local phone number in the page footer or contact section.")
    if not address_found:
        quick_fixes.append("Include your full street address (e.g. 123 Main Street) on the page.")
    if not business_name_found:
        quick_fixes.append("Make your business name clear in the page title or H1 heading.")
    if not has_local_business:
        quick_fixes.append('Add LocalBusiness JSON-LD schema (use the Schema tool above to generate one).')
    if not has_geo:
        quick_fixes.append("Add latitude/longitude coordinates to your LocalBusiness schema.")
    if not google_maps_embed:
        quick_fixes.append("Embed a Google Maps widget or add a directions link to help customers find you.")
    if not has_location_keyword:
        quick_fixes.append('Use location phrases like "near me", "serving [city]", or "visit us at" in your copy.')
    if not city_mentions:
        quick_fixes.append("Mention the city or region you serve in your page content.")

    return {
        "local_score":       local_score,
        "nap":               nap,
        "local_schema":      local_schema,
        "geo_signals":       geo_signals,
        "google_maps_embed": google_maps_embed,
        "local_checks":      local_checks,
        "quick_fixes":       quick_fixes,
    }
