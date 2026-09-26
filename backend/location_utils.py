"""
Location detection from URLs for geo-targeted competitor search
"""

import re
from urllib.parse import urlparse


# Domain to country mapping
DOMAIN_TO_COUNTRY = {
    '.co.nz': ('NZ', 'New Zealand'),
    '.nz': ('NZ', 'New Zealand'),
    '.com.au': ('AU', 'Australia'),
    '.au': ('AU', 'Australia'),
    '.co.uk': ('GB', 'United Kingdom'),
    '.uk': ('GB', 'United Kingdom'),
    '.ca': ('CA', 'Canada'),
    '.de': ('DE', 'Germany'),
    '.fr': ('FR', 'France'),
    '.jp': ('JP', 'Japan'),
    '.cn': ('CN', 'China'),
    '.in': ('IN', 'India'),
    '.sg': ('SG', 'Singapore'),
    '.my': ('MY', 'Malaysia'),
    '.ph': ('PH', 'Philippines'),
    '.th': ('TH', 'Thailand'),
    '.vn': ('VN', 'Vietnam'),
    '.id': ('ID', 'Indonesia'),
    '.za': ('ZA', 'South Africa'),
    '.br': ('BR', 'Brazil'),
    '.mx': ('MX', 'Mexico'),
    '.com': ('US', 'United States'),  # Default
}


# Common city patterns in URLs
CITY_PATTERNS = [
    r'/locations?/([a-z-]+)',
    r'/([a-z-]+)-location',
    r'/stores?/([a-z-]+)',
    r'/([a-z-]+)-store',
    r'/([a-z]+)/?$',  # City at end of path
]


# Known cities mapping (for common variations)
CITY_MAPPINGS = {
    # New Zealand
    'auckland': 'Auckland',
    'wellington': 'Wellington',
    'christchurch': 'Christchurch',
    'hamilton': 'Hamilton',
    'tauranga': 'Tauranga',
    'dunedin': 'Dunedin',
    'palmerston-north': 'Palmerston North',
    'napier': 'Napier',
    'rotorua': 'Rotorua',
    'queenstown': 'Queenstown',
    
    # Australia
    'sydney': 'Sydney',
    'melbourne': 'Melbourne',
    'brisbane': 'Brisbane',
    'perth': 'Perth',
    'adelaide': 'Adelaide',
    'gold-coast': 'Gold Coast',
    'canberra': 'Canberra',
    
    # United States
    'new-york': 'New York',
    'nyc': 'New York',
    'los-angeles': 'Los Angeles',
    'la': 'Los Angeles',
    'chicago': 'Chicago',
    'houston': 'Houston',
    'phoenix': 'Phoenix',
    'philadelphia': 'Philadelphia',
    'san-antonio': 'San Antonio',
    'san-diego': 'San Diego',
    'dallas': 'Dallas',
    'san-jose': 'San Jose',
    'austin': 'Austin',
    'seattle': 'Seattle',
    'denver': 'Denver',
    'boston': 'Boston',
    'portland': 'Portland',
    'las-vegas': 'Las Vegas',
    'miami': 'Miami',
    'atlanta': 'Atlanta',
    
    # UK
    'london': 'London',
    'manchester': 'Manchester',
    'birmingham': 'Birmingham',
    'leeds': 'Leeds',
    'glasgow': 'Glasgow',
    'edinburgh': 'Edinburgh',
    'liverpool': 'Liverpool',
    'bristol': 'Bristol',
}


def detect_country_from_domain(url):
    """
    Detect country from domain extension.
    
    Args:
        url: Full URL string
        
    Returns:
        Tuple of (country_code, country_name) or ('US', 'United States') as default
    """
    url_lower = url.lower()
    
    # Check each domain pattern
    for domain, (code, name) in DOMAIN_TO_COUNTRY.items():
        if domain in url_lower:
            return code, name
    
    # Default to US
    return 'US', 'United States'


def extract_city_from_url(url):
    """
    Extract city name from URL path.
    
    Args:
        url: Full URL string
        
    Returns:
        City name (formatted) or None if not found
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Try each pattern
        for pattern in CITY_PATTERNS:
            match = re.search(pattern, path)
            if match:
                city_slug = match.group(1)
                
                # Look up in mappings
                if city_slug in CITY_MAPPINGS:
                    return CITY_MAPPINGS[city_slug]
                
                # Otherwise title-case it
                return city_slug.replace('-', ' ').title()
        
        return None
        
    except Exception:
        return None


def get_location_from_url(url):
    """
    Extract full location (city + country) from URL.
    
    Args:
        url: Full URL string
        
    Returns:
        Dictionary with:
        {
            'country_code': 'NZ',
            'country_name': 'New Zealand',
            'city': 'Auckland',
            'location_string': 'Auckland, New Zealand',
            'serper_gl': 'nz',
            'serper_location': 'Auckland, New Zealand'
        }
    """
    country_code, country_name = detect_country_from_domain(url)
    city = extract_city_from_url(url)
    
    # Build location string
    if city:
        location_string = f"{city}, {country_name}"
    else:
        location_string = country_name
    
    return {
        'country_code': country_code,
        'country_name': country_name,
        'city': city,
        'location_string': location_string,
        'serper_gl': country_code.lower(),
        'serper_location': location_string
    }


def format_location_display(location_info):
    """
    Format location for display to user.
    
    Args:
        location_info: Dictionary from get_location_from_url()
        
    Returns:
        Formatted string like "🌍 Searching from: Auckland, New Zealand"
    """
    if location_info['city']:
        return f"🌍 Searching from: {location_info['city']}, {location_info['country_name']}"
    else:
        return f"🌍 Searching from: {location_info['country_name']}"


# Example usage:
if __name__ == "__main__":
    test_urls = [
        "https://holeymoley.co.nz/locations/auckland",
        "https://wendys.com/locations/new-york",
        "https://mcdonalds.co.uk/london",
        "https://kfc.com.au/sydney",
        "https://pizzahut.co.nz/wellington",
        "https://subway.com",
    ]
    
    for url in test_urls:
        location = get_location_from_url(url)
        print(f"\n{url}")
        print(f"  → {format_location_display(location)}")
        print(f"  → SERPER params: gl={location['serper_gl']}, location={location['serper_location']}")
