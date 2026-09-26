"""
Enhanced SEO Scoring Algorithm with weighted factors.

Scoring breakdown (100 points total):
- Critical Factors (50 points): Title keyword, content depth, H1 keyword, HTTPS
- High Priority (30 points): Meta keyword, title/meta length, keyword presence
- Medium Priority (20 points): ALT tags, internal links, schema markup, heading structure
"""

import logging

logger = logging.getLogger(__name__)


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
    mobile_viewport=True
):
    """
    Calculate comprehensive SEO score with weighted factors.
    
    Args:
        title (str): Page title
        meta_description (str): Meta description
        h1_tags (list): H1 headings
        keyword_count (int): Exact keyword matches
        word_count (int): Total word count
        missing_alt_count (int): Images without ALT text
        keyword_in_title_flag (bool): Keyword in title
        keyword_in_meta_flag (bool): Keyword in meta
        keyword_in_h1_flag (bool): Keyword in H1
        title_len (int): Title character length
        meta_len (int): Meta description character length
        internal_links_count (int): Number of internal links
        external_links_count (int): Number of external links
        has_schema (bool): Structured data present
        https_enabled (bool): HTTPS protocol
        mobile_viewport (bool): Mobile viewport meta tag
        
    Returns:
        tuple: (score: int, recommendations: list of str)
    """
    score = 0
    recommendations = []
    
    # ==================== CRITICAL FACTORS (50 points) ====================
    
    # Title keyword placement (15 points) - MOST IMPORTANT
    if keyword_in_title_flag:
        score += 15
    else:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Target keyword missing from title",
            "fix": "Add the target keyword naturally to the page title",
            "impact": "High - titles are the most important on-page SEO factor"
        })
    
    # Content depth (15 points)
    if word_count >= 1500:
        score += 15
    elif word_count >= 1000:
        score += 12
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": f"Content is good but could be more comprehensive ({word_count} words)",
            "fix": "Add more in-depth information to reach 1500+ words",
            "impact": "Medium - longer content tends to rank better"
        })
    elif word_count >= 500:
        score += 8
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Content depth is moderate ({word_count} words)",
            "fix": "Expand content to 1000+ words for better competitiveness",
            "impact": "High - thin content reduces ranking potential"
        })
    elif word_count >= 300:
        score += 5
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": f"Content is too thin ({word_count} words)",
            "fix": "Significantly expand content to at least 500-1000 words",
            "impact": "Critical - thin content rarely ranks well"
        })
    else:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": f"Critically thin content ({word_count} words)",
            "fix": "Create substantial content (minimum 500 words)",
            "impact": "Critical - insufficient content for ranking"
        })
    
    # H1 keyword placement (10 points)
    if keyword_in_h1_flag:
        score += 10
    else:
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
    if keyword_in_meta_flag:
        score += 8
    else:
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": "Target keyword missing from meta description",
            "fix": "Rewrite meta description to include keyword and compelling CTA",
            "impact": "Medium - improves click-through rate"
        })
    
    # Title length optimization (7 points)
    if 30 <= title_len <= 60:
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
    if 120 <= meta_len <= 160:
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
            "impact": "Medium - will be truncated or missing"
        })
    
    # Keyword usage frequency (8 points)
    if keyword_count >= 5:
        score += 8
    elif keyword_count >= 3:
        score += 6
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "issue": "Moderate keyword usage",
            "fix": "Increase natural keyword usage to 5+ occurrences",
            "impact": "Low-Medium - could strengthen topical relevance"
        })
    elif keyword_count > 0:
        score += 3
        recommendations.append({
            "priority": "🟠 HIGH",
            "issue": f"Low keyword usage ({keyword_count} times)",
            "fix": "Increase keyword usage naturally throughout content",
            "impact": "High - weak topical signals"
        })
    else:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "Keyword not found in content",
            "fix": "Use target keyword naturally in intro, headings, and body",
            "impact": "Critical - no relevance signals for target keyword"
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
    h1_count = len(h1_tags)
    if h1_count == 1:
        score += 5
    elif h1_count == 0:
        recommendations.append({
            "priority": "🔴 CRITICAL",
            "issue": "No H1 heading found",
            "fix": "Add exactly one H1 tag with keyword",
            "impact": "High - H1 is essential for content structure"
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
    
    # Ensure score doesn't exceed 100
    score = min(score, 100)
    
    # If no issues found, add positive note
    if score >= 90:
        recommendations.append({
            "priority": "✅ EXCELLENT",
            "issue": "Strong overall SEO performance",
            "fix": "Maintain current optimization and monitor competitors regularly",
            "impact": "Continue monitoring for ranking opportunities"
        })
    
    logger.info(f"SEO Score calculated: {score}/100")
    
    return score, recommendations


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
