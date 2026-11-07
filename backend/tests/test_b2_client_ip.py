"""B2 — client IP behind Railway's proxy and constant-time admin check."""
from types import SimpleNamespace

import pytest


def _req(host, headers):
    return SimpleNamespace(client=SimpleNamespace(host=host), headers={k: v for k, v in headers.items()})


def test_forged_xff_not_trusted_behind_railway():
    import main
    r = _req("100.64.1.1", {"X-Forwarded-For": "1.2.3.4"})
    assert main._client_ip(r) == "100.64.1.1"


def test_x_real_ip_trusted_behind_railway():
    import main
    r = _req("100.64.1.1", {"X-Real-IP": "8.8.8.8", "X-Forwarded-For": "1.2.3.4"})
    assert main._client_ip(r) == "8.8.8.8"


def test_headers_ignored_from_direct_client():
    import main
    r = _req("203.0.113.9", {"X-Real-IP": "8.8.8.8"})
    assert main._client_ip(r) == "203.0.113.9"


def test_admin_reset_uses_compare_digest(monkeypatch):
    import main
    from fastapi import HTTPException
    monkeypatch.setattr(main, "ADMIN_SECRET", "s3cret")
    used = []
    import hmac
    real = hmac.compare_digest
    monkeypatch.setattr(hmac, "compare_digest", lambda a, b: used.append(1) or real(a, b))
    with pytest.raises(HTTPException) as ei:
        main.admin_reset_pool("wrong")
    assert ei.value.status_code == 403 and used
    with pytest.raises(HTTPException):
        main.admin_reset_pool(None)
