"""B1 — SSRF hardening."""
import pytest

from conftest import FakeResponse

BAD_HOSTS = {
    "--1.sslip.io": ["::1"],
    "fd12--1.sslip.io": ["fd12::1"],
    "cgnat.test": ["100.64.1.1"],
    "meta.test": ["169.254.169.254"],
    "v6loop.test": ["::1"],
    "mixed.test": ["93.184.215.14", "10.0.0.5"],
}
BAD_URLS = [
    "http://--1.sslip.io:8080/",
    "https://fd12--1.sslip.io/",
    "http://100.64.1.1/",
    "http://[::ffff:127.0.0.1]/",
    "http://169.254.169.254/latest/meta-data/",
    "https://cgnat.test/",
    "https://meta.test/",
    "https://v6loop.test/",
    "https://mixed.test/",
]


def test_is_public_ip():
    from net_safety import is_public_ip
    assert is_public_ip("93.184.215.14")
    assert is_public_ip("2606:4700::1111")
    for bad in ("127.0.0.1", "10.1.2.3", "100.64.1.1", "169.254.169.254", "::1", "fd12::1",
                "::ffff:127.0.0.1", "::ffff:10.0.0.1", "fe80::1%en0", "0.0.0.0", "224.0.0.1", "nonsense"):
        assert not is_public_ip(bad), bad


@pytest.mark.parametrize("url", BAD_URLS)
def test_validate_url_rejects_private(dns, url):
    from models import _validate_url
    dns.update(BAD_HOSTS)
    with pytest.raises(ValueError):
        _validate_url(url)


@pytest.mark.parametrize("url", BAD_URLS)
def test_is_public_url_rejects_private(dns, url):
    import seo_utils
    dns.update(BAD_HOSTS)
    assert seo_utils._is_public_url(url) is False


def test_validate_url_fails_closed_on_lookup_failure(dns):
    from models import _validate_url
    with pytest.raises(ValueError, match="resolve"):
        _validate_url("https://does-not-exist.example-nope.com/")


def test_validate_url_accepts_public(public_dns):
    from models import _validate_url
    assert _validate_url("example.com/page") == "https://example.com/page"
    import seo_utils
    assert seo_utils._is_public_url("https://example.com/")
    assert seo_utils._is_public_url("https://nowhere.invalid/") is False   # lookup failure


def test_tier1_redirect_to_private_raises_blocked(public_dns, monkeypatch):
    import seo_utils
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        assert kw.get("allow_redirects") is False
        return FakeResponse(302, b"", {"Location": "http://10.0.0.1/"})

    monkeypatch.setattr(seo_utils.requests, "get", fake_get)
    with pytest.raises(seo_utils.FetchError) as ei:
        seo_utils._fetch_page.__wrapped__("https://example.com/")
    assert ei.value.kind == "blocked"
    assert "redirected to a private address" in str(ei.value)
    assert calls == ["https://example.com/"]       # the private hop was never requested


def test_tier1_relative_redirect_joins_current_hop(public_dns, monkeypatch):
    import seo_utils
    calls = []
    big = b"<html><head><title>x</title></head><body>" + b"word " * 200 + b"</body></html>"

    def fake_get(url, **kw):
        calls.append(url)
        if url == "https://example.com/a/start":
            return FakeResponse(302, b"", {"Location": "https://www.example.com/b/"})
        if url == "https://www.example.com/b/":
            return FakeResponse(301, b"", {"Location": "next"})
        return FakeResponse(200, big, {"Content-Type": "text/html; charset=utf-8"})

    monkeypatch.setattr(seo_utils.requests, "get", fake_get)
    soup, html, meta = seo_utils._fetch_page.__wrapped__("https://example.com/a/start")
    assert calls[-1] == "https://www.example.com/b/next"
    assert meta["final_url"] == "https://www.example.com/b/next"


def test_tier1_first_url_private_never_requested(dns, monkeypatch):
    import seo_utils
    dns.update(BAD_HOSTS)
    monkeypatch.setattr(seo_utils.requests, "get", lambda *a, **k: pytest.fail("requested a private host"))
    with pytest.raises(seo_utils.FetchError) as ei:
        seo_utils._fetch_page.__wrapped__("https://meta.test/")
    assert ei.value.kind == "blocked"


def test_tier1_size_cap_is_fetch_error(public_dns, monkeypatch):
    import seo_utils
    monkeypatch.setattr(seo_utils.requests, "get",
                        lambda url, **k: FakeResponse(200, b"x" * (5 * 1024 * 1024 + 10), {"Content-Type": "text/html"}))
    with pytest.raises(seo_utils.FetchError):
        seo_utils._fetch_page.__wrapped__("https://example.com/")


def test_paid_proxies_never_called_for_private_host(dns, monkeypatch):
    import seo_utils
    dns.update(BAD_HOSTS)
    monkeypatch.setattr(seo_utils, "_SCRAPER_API_KEY", "k")
    monkeypatch.setattr(seo_utils, "_ZENROWS_API_KEY", "k")
    monkeypatch.setattr(seo_utils.requests, "get", lambda *a, **k: pytest.fail("network call for a private host"))
    for fn in (seo_utils._fetch_with_scraperapi, seo_utils._fetch_with_zenrows):
        with pytest.raises(seo_utils.FetchError):
            fn("https://meta.test/")
    with pytest.raises(seo_utils.FetchError):
        seo_utils._fetch_page.__wrapped__("https://meta.test/")


def test_robots_redirect_to_private_returns_no_body(public_dns, monkeypatch):
    import geo_utils
    import net_safety

    def fake_get(url, **kw):
        assert kw.get("allow_redirects") is False
        if url == "https://example.com/robots.txt":
            return FakeResponse(302, b"", {"Location": "http://127.0.0.1/robots.txt"})
        pytest.fail(f"followed redirect to {url}")

    monkeypatch.setattr(net_safety.requests, "get", fake_get)
    out = geo_utils.check_ai_crawlers("https://example.com/")
    assert out["raw_robots"] == ""


def test_raw_robots_truncated(public_dns, monkeypatch):
    import geo_utils
    import net_safety
    body = ("User-agent: *\nDisallow: /x\n" + "# filler line\n" * 2000).encode()
    monkeypatch.setattr(net_safety.requests, "get",
                        lambda url, **k: FakeResponse(200, body, {"Content-Type": "text/plain"}))
    out = geo_utils.check_ai_crawlers("https://example.com/")
    assert 0 < len(out["raw_robots"]) <= 5000


# ── Round-4 pen-test regressions ──────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://127.0.0.1\\@example.com/",          # urlparse: example.com, requests: 127.0.0.1
    "http://10.0.0.1:8080\\@example.com/x",
])
def test_backslash_parser_gap_rejected(public_dns, url):
    import seo_utils
    from models import _validate_url
    with pytest.raises(ValueError):
        _validate_url(url)
    assert seo_utils._is_public_url(url) is False
    with pytest.raises(seo_utils.FetchError) as ei:
        seo_utils._assert_public(url)
    assert ei.value.kind == "blocked"


def test_safe_get_refuses_backslash_hop(public_dns, monkeypatch):
    import net_safety
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return FakeResponse(302, b"", {"Location": "http://127.0.0.1\\@example.com/robots.txt"})

    monkeypatch.setattr(net_safety.requests, "get", fake_get)
    assert net_safety.safe_get("https://example.com/robots.txt") is None
    assert calls == ["https://example.com/robots.txt"]


def test_ipv6_embedded_ipv4_forms_not_public():
    from net_safety import is_public_ip
    for bad in ("64:ff9b::7f00:1", "64:ff9b::a9fe:a9fe", "::127.0.0.1", "2002:7f00:1::",
                "2001:0:4136:e378:8000:63bf:3fff:fdd2", "fec0::1", "::FFFF:7F00:1"):
        assert not is_public_ip(bad), bad
    assert is_public_ip("64:ff9b::808:808")          # NAT64 of 8.8.8.8 is still public
