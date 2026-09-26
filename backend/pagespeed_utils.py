import requests


def get_pagespeed_data(url, api_key, strategy="mobile"):
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    params = {
        "url": url,
        "strategy": strategy,
        "key": api_key,
        "category": [
            "PERFORMANCE",
            "ACCESSIBILITY",
            "BEST_PRACTICES",
            "SEO"
        ]
    }

    response = requests.get(endpoint, params=params, timeout=45)
    response.raise_for_status()

    data = response.json()
    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})

    result = {
        "performance_score": categories.get("performance", {}).get("score"),
        "accessibility_score": categories.get("accessibility", {}).get("score"),
        "best_practices_score": categories.get("best-practices", {}).get("score"),
        "seo_score": categories.get("seo", {}).get("score"),
        "first_contentful_paint": audits.get("first-contentful-paint", {}).get("displayValue"),
        "largest_contentful_paint": audits.get("largest-contentful-paint", {}).get("displayValue"),
        "speed_index": audits.get("speed-index", {}).get("displayValue"),
        "total_blocking_time": audits.get("total-blocking-time", {}).get("displayValue"),
        "cumulative_layout_shift": audits.get("cumulative-layout-shift", {}).get("displayValue")
    }

    return result