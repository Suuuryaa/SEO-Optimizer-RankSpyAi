"""
GEO (Generative Engine Optimization) analysis utilities for the FunLab SEO Dashboard.
Analyzes how well a site is optimized for AI-powered search engines and LLMs.
"""

import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FunLabSEOBot/1.0; +https://funlab.io)"
    )
}

_REQUEST_TIMEOUT = 10


def _get(url: str, **kwargs):
    """Thin wrapper around requests.get with shared defaults."""
    kwargs.setdefault("headers", _HEADERS)
    kwargs.setdefault("timeout", _REQUEST_TIMEOUT)
    kwargs.setdefault("allow_redirects", True)
    return requests.get(url, **kwargs)


def _base_url(url: str) -> str:
    """Return scheme + netloc (e.g. https://example.com)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


# ---------------------------------------------------------------------------
# 1. check_ai_crawlers
# ---------------------------------------------------------------------------

_AI_CRAWLERS = [
    # (display name, user-agent token, priority)
    ("GPTBot",            "GPTBot",            "critical"),
    ("ClaudeBot",         "ClaudeBot",          "critical"),
    ("PerplexityBot",     "PerplexityBot",      "critical"),
    ("OAI-SearchBot",     "OAI-SearchBot",      "critical"),
    ("Googlebot",         "Googlebot",          "critical"),
    ("Google-Extended",   "Google-Extended",    "secondary"),
    ("Amazonbot",         "Amazonbot",          "secondary"),
    ("Applebot-Extended", "Applebot-Extended",  "secondary"),
    ("FacebookBot",       "FacebookBot",        "secondary"),
    ("Bytespider",        "Bytespider",         "secondary"),
]

_CRITICAL_DEDUCTION  = 15
_SECONDARY_DEDUCTION = 5
_SITEMAP_DEDUCTION   = 10


def _parse_robots(robots_text: str) -> dict:
    """
    Parse robots.txt into a dict keyed by lower-cased user-agent.
    Each value is a list of disallow paths.
    Also returns a set of all encountered user-agents.
    """
    rules: dict[str, list[str]] = {}
    current_agents: list[str] = []

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#")[0].strip()
        if not line:
            if current_agents:
                current_agents = []
            continue

        if ":" not in line:
            continue

        field, _, value = line.partition(":")
        field  = field.strip().lower()
        value  = value.strip()

        if field == "user-agent":
            current_agents.append(value.lower())
            rules.setdefault(value.lower(), [])
        elif field == "disallow" and value:
            for agent in current_agents:
                rules.setdefault(agent, []).append(value)

    return rules


def _is_blocked(agent_token: str, rules: dict) -> bool:
    """
    Return True if the given agent token is blocked (Disallow: /) in robots.txt.
    Checks both the specific agent and the wildcard (*).
    """
    token_lower = agent_token.lower()

    for key, disallows in rules.items():
        if key == token_lower or key == "*":
            if "/" in disallows or "/*" in disallows:
                return True

    return False


def check_ai_crawlers(url: str) -> dict:
    """
    Fetch robots.txt and check access for 10 AI crawlers.
    """
    default = {
        "score": 0,
        "crawlers": [],
        "has_sitemap": False,
        "raw_robots": "",
    }

    try:
        robots_url = urljoin(_base_url(url), "/robots.txt")
        resp = _get(robots_url)
        raw_robots = resp.text if resp.status_code == 200 else ""
    except Exception:
        raw_robots = ""

    rules = _parse_robots(raw_robots)

    # Sitemap presence
    has_sitemap = bool(re.search(r"(?im)^sitemap\s*:", raw_robots))

    score = 100
    if not has_sitemap:
        score -= _SITEMAP_DEDUCTION

    crawlers = []
    for name, agent, priority in _AI_CRAWLERS:
        if not raw_robots:
            status = "not_specified"
        elif _is_blocked(agent, rules):
            status = "blocked"
            deduction = _CRITICAL_DEDUCTION if priority == "critical" else _SECONDARY_DEDUCTION
            score -= deduction
        else:
            status = "allowed"

        crawlers.append({
            "name":       name,
            "user_agent": agent,
            "status":     status,
            "priority":   priority,
        })

    score = max(0, min(100, score))

    return {
        "score":      score,
        "crawlers":   crawlers,
        "has_sitemap": has_sitemap,
        "raw_robots": raw_robots,
    }


# ---------------------------------------------------------------------------
# 2. score_citability
# ---------------------------------------------------------------------------

_GRADE_LABELS = {
    "A": "Highly Citable",
    "B": "Good Citability",
    "C": "Moderate Citability",
    "D": "Low Citability",
    "F": "Poor Citability",
}

_DEFINITION_PATTERNS = re.compile(
    r"\b\w+\s+(is|means|refers to)\b", re.IGNORECASE
)

_TRANSITION_WORDS = re.compile(
    r"\b(first|second|third|however|therefore|additionally|furthermore|"
    r"moreover|consequently|in contrast|as a result|for example|"
    r"in addition|finally|thus)\b",
    re.IGNORECASE,
)

_RESEARCH_PATTERNS = re.compile(
    r"\b(research shows|study found|according to|studies show|"
    r"data shows|report found|survey found|analysis shows)\b",
    re.IGNORECASE,
)

_PRONOUN_RE = re.compile(
    r"\b(he|she|it|they|this|that|these|those)\b", re.IGNORECASE
)

_TOOL_NAME_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]+(Bot|AI|GPT|LLM|API|Pro|Plus|X)?\b")


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _score_block(heading: str, text: str) -> dict:
    """Score a single content block on 5 dimensions."""
    words = text.split()
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    num_sentences = max(len(sentences), 1)

    total = 0

    # 1. Answer Block Quality (30 pts)
    aq = 0
    if _DEFINITION_PATTERNS.search(text):
        aq += 12
    first_60 = " ".join(words[:60])
    if len(first_60) > 30:                       # something meaningful in first 60 words
        aq += 10
    avg_words_per_sentence = word_count / num_sentences
    if 5 <= avg_words_per_sentence <= 25:
        aq += 8
    total += min(aq, 30)

    # 2. Self-Containment (25 pts)
    sc = 0
    if 100 <= word_count <= 200:
        sc += 10
    elif 80 <= word_count <= 250:
        sc += 6
    pronoun_count = len(_PRONOUN_RE.findall(text))
    pronoun_density = pronoun_count / max(word_count, 1)
    if pronoun_density < 0.03:
        sc += 8
    # Named entities: capitalised words that are not sentence-starters
    named_entities = set()
    for sent in sentences:
        sent_words = sent.split()
        for w in sent_words[1:]:        # skip first word of sentence
            if w and w[0].isupper() and w.isalpha():
                named_entities.add(w)
    if len(named_entities) >= 2:
        sc += 7
    total += min(sc, 25)

    # 3. Structural Readability (20 pts)
    sr = 0
    if re.search(r"(^|\n)\s*[-*•]|\d+\.", text):
        sr += 8
    if _TRANSITION_WORDS.search(text):
        sr += 6
    if num_sentences > 2:
        sr += 6
    total += min(sr, 20)

    # 4. Statistical Density (15 pts)
    sd = 0
    if re.search(r"\d+%", text):
        sd += 5
    if re.search(r"\b\d[\d,]*(\.\d+)?\b", text):
        sd += 5
    if re.search(r"\$[\d,]+|\b\d+\s*(dollars?|USD|EUR|GBP)\b", text, re.IGNORECASE):
        sd += 5
    total += min(sd, 15)

    # 5. Uniqueness Signals (10 pts)
    us = 0
    if _RESEARCH_PATTERNS.search(text):
        us += 5
    # Specific product/tool names heuristic
    if len(_TOOL_NAME_RE.findall(text)) >= 2:
        us += 5
    total += min(us, 10)

    block_score = min(100, total)
    return {
        "heading":    heading or "(no heading)",
        "score":      block_score,
        "grade":      _grade(block_score),
        "word_count": word_count,
        "preview":    text[:200].replace("\n", " ").strip() + ("…" if len(text) > 200 else ""),
    }


def score_citability(soup) -> dict:
    """
    Score content blocks for AI citability likelihood.
    """
    default = {
        "score": 0,
        "grade": "F",
        "grade_label": _GRADE_LABELS["F"],
        "blocks_analyzed": 0,
        "top_blocks": [],
        "optimal_blocks": 0,
    }

    try:
        # Build content blocks: each heading + following paragraphs
        content_tags = soup.find_all(["h1", "h2", "h3", "h4", "p", "li"])

        blocks = []
        current_heading = ""
        current_paras = []

        def flush():
            if current_paras:
                combined = " ".join(current_paras)
                if len(combined.split()) >= 20:    # ignore tiny fragments
                    blocks.append((current_heading, combined))

        for tag in content_tags:
            if tag.name in ("h1", "h2", "h3", "h4"):
                flush()
                current_heading = tag.get_text(separator=" ", strip=True)
                current_paras = []
            else:
                text = tag.get_text(separator=" ", strip=True)
                if text:
                    current_paras.append(text)

        flush()

        if not blocks:
            return default

        scored_blocks = [_score_block(h, t) for h, t in blocks]
        scored_blocks.sort(key=lambda b: b["score"], reverse=True)
        top_5 = scored_blocks[:5]

        avg_score = round(sum(b["score"] for b in top_5) / len(top_5))
        grade = _grade(avg_score)
        optimal = sum(1 for _, t in blocks if 100 <= len(t.split()) <= 200)

        return {
            "score":          avg_score,
            "grade":          grade,
            "grade_label":    _GRADE_LABELS[grade],
            "blocks_analyzed": len(blocks),
            "top_blocks":     top_5,
            "optimal_blocks": optimal,
        }

    except Exception:
        return default


# ---------------------------------------------------------------------------
# 3. check_llmstxt
# ---------------------------------------------------------------------------

def check_llmstxt(url: str) -> dict:
    """
    Check if site has llms.txt (emerging AI guidance standard).
    """
    default = {
        "exists":   False,
        "url":      None,
        "has_full": False,
        "is_valid": False,
        "sections": 0,
        "links":    0,
    }

    try:
        base = _base_url(url)
        llms_url      = urljoin(base, "/llms.txt")
        llms_full_url = urljoin(base, "/llms-full.txt")

        content      = None
        found_url    = None
        has_full     = False

        # Try main llms.txt
        try:
            r = _get(llms_url)
            if r.status_code == 200 and len(r.text.strip()) > 0:
                content   = r.text
                found_url = llms_url
        except Exception:
            pass

        # Try llms-full.txt regardless (to detect has_full)
        try:
            r2 = _get(llms_full_url)
            if r2.status_code == 200 and len(r2.text.strip()) > 0:
                has_full = True
                if content is None:
                    content   = r2.text
                    found_url = llms_full_url
        except Exception:
            pass

        if content is None:
            return default

        # Validate: must have # title line and > description line
        has_title       = bool(re.search(r"^#\s+\S", content, re.MULTILINE))
        has_description = bool(re.search(r"^>\s+\S", content, re.MULTILINE))
        is_valid        = has_title and has_description

        sections = len(re.findall(r"^##\s+", content, re.MULTILINE))
        links    = len(re.findall(r"^-\s+\[", content, re.MULTILINE))

        return {
            "exists":   True,
            "url":      found_url,
            "has_full": has_full,
            "is_valid": is_valid,
            "sections": sections,
            "links":    links,
        }

    except Exception:
        return default


# ---------------------------------------------------------------------------
# 4. check_eeat
# ---------------------------------------------------------------------------

_AUTHOR_PATTERNS = re.compile(
    r"\b(by\s+[A-Z][a-z]+|author\s*:|written\s+by\s+[A-Z]|contributor\s*:)",
    re.IGNORECASE,
)

_DATE_PATTERNS = re.compile(
    r"\b(published|updated|posted|last\s+modified|date)\b"
    r"|\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\b"
    r"|\d{4}-\d{2}-\d{2}",
    re.IGNORECASE,
)

_CREDENTIALS_RE = re.compile(
    r"\b(PhD|MD|MBA|CEO|CTO|CFO|CMO|expert|specialist|professor|"
    r"years\s+of\s+experience|certified|licensed|accredited)\b",
    re.IGNORECASE,
)

_METHODOLOGY_RE = re.compile(
    r"\b(how\s+(it\s+)?works|methodology|our\s+process|our\s+approach|"
    r"how\s+we|step\s+by\s+step|our\s+method)\b",
    re.IGNORECASE,
)

_CASE_STUDY_RE = re.compile(
    r"\b(case\s+study|for\s+example|for\s+instance|in\s+our\s+experience|"
    r"we\s+tested|we\s+found|in\s+practice)\b",
    re.IGNORECASE,
)

_EXTERNAL_CITE_RE = re.compile(
    r"(https?://(?!(?:www\.)?(?:example\.com))[^\s\"'<>]+)"
    r"|\[[\d]+\]"     # numbered references
    r"|\(source\s*:",
    re.IGNORECASE,
)


def _find_link(soup, patterns: list[str]) -> bool:
    """Return True if any <a> tag's href or text matches any pattern."""
    pattern_re = re.compile("|".join(patterns), re.IGNORECASE)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if pattern_re.search(href) or pattern_re.search(text):
            return True
    return False


def check_eeat(soup, url: str) -> dict:
    """
    Check E-E-A-T signals.
    """
    default = {
        "score":              0,
        "experience":         0,
        "expertise":          0,
        "authoritativeness":  0,
        "trustworthiness":    0,
        "signals": {
            "has_author":   False,
            "has_date":     False,
            "has_about":    False,
            "has_contact":  False,
            "has_privacy":  False,
            "has_https":    False,
            "word_count":   0,
        },
    }

    try:
        full_text = soup.get_text(separator=" ", strip=True)
        word_count = len(full_text.split())

        # ---- Experience (25 pts) ----
        experience = 0
        has_date = bool(_DATE_PATTERNS.search(full_text))
        if has_date:
            experience += 8
        if word_count > 800:
            experience += 10
        if _CASE_STUDY_RE.search(full_text):
            experience += 7

        # ---- Expertise (25 pts) ----
        expertise = 0
        has_author = bool(_AUTHOR_PATTERNS.search(full_text))
        if has_author:
            expertise += 12
        if _CREDENTIALS_RE.search(full_text):
            expertise += 8
        if _METHODOLOGY_RE.search(full_text):
            expertise += 5

        # ---- Authoritativeness (25 pts) ----
        authoritativeness = 0
        has_about   = _find_link(soup, [r"about", r"about-us", r"about_us"])
        has_contact = _find_link(soup, [r"contact", r"contact-us", r"get-in-touch"])
        if has_about:
            authoritativeness += 8
        external_links = _EXTERNAL_CITE_RE.findall(full_text)
        if len(external_links) >= 2:
            authoritativeness += 10
        elif len(external_links) == 1:
            authoritativeness += 5
        if has_contact:
            authoritativeness += 7

        # ---- Trustworthiness (25 pts) ----
        trustworthiness = 0
        has_https   = url.startswith("https://")
        has_privacy = _find_link(soup, [r"privacy", r"privacy-policy"])
        has_terms   = _find_link(soup, [r"terms", r"terms-of-service", r"legal", r"tos"])
        if has_https:
            trustworthiness += 10
        if has_privacy:
            trustworthiness += 8
        if has_terms:
            trustworthiness += 7

        # Clamp each dimension
        experience        = min(25, experience)
        expertise         = min(25, expertise)
        authoritativeness = min(25, authoritativeness)
        trustworthiness   = min(25, trustworthiness)

        total = experience + expertise + authoritativeness + trustworthiness   # max 100

        return {
            "score":              total,
            "experience":         experience,
            "expertise":          expertise,
            "authoritativeness":  authoritativeness,
            "trustworthiness":    trustworthiness,
            "signals": {
                "has_author":   has_author,
                "has_date":     has_date,
                "has_about":    has_about,
                "has_contact":  has_contact,
                "has_privacy":  has_privacy,
                "has_https":    has_https,
                "word_count":   word_count,
            },
        }

    except Exception:
        return default


# ---------------------------------------------------------------------------
# 5. calculate_geo_score
# ---------------------------------------------------------------------------

_BANDS = [
    (80,  "Excellent"),
    (65,  "Good"),
    (50,  "Fair"),
    (35,  "Poor"),
    (0,   "Critical"),
]


def _band(score: float) -> str:
    for threshold, label in _BANDS:
        if score >= threshold:
            return label
    return "Critical"


def calculate_geo_score(
    crawler_score:    int | float,
    citability_score: int | float,
    eeat_score:       int | float,
    llmstxt_exists:   bool,
    has_schema:       bool,
) -> dict:
    """
    Weighted GEO composite score.
    """
    try:
        schema_score  = 100 if has_schema    else 0
        llmstxt_score = 50  if llmstxt_exists else 0

        weights = {
            "citability": 0.30,
            "eeat":       0.25,
            "crawlers":   0.25,
            "schema":     0.10,
            "llmstxt":    0.10,
        }

        scores = {
            "citability": float(citability_score),
            "eeat":       float(eeat_score),
            "crawlers":   float(crawler_score),
            "schema":     float(schema_score),
            "llmstxt":    float(llmstxt_score),
        }

        breakdown = {}
        total = 0.0
        for key, weight in weights.items():
            s       = scores[key]
            weighted = round(s * weight, 2)
            total   += weighted
            breakdown[key] = {
                "score":    int(round(s)),
                "weight":   weight,
                "weighted": weighted,
            }

        composite = int(round(min(100, max(0, total))))

        return {
            "score":     composite,
            "band":      _band(composite),
            "breakdown": breakdown,
        }

    except Exception:
        return {
            "score":     0,
            "band":      "Critical",
            "breakdown": {},
        }
