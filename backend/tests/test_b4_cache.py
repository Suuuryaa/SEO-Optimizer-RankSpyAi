"""B4 — Redis result cache (JSON-body commands) + SCORING_VERSION."""
import asyncio
import json
from types import SimpleNamespace

import pytest


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(json)
        cmd = json[0].upper()
        if cmd == "SET":
            self.store[json[1]] = json[2]
            result = "OK"
        elif cmd == "GET":
            result = self.store.get(json[1])
        else:
            result = None
        return SimpleNamespace(json=lambda: {"result": result})


@pytest.fixture
def fake_redis(monkeypatch):
    import cache
    r = FakeRedis()
    monkeypatch.setattr(cache, "UPSTASH_REDIS_REST_URL", "https://redis.invalid")
    monkeypatch.setattr(cache, "UPSTASH_REDIS_REST_TOKEN", "t")
    monkeypatch.setattr(cache.requests, "post", r.post)
    monkeypatch.setattr(cache.requests, "get", lambda *a, **k: pytest.fail("path-style Redis call"))
    return r


def test_cache_key_has_version():
    import cache
    from scoring import SCORING_VERSION
    assert SCORING_VERSION == "1.1"
    assert cache._cache_key("https://a.com", "kw").startswith("result:v1.1:")


def test_set_cached_posts_json_command(fake_redis):
    import cache
    cache.set_cached("https://a.com", "kw", {"seo_score": 50, "_soup": object()})
    body = fake_redis.calls[-1]
    assert body[0] == "SET" and body[1] == cache._cache_key("https://a.com", "kw")
    assert body[3:] == ["EX", 21600]
    stored = json.loads(body[2])
    assert "_soup" not in stored and stored["cached_at"]


def test_round_trip_special_chars(fake_redis):
    import cache
    data = {"title": "Deals /ex/1?x=1#frag & more", "seo_score": 70}
    cache.set_cached("https://a.com/p?q=1#h", "a/b?c", data)
    got = cache.get_cached("https://a.com/p?q=1#h", "a/b?c")
    assert got["title"] == data["title"] and got["seo_score"] == 70


def test_redis_set_ex_posts_json(fake_redis):
    import cache
    cache._redis_set_ex("keyok:abc", "1", 3600)
    assert fake_redis.calls[-1] == ["SET", "keyok:abc", "1", "EX", 3600]


def _request(ip="203.0.113.5"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={})


def _run_analyze(req):
    import main
    return asyncio.run(main.analyze(req, _request()))


def test_cache_hit_costs_no_credit_fresh_is_charged(public_dns, monkeypatch):
    import main
    from models import AnalyzeRequest
    stored = {}
    consumed = []
    monkeypatch.setattr(main, "get_cached", lambda u, k: dict(stored[(u, k)]) if (u, k) in stored else None)
    monkeypatch.setattr(main, "set_cached", lambda u, k, d: stored.__setitem__((u, k), {**{x: y for x, y in d.items() if not x.startswith("_")}, "cached_at": "2026-11-07T00:00:00+00:00"}))
    monkeypatch.setattr(main, "check_and_consume", lambda user_has_own_keys=False: consumed.append(1) or {"allowed": True, "uses": len(consumed), "remaining": 100 - len(consumed)})
    monkeypatch.setattr(main, "get_global_uses", lambda: len(consumed))
    monkeypatch.setattr(main, "_full_seo_analysis",
                        lambda u, k, keys: {"seo_score": 60, "technical_seo": {}, "_soup": None, "_text": ""})

    req = AnalyzeRequest(url="https://example.com/", keyword="seo")
    first = _run_analyze(req)
    assert first["cached"] is False and first["cached_at"] is None and len(consumed) == 1

    second = _run_analyze(req)
    assert second["cached"] is True and second["cached_at"] and len(consumed) == 1
    assert second["pool_uses"] == 1 and second["pool_remaining"] == 99

    third = _run_analyze(AnalyzeRequest(url="https://example.com/", keyword="seo", fresh=True))
    assert third["cached"] is False and len(consumed) == 2


def test_cache_key_path_case_sensitive():
    """Round-4: /Page and /page are different pages (multi-tenant hosts), so one
    must not be served the other's cached result; host/scheme case doesn't matter."""
    import cache
    assert cache._cache_key("https://host.com/~Alice", "kw") != cache._cache_key("https://host.com/~alice", "kw")
    assert cache._cache_key("HTTPS://HOST.com/a", "KW") == cache._cache_key("https://host.com/a", "kw")
