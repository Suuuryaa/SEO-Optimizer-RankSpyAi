"""
AI Content Brief Generator.

Compares the primary page against top competitors to surface:
  - Word count gap
  - Missing topic clusters (via keyword extraction)
  - Heading structure gaps
  - Missing content elements
  - Recommended improvements

Uses Gemini for the narrative brief, keyword overlap for gap analysis.
"""

import logging
import re
import requests
from collections import Counter

logger = logging.getLogger(__name__)

# Common English stop words to filter from keyword extraction
_STOP = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'by','from','is','are','was','were','be','been','has','have','had',
    'will','would','could','should','may','might','can','this','that','these',
    'those','it','its','we','our','you','your','they','their','as','if',
    'not','no','so','do','does','did','i','my','he','she','his','her',
    'what','which','who','how','when','where','why','all','more','also',
    'than','then','there','here','just','about','up','out','into','over',
    'after','before','new','one','two','three','get','got','use','used',
    'page','site','website','click','read','learn','find','see','view',
}


def _extract_keywords(text: str, top_n: int = 30) -> list[str]:
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    words = [w for w in words if w not in _STOP]
    return [word for word, _ in Counter(words).most_common(top_n)]


def _find_topic_gaps(primary_text: str, competitor_texts: list[str]) -> list[str]:
    """Return topics covered by ≥2 competitors but absent from primary page."""
    primary_kws = set(_extract_keywords(primary_text))
    competitor_kw_sets = [set(_extract_keywords(t)) for t in competitor_texts if t]

    # Topics in at least half of competitors but not in primary
    if not competitor_kw_sets:
        return []

    threshold = max(1, len(competitor_kw_sets) // 2)
    gap_topics = []
    for kw in set.union(*competitor_kw_sets):
        if kw not in primary_kws:
            count = sum(1 for s in competitor_kw_sets if kw in s)
            if count >= threshold:
                gap_topics.append((kw, count))

    gap_topics.sort(key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in gap_topics[:15]]


def _avg(vals: list, key: str) -> float:
    filtered = [v.get(key, 0) for v in vals if isinstance(v.get(key), (int, float))]
    return round(sum(filtered) / len(filtered), 1) if filtered else 0


def generate_content_brief(
    primary: dict,
    competitors: list[dict],
    keyword: str,
    gemini_api_key: str,
) -> dict:
    """
    Generate a full content brief comparing primary vs competitors.

    Returns:
        {
            word_count_target: int,
            word_count_gap: int,
            topic_gaps: list[str],
            competitor_avg_score: float,
            competitor_avg_words: int,
            heading_suggestions: list[str],
            ai_brief: str,
            quick_wins: list[str],
        }
    """
    primary_words  = primary.get("word_count", 0) or 0
    primary_score  = primary.get("seo_score", 0) or 0
    primary_title  = primary.get("title", "")
    primary_meta   = primary.get("meta_description", "")

    # Filter out errored competitors
    valid_comps = [c for c in competitors if not c.get("error") and c.get("word_count")]

    avg_score  = _avg(valid_comps, "SEO Score") or _avg(valid_comps, "seo_score") or 0
    avg_words  = int(_avg(valid_comps, "Word Count") or _avg(valid_comps, "word_count") or 0)
    target_words = max(avg_words + 200, primary_words + 500, 800)

    # Topic gap analysis
    primary_text    = primary.get("_text", "")
    comp_texts      = [c.get("_text", c.get("text_content", "")) for c in competitors[:5]]
    topic_gaps      = _find_topic_gaps(primary_text, comp_texts)

    # Quick wins (rule-based)
    quick_wins = []
    if not primary.get("keyword_in_title"):
        quick_wins.append(f'Add "{keyword}" to your page title')
    if not primary.get("keyword_in_h1"):
        quick_wins.append(f'Include "{keyword}" in your main H1 heading')
    if not primary.get("keyword_in_meta"):
        quick_wins.append(f'Add "{keyword}" to your meta description')
    if primary_words < avg_words:
        quick_wins.append(f"Expand content to ~{target_words} words (competitors average {avg_words})")
    if primary.get("missing_alt", 0) > 0:
        quick_wins.append(f"Add ALT text to {primary['missing_alt']} images")
    if not primary.get("technical_seo", {}).get("has_schema"):
        quick_wins.append("Add Schema markup (structured data)")
    if primary_score < avg_score:
        quick_wins.append(f"Your SEO score ({primary_score}) is below competitor average ({int(avg_score)})")

    # Heading suggestions from topic gaps
    heading_suggestions = [
        f"What is {topic_gaps[0]}?" if topic_gaps else f"What is {keyword}?",
        f"Benefits of {keyword}",
        f"How to use {keyword}",
        f"Best {keyword} for your needs" if keyword else "Expert recommendations",
        "Frequently Asked Questions",
    ]
    if topic_gaps:
        heading_suggestions[2:2] = [f"{t.title()} guide" for t in topic_gaps[:3]]

    # ── Gemini narrative brief ────────────────────────────────────────────────
    ai_brief = None
    if gemini_api_key and valid_comps:
        try:
            comp_summary = "\n".join([
                f"- {c.get('Venue Name', c.get('url', '?'))}: "
                f"{c.get('SEO Score', c.get('seo_score', 0))} score, "
                f"{c.get('Word Count', c.get('word_count', 0))} words"
                for c in valid_comps[:5]
            ])

            prompt = f"""You are an expert SEO content strategist.

Primary page: {primary_title}
Target keyword: {keyword}
Current word count: {primary_words}
Current SEO score: {primary_score}/100

Top {len(valid_comps[:5])} competitors:
{comp_summary}

Competitor average: {int(avg_words)} words, {int(avg_score)} SEO score
Missing topics vs competitors: {', '.join(topic_gaps[:8]) if topic_gaps else 'None identified'}

Write a concise, actionable content brief (150–200 words) covering:
1. Content goal and target audience
2. Recommended structure (key sections to add)
3. Competitive differentiation angle
4. Top 3 immediate actions

Be specific, direct, and avoid filler language."""

            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            if resp.status_code == 200:
                ai_brief = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                ai_brief = None
        except Exception as exc:
            logger.warning(f"content_brief Gemini error: {exc}")
            ai_brief = None

    if not ai_brief:
        ai_brief = (
            f"Your page scores {primary_score}/100 against competitors averaging {int(avg_score)}/100. "
            f"Expand from {primary_words} to ~{target_words} words to match competitor depth. "
            f"Key topics to cover: {', '.join(topic_gaps[:5]) or 'N/A'}. "
            f"Priority fixes: {'; '.join(quick_wins[:3]) or 'None identified'}."
        )

    return {
        "word_count_target":      target_words,
        "word_count_gap":         max(0, target_words - primary_words),
        "competitor_avg_words":   avg_words,
        "competitor_avg_score":   round(avg_score, 1),
        "topic_gaps":             topic_gaps,
        "heading_suggestions":    heading_suggestions[:7],
        "quick_wins":             quick_wins,
        "ai_brief":               ai_brief,
    }
