import requests as _req


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
        return "No Gemini API key provided."

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
            f"  - {r.get('Venue Name','?')}: SEO Score {r.get('SEO Score',0)}, "
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

    insights_text = "\n".join([f"  - {i}" for i in strategic_insights[:8]]) or "  None provided."

    prompt = f"""You are a senior SEO strategist writing a detailed analysis report for a business owner.

PRIMARY SITE: {primary_name}
TARGET KEYWORD: "{keyword}"
PRIMARY SEO DATA: {primary_detail}
BEST COMPETITOR: {top_competitor}

COMPETITOR DATA:
{comp_text}

STRATEGIC INSIGHTS:
{insights_text}

Write a COMPREHENSIVE SEO analysis report with these exact sections:

## Executive Summary
2-3 sentences on overall SEO position vs competitors.

## Strengths
3-5 bullet points on what the primary site is doing well compared to competitors.

## Weaknesses
3-5 bullet points on specific areas where the primary site is underperforming vs competitors.

## Keyword & Content Analysis
Specific analysis of keyword usage, content depth, and how to improve for "{keyword}".

## Technical SEO Issues
Specific technical problems found (HTTPS, schema, alt text, internal links) with impact explanation.

## Competitor Insights
2-3 specific things top competitors are doing better that should be replicated.

## Priority Action Plan
5 concrete, specific actions ranked by impact. Each should say WHAT to do, WHERE to do it, and WHY it will help rankings.

## Conclusion
1-2 sentences on expected outcome if recommendations are followed.

Be specific, use the actual data provided, and write for a non-technical business owner."""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 8192}
        }

        models_to_try = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash",
                         "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-1.0-pro"]
        for api_ver in ["v1beta", "v1"]:
            try:
                r = _req.get(
                    f"https://generativelanguage.googleapis.com/{api_ver}/models?key={gemini_api_key}",
                    timeout=10
                )
                if r.status_code == 200:
                    discovered = [
                        m["name"].replace("models/", "")
                        for m in r.json().get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                        and "gemini" in m.get("name", "").lower()
                    ]
                    if discovered:
                        models_to_try = sorted(discovered, key=lambda x: (0 if "flash" in x else 1))
                        break
            except Exception:
                pass

        for model in models_to_try[:4]:
            for api_ver in ["v1beta", "v1"]:
                ep = (f"https://generativelanguage.googleapis.com/{api_ver}"
                      f"/models/{model}:generateContent?key={gemini_api_key}")
                resp = _req.post(ep, json=payload, timeout=60)
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        return "AI summary unavailable — no working Gemini model found for this API key."
    except Exception as e:
        return f"AI summary error: {e}"
