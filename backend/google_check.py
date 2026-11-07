"""Google's own view of a page, for competitor sites that block our scanner.

Many big sites refuse automated visitors but let Google's Lighthouse (PageSpeed)
tool in. We never try to get past a site's bot protection; we only ask Google.
"""
import requests


def google_seo_check(url, api_key, timeout=45):
    """Google Lighthouse SEO check of one page, run from Google's servers.

    Returns {"seo_score", "checked_url", "title_ok", "meta_ok", "crawlable"}
    or None when Google couldn't check it either.
    """
    if not api_key or not url:
        return None
    try:
        r = requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                         params={"url": url, "strategy": "mobile", "category": "SEO", "key": api_key},
                         timeout=timeout)
        if r.status_code != 200:
            return None
        lh = r.json().get("lighthouseResult") or {}
        score = (lh.get("categories", {}).get("seo") or {}).get("score")
        if score is None:
            return None
        audits = lh.get("audits", {})

        def ok(k):
            return (audits.get(k) or {}).get("score") == 1
        return {"seo_score": round(score * 100), "checked_url": lh.get("finalDisplayedUrl") or url,
                "title_ok": ok("document-title"), "meta_ok": ok("meta-description"),
                "crawlable": ok("is-crawlable")}
    except Exception:
        return None
