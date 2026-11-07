"""
Test setup: no network, no production Redis, no real API keys.

Env vars are blanked BEFORE any backend module is imported; load_dotenv never
overrides variables that already exist, so backend/.env (production Redis)
is never used by the tests.
"""
import os
import socket
import sys

for _k in ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "SERPER_API_KEY", "GEMINI_API_KEY",
           "PAGESPEED_API_KEY", "SCRAPER_API_KEY", "ZENROWS_API_KEY", "ADMIN_SECRET", "HF_TOKEN",
           "SUPABASE_URL", "SUPABASE_KEY", "RESEND_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD",
           "ENABLE_LEGACY_ENDPOINTS"):
    os.environ[_k] = ""
os.environ["GLOBAL_LIMIT"] = "100"

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import pytest  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_html(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


class _NoNetwork(Exception):
    pass


@pytest.fixture(autouse=True)
def dns(monkeypatch):
    """Fake resolver: tests add {host: [addresses]}; anything else fails to resolve.

    Real sockets can't connect anywhere, so nothing leaves the machine.
    """
    table: dict = {}

    def fake_getaddrinfo(host, port, *args, **kwargs):
        host = (host or "").strip("[]")
        if host in table:
            out = []
            for addr in table[host]:
                fam = socket.AF_INET6 if ":" in addr else socket.AF_INET
                sa = (addr, port or 0, 0, 0) if fam == socket.AF_INET6 else (addr, port or 0)
                out.append((fam, socket.SOCK_STREAM, 6, "", sa))
            return out
        raise socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided (test resolver)")

    def no_connect(self, *a, **k):
        raise _NoNetwork("network disabled in tests")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", no_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", no_connect)
    return table


@pytest.fixture
def public_dns(dns):
    dns.update({"example.com": ["93.184.215.14"], "www.example.com": ["93.184.215.14"],
                "public.test": ["93.184.215.15"]})
    return dns


@pytest.fixture(autouse=True)
def _clear_caches():
    import seo_utils
    with seo_utils._PAGE_CACHE_LOCK:
        seo_utils._PAGE_CACHE.clear()
        seo_utils._page_cache_bytes = 0
    yield


class FakeResponse:
    """Minimal stand-in for requests.Response used by mocked requests.get/post."""

    def __init__(self, status=200, body=b"", headers=None, json_data=None):
        self.status_code = status
        self.headers = headers or {}
        self._body = body if isinstance(body, bytes) else body.encode()
        self._json = json_data
        self.closed = False
        self._content = self._body
        self.url = None

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308) and "Location" in self.headers

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        self.closed = True

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._content.decode("utf-8", errors="replace")

    @property
    def apparent_encoding(self):
        return "utf-8"

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def analyse(monkeypatch, public_dns):
    """Run main._full_seo_analysis on a fixture file with fetching mocked out.

    analyse(name, url=..., keyword=..., meta={...}, robots_allows=True)
    """
    import main
    import seo_utils
    from bs4 import BeautifulSoup

    def run(name, url="https://example.com/page", keyword="seo", meta=None, robots_allows=True, render=None):
        html = fixture_html(name)
        monkeypatch.setattr(main, "get_page_soup", lambda u: (BeautifulSoup(html, "lxml"), html))
        monkeypatch.setattr(main, "get_page_meta", lambda u: meta)
        monkeypatch.setattr(seo_utils, "robots_txt_allows", lambda u, ua="Googlebot": robots_allows)
        monkeypatch.setattr(main, "render_page_html", render or (lambda u: None))
        out = main._full_seo_analysis(url, keyword, {})
        out.pop("_soup", None)
        out.pop("_text", None)
        return out

    return run
