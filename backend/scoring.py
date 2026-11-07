"""
Enhanced SEO Scoring Algorithm with weighted factors.

Scoring breakdown (100 points total):
- Critical Factors (50 points): Title keyword, content depth, H1 keyword, HTTPS
- High Priority (30 points): Meta keyword, title/meta length, keyword presence
- Medium Priority (20 points): ALT tags, internal links, schema markup, heading structure
"""

import logging

logger = logging.getLogger(__name__)

# Bump when scoring changes: it is returned with every result and is part of
# the result-cache key, so old cached scores are never mixed with new ones.
SCORING_VERSION = "1.1"


INDEXABILITY_CAP = 20

_INDEX_RECS = {
    "meta_noindex": ("Page is set to noindex",
                     "Remove 'noindex' from the robots meta tag so Google can list this page"),
    "x_robots_noindex": ("Server header blocks indexing (X-Robots-Tag: noindex)",
                         "Remove 'noindex' from the X-Robots-Tag HTTP header"),
    "robots_txt_blocked": ("robots.txt blocks Googlebot from this page",
                           "Allow Googlebot for this path in robots.txt"),
    "canonical_elsewhere": ("Canonical tag points to a different page",
                            "Point the canonical tag at this page's own URL, or optimise the canonical page instead"),
}


def _points(flag, full):
    """Full points for an exact match (or True), half for all_tokens, none otherwise."""
    if flag is True or flag == "exact":
        return full
    if flag == "all_tokens":
        return full // 2
    return 0


def calculate_seo_score(
    title,
    meta_description,
    h1_tags,
    keyword_count,
    word_count,
    missing_alt_count,
    keyword_in_title_flag,
    keyword_in_meta_flag,
    keyword_in_h1_flag,
    title_len,
    meta_len,
    internal_links_count=0,
    external_links_count=0,
    has_schema=False,
    https_enabled=True,
    mobile_viewport=True,
    keyword_density_pct=None,
    indexability=None,
):
    """
    Calculate the on-page SEO score (v1.1, same weights as 1.0).

    keyword_in_*_flag: True/"exact" = full points, "all_tokens" = half points,
    False/None = none.
    keyword_density_pct: when given, keyword usage is scored on density
    (0.5–2.5% best, >3.5% possible stuffing) instead of the raw count.
    indexability: {"indexable": bool, "reasons": [...]} — a page Google can't
    index is capped at 20 and gets one CRITICAL task per reason, listed first.

    Returns:
        tuple: (score, recommendations, score_uncapped, keyword_stuffing)
    """
    score = 0
    recommendations = []
    keyword_stuffing = False
    has_title = bool(title)
    has_meta = bool(meta_description)
    h1_count = len(h1_tags)

    # ==================== CRITICAL FACTORS (50 points) ====================

    # Title keyword placement (15 points) - MOST IMPORTANT
    score += _points(keyword_in_title_flag, 15)
    if not has_title:
        pass  # "Missing title" below covers it
    elif keyword_in_title_flag == "all_tokens":
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": "Title has the keyword's words but not the exact phrase",
            "fix": "Use the exact keyword phrase in the page title",
            "impact": "Medium - the exact phrase is a clearer relevance signal"
        })
    elif not keyword_in_title_flag:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Target keyword missing from title",
            "fix": "Add the target keyword naturally to the page title",
            "impact": "High - titles are the most important on-page SEO factor"
        })

    # Content depth (15 points). Points by length; advice severity is never
    # CRITICAL for word count alone.
    if word_count >= 1500:
        score += 15
    elif word_count >= 1000:
        score += 12
    elif word_count >= 500:
        score += 8
    elif word_count >= 300:
        score += 5
    if 300 <= word_count < 1500:
        recommendations.append({
            "priority": "🟢 LOW",
            "issue": f"Content length is {word_count} words",
            "fix": "Consider whether the page covers the topic in as much depth as the pages ranking above you",
            "impact": "Low - length helps only when it adds useful detail"
        })
    elif 150 <= word_count < 300:
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Content is thin ({word_count} words)",
            "fix": "Expand the page with useful detail visitors are looking for (aim for 300+ words)",
            "impact": "Medium - thin pages rarely rank well"
        })
    elif word_count < 150:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Very little content ({word_count} words)",
            "fix": "Add substantial, useful content (at least 300 words)",
            "impact": "High - search engines have little to understand the page by"
        })

    # H1 keyword placement (10 points)
    score += _points(keyword_in_h1_flag, 10)
    if h1_count == 0:
        pass  # one "No H1 heading found" task below covers it
    elif keyword_in_h1_flag == "all_tokens":
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": "H1 has the keyword's words but not the exact phrase",
            "fix": "Use the exact keyword phrase in the main H1 heading",
            "impact": "Medium - H1 is a strong relevance signal"
        })
    elif not keyword_in_h1_flag:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Target keyword missing from H1",
            "fix": "Add the target keyword or close variation to the main H1 heading",
            "impact": "High - H1 is a strong relevance signal"
        })

    # HTTPS security (5 points)
    if https_enabled:
        score += 5
    else:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Site not using HTTPS",
            "fix": "Enable HTTPS/SSL certificate immediately",
            "impact": "Critical - HTTPS is a ranking factor and security requirement"
        })

    # Mobile viewport (5 points)
    if mobile_viewport:
        score += 5
    else:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "No mobile viewport meta tag",
            "fix": "Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
            "impact": "Critical - required for mobile-first indexing"
        })

    # ==================== HIGH PRIORITY (30 points) ====================

    # Meta description keyword (8 points)
    score += _points(keyword_in_meta_flag, 8)
    if has_meta and not keyword_in_meta_flag:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": "Target keyword missing from meta description",
            "fix": "Rewrite meta description to include keyword and compelling CTA",
            "impact": "Medium - improves click-through rate"
        })

    # Title length optimization (7 points)
    if not has_title:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Missing title",
            "fix": "Add a <title> of 30-60 characters that includes the target keyword",
            "impact": "Critical - the title is what Google shows as the link in results"
        })
    elif 30 <= title_len <= 60:
        score += 7
    elif 25 <= title_len < 30 or 60 < title_len <= 70:
        score += 5
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Title length suboptimal ({title_len} characters)",
            "fix": "Adjust title to 30-60 characters for best display",
            "impact": "Low-Medium - may get truncated in search results"
        })
    else:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Title length problematic ({title_len} characters)",
            "fix": "Keep title between 30-60 characters",
            "impact": "Medium - will be truncated or flagged as too short"
        })

    # Meta description length (7 points)
    if not has_meta:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": "Missing meta description",
            "fix": "Add a 120-160 character meta description that includes the keyword",
            "impact": "Medium - Google writes its own snippet, often a poor one"
        })
    elif 120 <= meta_len <= 160:
        score += 7
    elif 100 <= meta_len < 120 or 160 < meta_len <= 200:
        score += 5
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Meta description length suboptimal ({meta_len} characters)",
            "fix": "Adjust meta description to 120-160 characters",
            "impact": "Low-Medium - may get truncated"
        })
    else:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Meta description length problematic ({meta_len} characters)",
            "fix": "Rewrite to 120-160 characters",
            "impact": "Medium - will be truncated"
        })

    # Keyword usage (8 points)
    d = keyword_density_pct
    if keyword_count == 0:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Keyword not found in content",
            "fix": "Use target keyword naturally in intro, headings, and body",
            "impact": "Critical - no relevance signals for target keyword"
        })
    elif d is not None and d > 3.5:
        keyword_stuffing = True
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Possible keyword stuffing ({d}% keyword density)",
            "fix": "Cut repeated uses of the keyword and write naturally (aim for 0.5-2.5%)",
            "impact": "High - Google can demote pages that repeat a keyword unnaturally"
        })
    elif d is not None and d > 2.5:
        score += 5
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Keyword density is on the high side ({d}%)",
            "fix": "Replace a few repeats with natural variations (aim for 0.5-2.5%)",
            "impact": "Medium - heavy repetition reads badly and can look like stuffing"
        })
    elif d is not None and d >= 0.5:
        score += 8
    elif d is None and keyword_count >= 5:
        score += 8          # no density given (old callers): count-based
    elif keyword_count >= 3:
        score += 6          # density below 0.5%: partial points
        recommendations.append({
                "priority": "🟡 MEDIUM",
                "issue": f"Low keyword density ({d}%)" if d is not None else "Moderate keyword usage",
                "fix": "Use the keyword a little more often in the body text (aim for 0.5-2.5%)",
                "impact": "Low-Medium - could strengthen topical relevance"
            })
    else:
        score += 3
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Low keyword usage ({keyword_count} times)",
            "fix": "Increase keyword usage naturally throughout content",
            "impact": "High - weak topical signals"
        })

    # ==================== MEDIUM PRIORITY (20 points) ====================

    # Image ALT text coverage (5 points)
    if missing_alt_count == 0:
        score += 5
    elif missing_alt_count <= 3:
        score += 3
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"{missing_alt_count} images missing ALT text",
            "fix": "Add descriptive ALT text to remaining images",
            "impact": "Low - minor accessibility and image SEO issue"
        })
    else:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"{missing_alt_count} images missing ALT text",
            "fix": "Add descriptive ALT text to all images",
            "impact": "Medium - accessibility issue and missed image SEO opportunity"
        })

    # Internal linking (5 points)
    if internal_links_count >= 5:
        score += 5
    elif internal_links_count >= 2:
        score += 3
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Limited internal linking ({internal_links_count} links)",
            "fix": "Add more contextual internal links (target: 5+)",
            "impact": "Low-Medium - improves site structure and page authority distribution"
        })
    else:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Very few internal links ({internal_links_count})",
            "fix": "Add contextual internal links to related pages",
            "impact": "Medium - weak internal linking structure"
        })

    # Structured data / Schema markup (5 points)
    if has_schema:
        score += 5
    else:
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": "No structured data detected",
            "fix": "Add relevant schema markup (Organization, LocalBusiness, etc.)",
            "impact": "Medium - enables rich snippets and better search visibility"
        })

    # H1 heading structure (5 points)
    if h1_count == 1:
        score += 5
    elif h1_count == 0:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "No H1 heading found",
            "fix": "Add exactly one H1 heading that includes the target keyword",
            "impact": "High - H1 is essential for content structure and relevance"
        })
    else:
        score += 2
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Multiple H1 tags detected ({h1_count})",
            "fix": "Use only one H1 per page",
            "impact": "Medium - dilutes heading importance"
        })

    # ==================== VALIDATION ====================

    score = min(score, 100)
    score_uncapped = score

    # Indexability gate: on-page work can't help a page Google won't index
    if indexability and indexability.get("indexable") is False:
        score = min(score, INDEXABILITY_CAP)
        gate_recs = []
        for reason in indexability.get("reasons", []):
            issue, fix = _INDEX_RECS.get(reason.get("code"), ("Google can't index this page", "Fix indexing first"))
            gate_recs.append({
                "priority": "🔴 CRITICAL",
                "issue": issue,
                "fix": fix,
                "impact": "Critical - Google won't show this page in results until this is fixed"
            })
        recommendations = gate_recs + recommendations

    if score >= 90:
        recommendations.append({
            "priority": "✅ EXCELLENT",
            "issue": "Strong overall SEO performance",
            "fix": "Maintain current optimization and monitor competitors regularly",
            "impact": "Continue monitoring for ranking opportunities"
        })

    logger.info(f"SEO Score calculated: {score}/100 (uncapped {score_uncapped})")

    return score, recommendations, score_uncapped, keyword_stuffing


def get_score_band(score):
    """
    Categorize score into performance bands.
    
    Returns:
        str: Performance band label
    """
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Strong"
    elif score >= 70:
        return "Good"
    elif score >= 60:
        return "Moderate"
    elif score >= 50:
        return "Fair"
    else:
        return "Weak"


def get_score_color(score):
    """
    Get color for score visualization.
    
    Returns:
        str: Color name or hex code
    """
    if score >= 80:
        return "green"
    elif score >= 60:
        return "orange"
    else:
        return "red"
