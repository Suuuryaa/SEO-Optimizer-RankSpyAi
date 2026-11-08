"""Private search log: rows, 3-day expiry, admin-only Excel download."""
import io
import json

import pytest

import search_log


class FakeRedis:
    def __init__(self):
        self.lists, self.ttl = {}, {}

    def __call__(self, *args):
        op, key = args[0], args[1]
        if op == "RPUSH":
            self.lists.setdefault(key, []).append(args[2])
            return len(self.lists[key])
        if op == "EXPIRE":
            self.ttl[key] = args[2]
            return 1
        if op == "LRANGE":
            return list(self.lists.get(key, []))
        if op == "LLEN":
            return len(self.lists.get(key, []))
        if op == "LTRIM":
            self.lists[key] = self.lists[key][args[2]:]
            return "OK"


@pytest.fixture
def fake(monkeypatch):
    f = FakeRedis()
    monkeypatch.setattr(search_log, "_cmd", f)
    return f


def test_row_has_no_ip_and_flags_bots():
    row = search_log.build_row("https://www.woolworths.co.nz/", "groceries",
                               {"user-agent": "Googlebot/2.1", "cf-ipcountry": "US"}, cached=False)
    assert row["website"] == "https://www.woolworths.co.nz/"
    assert row["keyword"] == "groceries"
    assert row["visitor_country"] == "US"
    assert row["site_country"] == "New Zealand"
    assert row["looks_like_bot"] is True
    assert not any("ip" == k or k.endswith("_ip") for k in row)


def test_real_browser_not_bot():
    ua = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
    assert search_log.looks_like_bot(ua) is False
    assert search_log._browser(ua) == "Chrome"


def test_record_sets_expiry_once_and_reads_back(fake):
    r = search_log.build_row("https://a.co.nz/", "k", {}, cached=True)
    search_log.record(r)
    search_log.record(r)
    key = "searchlog:" + r["time_nz"][:10]
    assert len(fake.lists[key]) == 2
    assert fake.ttl[key] == search_log.KEEP_SECONDS == 4 * 24 * 3600
    assert search_log.get_day(r["time_nz"][:10])[0]["from_cache"] is True


def test_record_never_raises(monkeypatch):
    def boom(*a):
        raise RuntimeError("redis down")
    monkeypatch.setattr(search_log, "_cmd", boom)
    search_log.record({"time_nz": "2026-11-09 10:00:00"})  # must not raise


def test_xlsx_has_header_and_rows():
    from openpyxl import load_workbook
    rows = [search_log.build_row("https://x.com/", "shoes", {}, cached=False)]
    wb = load_workbook(io.BytesIO(search_log.to_xlsx(rows, "2026-11-09")))
    ws = wb.active
    assert [c.value for c in ws[1]] == search_log.COLUMNS
    assert ws.cell(2, 2).value == "https://x.com/"
    assert ws.cell(2, 3).value == "shoes"


def test_admin_endpoint_requires_key(monkeypatch, fake):
    from fastapi.testclient import TestClient
    import main
    monkeypatch.setattr(main, "ADMIN_SECRET", "s3cret")
    c = TestClient(main.app)
    assert c.get("/admin/search-log").status_code == 403
    assert c.get("/admin/search-log?key=wrong").status_code == 403
    ok = c.get("/admin/search-log?key=s3cret&date=2026-11-09")
    assert ok.status_code == 200
    assert "spreadsheetml" in ok.headers["content-type"]
    assert c.get("/admin/search-log?key=s3cret&date=../etc").status_code == 400
    assert c.get("/admin/search-log/days?key=s3cret").json() == {"days": []}
