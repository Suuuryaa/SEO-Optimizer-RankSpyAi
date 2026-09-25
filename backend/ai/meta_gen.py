"""
AI-powered meta title + description generator.

Primary:  HuggingFace facebook/bart-large-cnn (summarization)
Fallback: Rule-based extraction when HF is unavailable
"""

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

HF_SUMM_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_TOKEN    = os.getenv("HF_TOKEN", "")
_TIMEOUT    = 20


def _hf_summarize(text: str, max_len: int = 45, min_len: int = 12) -> str | None:
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    try:
        r = requests.post(
            HF_SUMM_URL,
            headers=headers,
            json={
                "inputs": text[:1024],
                "parameters": {
                    "max_length": max_len,
                    "min_length": min_len,
                    "do_sample": False,
                    "truncation": True,
                },
                "options": {"wait_for_model": True},
            },
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            result = r.json()
            if isinstance(result, list) and result:
                return result[0].get("summary_text", "").strip()
        logger.warning(f"HF summarize failed: {r.status_code} {r.text[:200]}")
        return None
    except Exception as exc:
        logger.warning(f"HF summarize error: {exc}")
        return None


def _rule_based_meta(title: str, h1_tags: list, text: str, keyword: str) -> str:
    """Extract a good meta description using first substantial sentences."""
    # Take first 3 sentences from page text
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    desc = " ".join(sentences[:3])[:160]

    # Ensure keyword is present
    if keyword and keyword.lower() not in desc.lower():
        desc = f"{keyword.capitalize()}: {desc}"[:160]

    return desc.strip()


def _rule_based_title(title: str, keyword: str) -> str:
    """Generate a better title if current one is too long/short."""
    if keyword and keyword.lower() not in title.lower():
        # Prepend keyword
        short_title = title[:40] if len(title) > 40 else title
        return f"{keyword.title()} | {short_title}"[:60]
    return title[:60]


def generate_meta_suggestions(
    current_title: str,
    current_meta: str,
    h1_tags: list,
    page_text: str,
    keyword: str,
    url: str,
) -> dict:
    """
    Generate AI-powered meta title and description suggestions.

    Returns:
        {
            suggested_title: str,
            suggested_meta: str,
            title_changes: list[str],   # what was improved
            meta_changes: list[str],
            hf_available: bool,
        }
    """
    keyword = (keyword or "").strip()
    h1_text = h1_tags[0] if h1_tags else ""

    # Build context for summarisation
    context = f"{h1_text}. {page_text[:800]}".strip()

    # ── Generate meta description ─────────────────────────────────────────────
    hf_available = False
    ai_meta = None

    if context:
        ai_meta = _hf_summarize(context, max_len=45, min_len=12)
        if ai_meta:
            hf_available = True
            # Inject keyword if missing
            if keyword and keyword.lower() not in ai_meta.lower():
                ai_meta = f"{keyword.capitalize()}: {ai_meta}"
            ai_meta = ai_meta[:160]

    suggested_meta = ai_meta or _rule_based_meta(current_title, h1_tags, page_text, keyword)

    # ── Generate title ────────────────────────────────────────────────────────
    # Use H1 as base (usually more descriptive than title) if available
    base = h1_text or current_title or url
    if len(base) < 20:
        base = current_title or url

    suggested_title = _rule_based_title(base, keyword)

    # ── Analyse what changed ──────────────────────────────────────────────────
    title_changes = []
    meta_changes  = []

    if keyword and keyword.lower() not in (current_title or "").lower():
        title_changes.append(f'Added keyword "{keyword}"')
    if current_title and len(current_title) > 60:
        title_changes.append("Shortened to under 60 characters")
    if not current_title:
        title_changes.append("Generated from H1 / page content")

    if not current_meta:
        meta_changes.append("Generated — page had no meta description")
    elif len(current_meta) < 50:
        meta_changes.append("Expanded — original was too short")
    elif len(current_meta) > 160:
        meta_changes.append("Trimmed — original exceeded 160 chars")
    if keyword and keyword.lower() not in (current_meta or "").lower():
        meta_changes.append(f'Injected keyword "{keyword}"')
    if hf_available:
        meta_changes.append("AI-generated summary (BART)")
    else:
        meta_changes.append("Rule-based extraction (HF unavailable)")

    return {
        "suggested_title": suggested_title,
        "suggested_meta":  suggested_meta,
        "title_changes":   title_changes,
        "meta_changes":    meta_changes,
        "hf_available":    hf_available,
    }
