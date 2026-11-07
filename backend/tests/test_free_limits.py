"""Per-visitor free allowance, free rescans, IPv6 /64 grouping, refunds and the spend cap."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _req(ip="203.0.113.5"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={})


@pytest.fixture
def gate(monkeypatch):
    import main
    monkeypatch.setattr(main, "check_and_consume",
                        lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "refund", lambda: None)
    return main


def _kind(exc):
    return getattr(exc, "error_kind", None)


def test_three_free_scans_then_daily_limit(gate):
    for _ in range(3):
        gate._gate(None, _req())
    with pytest.raises(HTTPException) as e:
        gate._gate(None, _req())
    assert e.value.status_code == 429 and _kind(e.value) == "daily_limit"
    assert "3 free scans" in e.value.detail


def test_other_visitors_unaffected(gate):
    for _ in range(3):
        gate._gate(None, _req("203.0.113.5"))
    gate._gate(None, _req("198.51.100.7"))     # a different visitor still has scans


def test_ipv6_same_64_shares_allowance(gate):
    for i in range(3):
        gate._gate(None, _req(f"2001:db8:1:2::{i + 1}"))
    with pytest.raises(HTTPException):
        gate._gate(None, _req("2001:db8:1:2:ffff::9"))     # same /64, new address
    gate._gate(None, _req("2001:db8:1:3::1"))              # different /64


def test_free_rescan_after_fixing(gate):
    import free_limits
    url, kw = "https://example.com/", "plumber"
    g = gate._gate(None, _req(), "scan", url, kw, False)
    assert g["personal"] == "scan"
    free_limits.mark_seen(g["bucket"], url, kw)
    for _ in range(2):          # two free rescans of the same page
        assert gate._gate(None, _req(), "scan", url, kw, True)["personal"] == "rescan"
    # third rescan is a normal (counted) scan
    assert gate._gate(None, _req(), "scan", url, kw, True)["personal"] == "scan"
    assert free_limits.used(g["bucket"]) == 2


def test_fresh_scan_of_unseen_page_is_counted(gate):
    g = gate._gate(None, _req(), "scan", "https://new.example/", "", True)
    assert g["personal"] == "scan"


def test_comparisons_have_their_own_daily_allowance(gate):
    gate._gate(None, _req(), "compare")
    with pytest.raises(HTTPException) as e:
        gate._gate(None, _req(), "compare")
    assert _kind(e.value) == "compare_limit" and "competitor comparison" in e.value.detail
    gate._gate(None, _req())     # page scans still available


def test_failed_scan_is_refunded_but_not_after_proxy_use(gate):
    import free_limits
    g = gate._gate(None, _req())
    gate._refund(g)
    assert free_limits.used(g["bucket"]) == 0
    g = gate._gate(None, _req())
    gate._refund(g, SimpleNamespace(used_proxy=True))
    assert free_limits.used(g["bucket"]) == 1


def test_global_pool_empty_gives_back_personal_scan(gate, monkeypatch):
    import free_limits
    monkeypatch.setattr(gate, "check_and_consume", lambda user_has_own_keys=False: {"allowed": False})
    with pytest.raises(HTTPException) as e:
        gate._gate(None, _req())
    assert _kind(e.value) == "busy"
    assert free_limits.used("203.0.113.5") == 0


def test_spend_cap_pauses_free_scans(gate):
    import spend
    spend.add(spend.FREE_DAILY_USD_CAP + 0.01)
    with pytest.raises(HTTPException) as e:
        gate._gate(None, _req())
    assert e.value.status_code == 503 and _kind(e.value) == "busy"


def test_spend_counts_server_keys_only(monkeypatch):
    import spend
    monkeypatch.setenv("GEMINI_API_KEY", "server-key")
    monkeypatch.setenv("SERPER_API_KEY", "serper-server")
    spend.gemini_call("visitor-own-key", {"promptTokenCount": 10_000_000})
    spend.serper_call("someone-else")
    assert spend.today_usd() == 0
    spend.gemini_call("server-key", {"promptTokenCount": 1_000_000, "candidatesTokenCount": 0})
    spend.serper_call("serper-server")
    assert spend.today_usd() == pytest.approx(spend.GEMINI_USD_PER_M_IN + spend.SERPER_USD_PER_QUERY)


def test_ip_quota_groups_ipv6_by_64(monkeypatch):
    import cache
    monkeypatch.setattr(cache, "_LOCAL_QUOTA", {})
    monkeypatch.setattr(cache, "_redis_cmd", lambda *a: None)
    results = [cache.check_ip_quota(f"2001:db8:9:9::{i + 1}", "helpers", 2) for i in range(3)]
    assert results == [True, True, False]


def test_rate_status_reports_this_visitors_allowance(gate):
    client = TestClient(gate.app)
    body = client.get("/rate-status").json()
    assert body["scans_limit"] == 3 and body["scans_remaining"] == 3
    assert body["daily_limit"] == 3 and body["resets_at"].endswith("Z")


def test_image_text_off_by_default(public_dns):
    from models import AnalyzeRequest
    import main
    assert AnalyzeRequest(url="https://example.com").image_text is False
    assert main.IMAGE_TEXT_ENABLED is False


def test_proxy_fallback_off_by_default():
    import seo_utils
    assert seo_utils._PROXY_FALLBACK is False


def test_gemini_minimal_thinking_by_default():
    import inspect
    from ai.gemini import generate_text
    p = inspect.signature(generate_text).parameters
    assert p["fast"].default is True and p["max_output_tokens"].default <= 4096


def test_flash_lite_preferred():
    from ai.gemini import select_models
    order = select_models(["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.5-pro"])
    assert order[0] == "gemini-3.5-flash-lite" and order[-1] == "gemini-3.5-pro"
