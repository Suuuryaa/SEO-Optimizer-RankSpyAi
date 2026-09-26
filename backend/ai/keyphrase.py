"""
HuggingFace keyphrase + NER extraction.

Models used:
  - ml6team/keyphrase-extraction-kbir-inspec  (keyphrase)
  - dslim/bert-base-NER                       (named entities)

Falls back to regex frequency analysis when HF is unavailable.
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter

import requests

logger = logging.getLogger(__name__)

HF_TOKEN = os.environ.get("HF_TOKEN", "")
_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
_TIMEOUT = 20

_KP_MODEL  = "ml6team/keyphrase-extraction-kbir-inspec"
_NER_MODEL = "dslim/bert-base-NER"

_KP_URL  = f"https://api-inference.huggingface.co/models/{_KP_MODEL}"
_NER_URL = f"https://api-inference.huggingface.co/models/{_NER_MODEL}"


def _hf_post(url: str, text: str) -> list | None:
    if not HF_TOKEN:
        return None
    try:
        r = requests.post(url, headers=_HEADERS, json={"inputs": text[:512]}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.debug(f"hf_post {url}: {exc}")
        return None


def _fallback_keyphrases(text: str, top_n: int = 15) -> list[str]:
    """Simple regex frequency fallback when HF is unavailable."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z\-]{3,}\b", text.lower())
    stopwords = {
        "this", "that", "with", "from", "have", "they", "will", "your",
        "more", "also", "into", "their", "been", "were", "when", "what",
        "about", "which", "these", "some", "other", "such", "than", "then",
    }
    filtered = [w for w in words if w not in stopwords]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]


def extract_keyphrases(text: str, top_n: int = 15) -> dict:
    """
    Extract keyphrases and named entities from `text`.
    Returns { keyphrases: [...], entities: [...], method: str }
    """
    # Try keyphrase extraction
    kp_result = _hf_post(_KP_URL, text[:2000])
    keyphrases: list[str] = []
    method = "fallback"

    if isinstance(kp_result, list) and kp_result:
        method = "hf-keyphrase"
        seen: set[str] = set()
        for item in kp_result:
            if isinstance(item, dict):
                word = item.get("word", "").strip()
                score = item.get("score", 0)
                if word and score > 0.5 and word not in seen:
                    keyphrases.append(word)
                    seen.add(word)
        keyphrases = keyphrases[:top_n]

    if not keyphrases:
        keyphrases = _fallback_keyphrases(text, top_n)

    # Try NER
    entities: list[dict] = []
    ner_result = _hf_post(_NER_URL, text[:512])
    if isinstance(ner_result, list):
        seen_ents: set[str] = set()
        for item in ner_result:
            if isinstance(item, dict):
                word  = item.get("word", "").strip()
                label = item.get("entity_group", item.get("entity", ""))
                score = item.get("score", 0)
                if word and score > 0.7 and word not in seen_ents and not word.startswith("##"):
                    entities.append({"word": word, "label": label, "score": round(score, 3)})
                    seen_ents.add(word)

    return {
        "keyphrases": keyphrases,
        "entities":   entities[:20],
        "method":     method,
    }
