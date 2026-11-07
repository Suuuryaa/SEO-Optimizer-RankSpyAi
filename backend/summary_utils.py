import requests as _req
import re as _re_prompt


def _sanitize_for_prompt(text, max_len: int = 200) -> str:
    """Scraped/user text → prompt-safe (see ai.gemini.sanitize_for_prompt)."""
    from ai.gemini import sanitize_for_prompt
    return sanitize_for_prompt(text, max_len)


def get_executive_summary(score, keyword_count, missing_alt_count, word_count):
    if score >= 80:
        overall = "Strong SEO performance"
    elif score >= 60:
        overall = "Moderate SEO performance"
    else:
        overall = "Weak SEO performance"

    if keyword_count == 0:
        top_issue = "Target keyword is not being used in the page content."
    elif missing_alt_count > 10:
        top_issue = "A large number of images are missing alt text."
    elif word_count < 300:
        top_issue = "Content depth is too low for strong SEO performance."
    else:
        top_issue = "No major critical issue, but optimization opportunities remain."

    if word_count >= 500:
        strongest_area = "Content depth is relatively strong."
    else:
        strongest_area = "Basic page structure is present."

    if keyword_count == 0:
        priority_action = "Add the target keyword naturally to titles, headings, and body content."
    elif missing_alt_count > 10:
        priority_action = "Improve image alt text coverage."
    else:
        priority_action = "Refine on-page optimization and compare against competitors."

    return {
        "Overall Status": overall,
        "Top Issue": top_issue,
        "Strongest Area": strongest_area,
        "Priority Action": priority_action
    }


def generate_ai_executive_summary(
    gemini_api_key,
    primary_name,
    keyword,
    primary_rank,
    primary_score,
    top_competitor,
    strategic_insights=None,
    recommended_fixes=None,
    benchmark_rows=None,
):
    if not gemini_api_key:
        return None

    strategic_insights = strategic_insights or []
    recommended_fixes = recommended_fixes or []
    benchmark_rows = benchmark_rows or []

    # Build competitor comparison table text
    valid_rows = [r for r in benchmark_rows if r.get("Score Band") not in ("Blocked", "Error")]
    comp_rows = [r for r in valid_rows if "Competitor" in r.get("Role", "")]
    primary_rows = [r for r in valid_rows if "Primary" in r.get("Role", "")]

    comp_lines = []
    for r in comp_rows[:10]:
        comp_lines.append(
            f"  - {_sanitize_for_prompt(r.get('Venue Name','?'))}: SEO Score {r.get('SEO Score',0)}, "
            f"Word Count {r.get('Word Count',0)}, Keyword Count {r.get('Keyword Count',0)}, "
            f"HTTPS {r.get('HTTPS','?')}, Schema {r.get('Schema','?')}"
        )
    comp_text = "\n".join(comp_lines) if comp_lines else "  No competitor data available."

    primary_data = primary_rows[0] if primary_rows else {}
    primary_detail = (
        f"SEO Score: {primary_data.get('SEO Score', primary_score)}, "
        f"Word Count: {primary_data.get('Word Count', 0)}, "
        f"Keyword Count: {primary_data.get('Keyword Count', 0)}, "
        f"HTTPS: {primary_data.get('HTTPS', '?')}, "
        f"Schema Markup: {primary_data.get('Schema', '?')}, "
        f"Internal Links: {primary_data.get('Internal Links', 0)}, "
        f"Images Missing ALT: {primary_data.get('Images Missing ALT', 0)}"
    )

    if isinstance(primary_rank, int):
        rank_text = f"#{primary_rank} in Google's organic results (measured)"
    elif primary_rank is None:
        rank_text = "not in Google's top 30 organic results (measured)"
    else:
        rank_text = "unknown (not measured)"

    insights_text = "\n".join([f"  - {_sanitize_for_prompt(i)}" for i in strategic_insights[:8]]) or "  None provided."

    from ai.gemini import untrusted_block
    safe_kw = _sanitize_for_prompt(keyword)
    data = f"""PRIMARY SITE: {_sanitize_for_prompt(primary_name)}
TARGET KEYWORD: "{safe_kw}"
GOOGLE POSITION FOR THIS KEYWORD: {rank_text}
PRIMARY SEO DATA: {primary_detail}
BEST COMPETITOR: {_sanitize_for_prompt(top_competitor)}

COMPETITOR DATA:
{comp_text}

STRATEGIC INSIGHTS:
{insights_text}"""

    prompt = f"""You are a senior SEO strategist writing a detailed analysis report for a business owner.

{untrusted_block(data)}

RULE: Only state a Google ranking for the primary site if GOOGLE POSITION above gives one. Never claim a position that is not listed there, and never claim a competitor's ranking.

Write a COMPREHENSIVE SEO analysis report with these exact sections:

## Executive Summary
2-3 sentences on overall SEO position vs competitors.

## Strengths
3-5 bullet points on what the primary site is doing well compared to competitors.

## Weaknesses
3-5 bullet points on specific areas where the primary site is underperforming vs competitors.

## Keyword & Content Analysis
Specific analysis of keyword usage, content depth, and how to improve for the target keyword.

## Technical SEO Issues
Specific technical problems found (HTTPS, schema, alt text, internal links) with impact explanation.

## Competitor Insights
2-3 specific things top competitors are doing better that should be replicated.

## Priority Action Plan
5 concrete, specific actions ranked by impact. Each should say WHAT to do, WHERE to do it, and WHY it will help rankings.

## Conclusion
1-2 sentences on expected outcome if recommendations are followed.

Be specific, use the actual data provided, and write for a non-technical business owner. Keep the whole report under 3,500 characters."""

    from ai.gemini import generate_text, GeminiError
    try:
        return generate_text(gemini_api_key, prompt, temperature=0.4,
                             max_output_tokens=8192, timeout=60)
    except GeminiError as e:
        # The caller shows product copy; the reason is only logged.
        import logging
        logging.getLogger(__name__).warning(f"AI summary failed: {e.kind}")
        return None
