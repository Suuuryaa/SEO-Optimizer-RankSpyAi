"""
Semantic keyword relevance scoring via HuggingFace Inference API.

Model: sentence-transformers/all-MiniLM-L6-v2
  - 80MB, runs on CPU, extremely fast for sentence similarity
  - Returns cosine similarity 0.0–1.0

We call the HF Inference API (free tier) — no local model loading,
no RAM overhead on Railway.
"""

import logging
import math
import os

import requests

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN   = os.getenv("HF_TOKEN", "")
_TIMEOUT   = 15


def _cosine(a: list[float], b: list[float]) -> float:
    dot  = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / norm if norm else 0.0


def _embed(texts: list[str]) -> list[list[float]] | None:
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    try:
        r = requests.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            result = r.json()
            # API returns list of embeddings (one per input text)
            if isinstance(result, list) and len(result) > 0:
                return result
        logger.warning(f"HF embed failed: {r.status_code} {r.text[:200]}")
        return None
    except Exception as exc:
        logger.warning(f"HF embed error: {exc}")
        return None


def semantic_keyword_score(page_text: str, keyword: str) -> dict:
    """
    Score how semantically relevant a page's content is to the target keyword.

    Returns:
        {
            semantic_score: int (0-100),
            semantic_label: str,
            best_chunk: str,
            hf_available: bool,
        }
    """
    if not keyword or not keyword.strip():
        return {"semantic_score": None, "semantic_label": "N/A", "best_chunk": "", "hf_available": False}

    # Split page into 500-char chunks (skip very short ones)
    raw_chunks = [page_text[i:i+500] for i in range(0, min(len(page_text), 6000), 500)]
    chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 50]

    if not chunks:
        return {"semantic_score": 0, "semantic_label": "No content", "best_chunk": "", "hf_available": False}

    # Embed keyword + all chunks in one API call
    texts = [keyword] + chunks[:10]  # max 11 texts per call
    embeddings = _embed(texts)

    if not embeddings:
        # HF unavailable — fall back to simple keyword presence score
        keyword_words = set(keyword.lower().split())
        page_words    = set(page_text.lower().split())
        overlap       = len(keyword_words & page_words)
        fallback_score = min(100, int((overlap / max(len(keyword_words), 1)) * 70))
        return {
            "semantic_score": fallback_score,
            "semantic_label": _label(fallback_score),
            "best_chunk": chunks[0][:200] if chunks else "",
            "hf_available": False,
        }

    kw_emb    = embeddings[0]
    chunk_embs = embeddings[1:]

    scores = [_cosine(kw_emb, ce) for ce in chunk_embs]
    best_idx   = scores.index(max(scores))
    best_score = max(scores)
    avg_score  = sum(scores) / len(scores)

    # Weighted: 70% best chunk, 30% average coverage
    combined   = (best_score * 0.7) + (avg_score * 0.3)
    final      = min(100, int(combined * 100))

    return {
        "semantic_score": final,
        "semantic_label": _label(final),
        "best_chunk": chunks[best_idx][:300],
        "hf_available": True,
    }


def _label(score: int) -> str:
    if score >= 75: return "Highly relevant"
    if score >= 50: return "Moderately relevant"
    if score >= 30: return "Weakly relevant"
    return "Not relevant"
