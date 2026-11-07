"""B7 — helper gating, page cache, pool fairness, job caps, quotas, legacy routes."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _request(ip="203.0.113.5"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={})


@pytest.fixture
def client():
    import main
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def helper_mocks(monkeypatch, public_dns):
    import main
    consumed = []
    monkeypatch.setattr(main, "check_and_consume",
                        lambda user_has_own_keys=False: consumed.append(1) or {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "_full_seo_analysis", lambda u, k, keys: {
        "title": "t", "meta_description": "m", "h1_tags": [], "title_length": 1, "meta_length": 1,
        "technical_seo": {}, "word_count": 10, "_soup": None, "_text": ""})
    monkeypatch.setattr(main, "generate_meta_suggestions", lambda *a: {"suggestions": []})
    monkeypatch.setattr(main, "check_ip_quota", lambda ip, bucket, limit: True)
    return consumed


def test_helper_after_cached_scan_is_free(client, helper_mocks, monkeypatch):
    import main
    monkeypatch.setattr(main, "page_cached", lambda u: True)
    r = client.post("/suggest-meta", json={"url": "https://example.com/", "keyword": "seo"})
    assert r.status_code == 200, r.text
    assert helper_mocks == []


def test_helper_uncached_costs_one_credit(client, helper_mocks, monkeypatch):
    import main
    monkeypatch.setattr(main, "page_cached", lambda u: False)
    r = client.post("/suggest-meta", json={"url": "https://example.com/", "keyword": "seo"})
    assert r.status_code == 200, r.text
    assert helper_mocks == [1]


def test_page_cached_covers_rendered(monkeypatch):
    import seo_utils
    assert not seo_utils.page_cached("https://example.com/r")
    seo_utils._cache_put(("https://example.com/r", "rendered"), "<html>" + "x" * 600 + "</html>")
    assert seo_utils.page_cached("https://example.com/r")


def test_page_cache_byte_cap_and_skip_big(monkeypatch):
    import seo_utils
    monkeypatch.setattr(seo_utils, "_PAGE_CACHE_MAX_BYTES", 3000)
    for i in range(5):
        seo_utils._cache_put(f"u{i}", "a" * 1000)
    assert seo_utils._page_cache_bytes <= 3000
    assert "u0" not in seo_utils._PAGE_CACHE and "u4" in seo_utils._PAGE_CACHE
    seo_utils._cache_put("big", "b" * (2 * 1024 * 1024 + 1))
    assert "big" not in seo_utils._PAGE_CACHE


def test_pool_incr_first_and_decr_when_over(monkeypatch):
    import rate_limiter
    calls = []
    monkeypatch.setattr(rate_limiter, "increment_global_uses", lambda: calls.append("incr") or rate_limiter.GLOBAL_LIMIT + 1)
    monkeypatch.setattr(rate_limiter, "_redis_decr", lambda k: calls.append("decr") or rate_limiter.GLOBAL_LIMIT)
    out = rate_limiter.check_and_consume()
    assert out["allowed"] is False and calls == ["incr", "decr"]


def test_refund_floor_zero(monkeypatch):
    import rate_limiter
    sets = []
    monkeypatch.setattr(rate_limiter, "_redis_decr", lambda k: -1)
    monkeypatch.setattr(rate_limiter, "_redis_set", lambda k, v: sets.append((k, v)))
    rate_limiter.refund()
    assert sets == [("global:uses", "0")]


def test_404_primary_refunds(public_dns, monkeypatch):
    import main
    from models import AnalyzeRequest
    from seo_utils import FetchError
    refunds = []
    monkeypatch.setattr(main, "get_cached", lambda u, k: None)
    monkeypatch.setattr(main, "check_and_consume", lambda user_has_own_keys=False: {"allowed": True, "uses": 1, "remaining": 99})
    monkeypatch.setattr(main, "refund", lambda: refunds.append(1))

    def boom(u, k, keys):
        raise FetchError("not_found", "The page returned 404 Not Found.", 404)
    monkeypatch.setattr(main, "_full_seo_analysis", boom)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.analyze(AnalyzeRequest(url="https://example.com/", keyword="x"), _request()))
    assert ei.value.status_code == 422 and ei.value.error_kind == "not_found"
    assert refunds == [1]


def test_third_concurrent_job_same_ip_429_and_global_cap(monkeypatch):
    import main
    monkeypatch.setattr(main, "_JOBS", {})

    async def scenario():
        gate = asyncio.Event()

        async def slow():
            await gate.wait()
            return {"ok": True}

        main._start_job("analyze", slow, "1.1.1.1")
        main._start_job("analyze", slow, "1.1.1.1")
        with pytest.raises(HTTPException) as ei:
            main._start_job("analyze", slow, "1.1.1.1")
        assert ei.value.status_code == 429
        main._start_job("analyze", slow, "2.2.2.2")      # another visitor is fine
        # fill the global unfinished cap
        for i in range(main._JOBS_UNFINISHED_MAX - 3):
            main._start_job("analyze", slow, f"10.0.{i}.1")
        with pytest.raises(HTTPException) as ei:
            main._start_job("analyze", slow, "3.3.3.3")
        assert ei.value.status_code == 503
        gate.set()
        await asyncio.sleep(0.05)
        assert all(j["status"] == "done" for j in main._JOBS.values())
        assert not main._JOB_TASKS

    asyncio.run(scenario())


def test_finished_jobs_purged_after_ttl(monkeypatch):
    import main
    monkeypatch.setattr(main, "_JOBS", {"old": {"status": "done", "finished": 1.0, "ip": "x"}})
    main._purge_jobs()
    assert main._JOBS == {}


def test_job_timeout_sets_error_kind(monkeypatch):
    import main
    monkeypatch.setattr(main, "_JOBS", {})
    monkeypatch.setattr(main, "_JOB_TIMEOUT", 0.05)

    async def scenario():
        async def hang():
            await asyncio.sleep(5)
        out = main._start_job("analyze", hang, "1.1.1.1")
        await asyncio.sleep(0.2)
        return main._JOBS[out["job_id"]]

    job = asyncio.run(scenario())
    assert job["status"] == "error" and job["error_kind"] == "timeout"


def test_ip_quota_redis_failure_enforced_in_process(monkeypatch):
    import cache
    monkeypatch.setattr(cache, "UPSTASH_REDIS_REST_URL", "https://redis.invalid")
    monkeypatch.setattr(cache, "UPSTASH_REDIS_REST_TOKEN", "t")
    monkeypatch.setattr(cache, "_LOCAL_QUOTA", {})

    def boom(*a, **k):
        raise RuntimeError("redis down")
    monkeypatch.setattr(cache, "_redis_cmd", boom)
    results = [cache.check_ip_quota("9.9.9.9", "helpers", 3) for _ in range(5)]
    assert results == [True, True, True, False, False]


def test_rankings_off_by_default(client, public_dns):
    # No accounts yet: /rankings would show anyone's tracked keywords, so it's off
    assert client.get("/rankings", params={"url": "https://example.com/"}).status_code == 404
    assert client.post("/track", json={"url": "https://example.com/", "keyword": "x"}).status_code == 404


def test_rankings_gated_when_enabled(client, monkeypatch):
    import main
    monkeypatch.setattr(main, "RANK_TRACKER_ENABLED", True)
    monkeypatch.setattr(main, "check_ip_quota", lambda ip, bucket, limit: bucket != "rankings")
    r = client.get("/rankings", params={"url": "https://example.com/"})
    assert r.status_code == 429


def test_legacy_routes_absent_by_default(client):
    for path in ("/analyze", "/competitors", "/compare", "/leaderboard", "/pagespeed"):
        assert client.post(path, json={}).status_code == 404, path


def test_ipv6_visitor_bucketed_by_64(monkeypatch):
    """Round-4: one IPv6 host owns a /64, so rotating addresses inside it can't
    bypass the 2-running-scans cap (and fill the global queue for free)."""
    import main
    monkeypatch.setattr(main, "_JOBS", {})

    async def scenario():
        gate = asyncio.Event()

        async def slow():
            await gate.wait()
            return {"ok": True}

        main._start_job("analyze", slow, "2001:db8:1:2::1")
        main._start_job("analyze", slow, "2001:db8:1:2::2")
        with pytest.raises(HTTPException) as ei:
            main._start_job("analyze", slow, "2001:db8:1:2:ffff::3")
        assert ei.value.status_code == 429
        main._start_job("analyze", slow, "2001:db8:1:3::1")    # another /64 is another visitor
        gate.set()
        await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert main._job_ip_bucket("1.2.3.4") == "1.2.3.4"
    assert main._job_ip_bucket("::ffff:1.2.3.4") == "1.2.3.4"
    assert main._job_ip_bucket("unknown") == "unknown"
