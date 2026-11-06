"""
Shared Gemini client — one place that picks a working text model and calls it.

Why this exists: each feature used to discover models on its own, sort anything
with "flash" in the name first and try only the first few. Google's model list
now includes TTS, image, live and preview variants that also say "flash", so
those got tried first and every request ended in "no working Gemini model".

Selection order:
  1. GEMINI_MODEL env var (comma-separated) — explicit override
  2. The model that last worked for this key
  3. Stable text models discovered from the API: newest flash → flash-lite → pro
  4. Fallback aliases if discovery fails
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time

import requests

logger = logging.getLogger(__name__)

_API = "https://generativelanguage.googleapis.com/v1beta"

# Google-maintained aliases that always point at the current model of that tier.
_FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# Only plain text-generation models: gemini-<version>-<flash|pro>[-lite][-NNN]
_STABLE_RE = re.compile(r"^gemini-(\d+(?:\.\d+)?)-(flash|pro)(-lite)?(-\d{3})?$")
_ALIAS_RE  = re.compile(r"^gemini-(flash|flash-lite|pro)-latest$")

_MAX_ATTEMPTS = 4
_DISCOVERY_TTL = 6 * 3600

_lock = threading.Lock()
_discovered: dict[str, tuple[float, list[str]]] = {}   # key fingerprint -> (time, models)
_last_good:  dict[str, str] = {}                       # key fingerprint -> model
_bad:        dict[str, dict[str, float]] = {}          # key fingerprint -> {model: skip-until}
_BAD_TTL = 6 * 3600
# A model not yet proven for this key gets a shorter leash: on the free tier the
# newest models can hang for 90 s, which would outlive Railway's 60 s request limit.
_PROBE_TIMEOUT = 20


class GeminiError(RuntimeError):
    """kind: 'invalid_key' | 'billing' | 'quota' | 'all_failed'"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def _fp(api_key: str) -> str:
    # Never store the raw key as a dict key that could end up in a log/dump.
    return f"{len(api_key)}:{api_key[-6:]}"


def _rank(name: str) -> tuple:
    """Sort key: newest version first, flash before flash-lite before pro."""
    m = _STABLE_RE.match(name)
    if m:
        version = float(m.group(1))
        tier = 0 if (m.group(2) == "flash" and not m.group(3)) else (1 if m.group(3) else 2)
        pinned = 1 if m.group(4) else 0          # prefer un-pinned name over -001
        return (0, tier, -version, pinned)
    a = _ALIAS_RE.match(name)
    if a:
        tier = {"flash": 0, "flash-lite": 1, "pro": 2}[a.group(1)]
        return (1, tier, 0, 0)                   # aliases after explicit versions
    return (9, 9, 0, 0)


def select_models(model_names: list[str]) -> list[str]:
    """Filter a raw model list down to usable text models, best first."""
    usable = {n for n in model_names if _STABLE_RE.match(n) or _ALIAS_RE.match(n)}
    return sorted(usable, key=_rank)


def _discover(api_key: str) -> list[str]:
    fp = _fp(api_key)
    with _lock:
        hit = _discovered.get(fp)
        if hit and time.time() - hit[0] < _DISCOVERY_TTL:
            return hit[1]
    try:
        resp = requests.get(
            f"{_API}/models", params={"pageSize": 1000},
            headers={"x-goog-api-key": api_key}, timeout=15,
        )
    except Exception as exc:
        logger.warning(f"Gemini model discovery failed: {exc}")
        return []
    if resp.status_code in (400, 401, 403):
        raise GeminiError("invalid_key", f"Gemini key rejected ({resp.status_code})")
    if resp.status_code != 200:
        logger.warning(f"Gemini model discovery HTTP {resp.status_code}")
        return []
    names = [
        m["name"].replace("models/", "")
        for m in resp.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    models = select_models(names)
    with _lock:
        _discovered[fp] = (time.time(), models)
    logger.info(f"Gemini models available: {models[:6]}")
    return models


def _candidates(api_key: str) -> list[str]:
    override = [m.strip() for m in os.getenv("GEMINI_MODEL", "").split(",") if m.strip()]
    now = time.time()
    bad = {m for m, until in _bad.get(_fp(api_key), {}).items() if until > now}
    order: list[str] = []
    for m in override + [_last_good.get(_fp(api_key), "")] + _discover(api_key) + _FALLBACK_MODELS:
        if m and m not in order and m not in bad:
            order.append(m)
    return order


def _mark_bad(api_key: str, model: str) -> None:
    _bad.setdefault(_fp(api_key), {})[model] = time.time() + _BAD_TTL


def _extract_text(data: dict) -> str:
    for cand in data.get("candidates", []):
        parts = cand.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if text.strip():
            return text.strip()
    return ""


def generate_text(
    api_key: str,
    prompt: str,
    *,
    temperature: float = 0.4,
    max_output_tokens: int = 8192,
    timeout: int = 60,
) -> str:
    """Return generated text, trying models in order. Raises GeminiError."""
    if not api_key:
        raise GeminiError("invalid_key", "No Gemini API key provided")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    errors: list[str] = []
    quota_hits = 0

    fp = _fp(api_key)
    for model in _candidates(api_key)[:_MAX_ATTEMPTS]:
        proven = _last_good.get(fp) == model
        try:
            resp = requests.post(
                f"{_API}/models/{model}:generateContent",
                headers=headers, json=payload,
                timeout=timeout if proven else min(timeout, _PROBE_TIMEOUT),
            )
        except Exception as exc:
            _mark_bad(api_key, model)   # hung or unreachable: skip it for 6 h
            errors.append(f"{model}: {type(exc).__name__}")
            continue

        if resp.status_code == 200:
            text = _extract_text(resp.json())
            if text:
                _last_good[_fp(api_key)] = model
                return text
            errors.append(f"{model}: empty response")
            continue
        if resp.status_code in (401, 403):
            raise GeminiError("invalid_key", f"Gemini key rejected ({resp.status_code})")
        if resp.status_code == 402:
            # Account-level: prepaid credits exhausted. Every model will fail the same way.
            raise GeminiError("billing", "Gemini prepaid credits are used up (HTTP 402)")
        if resp.status_code == 429:
            quota_hits += 1
        elif resp.status_code in (400, 404) or resp.status_code >= 500:
            _mark_bad(api_key, model)   # retired, not offered on this tier, or broken
        errors.append(f"{model}: HTTP {resp.status_code} {resp.text[:120]}")

    logger.warning(f"Gemini: all models failed — {errors}")
    if quota_hits and quota_hits == len(errors):
        raise GeminiError("quota", "Gemini quota exceeded on all models")
    raise GeminiError("all_failed", "; ".join(errors)[:500])
