from google import genai


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
    recommended_fixes=None
):
    if not gemini_api_key:
        return "No Gemini API key provided."

    strategic_insights = strategic_insights or []
    recommended_fixes = recommended_fixes or []

    insights_text = "\n".join([f"- {item}" for item in strategic_insights[:5]])
    fixes_text = "\n".join(
        [
            f"- {item.get('Priority', '')} | {item.get('Issue', '')} | {item.get('Recommended Fix', '')}"
            for item in recommended_fixes[:5]
        ]
    )

    prompt = f"""
You are an expert SEO strategist.

Write a short executive SEO summary for a non-technical business audience.

Primary venue: {primary_name}
Target keyword: {keyword}
Primary SERP rank: {primary_rank}
Primary SEO score: {primary_score}
Top competitor: {top_competitor}

Strategic insights:
{insights_text}

Recommended fixes:
{fixes_text}

Write:
1. A short executive summary
2. 3 priority actions
3. A 1-sentence conclusion
"""

    try:
        client = genai.Client(api_key=gemini_api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"AI summary error: {e}"