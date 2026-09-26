"""
Deep Playwright crawler — JS-rendered content extraction.

Hovers nav items to trigger dropdowns, discovers internal links,
follows sub-pages, returns aggregated text + structured page tree.
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

_MAX_PAGES   = 6   # sub-pages to follow after main
_NAV_TIMEOUT = 3000
_PAGE_TIMEOUT = 20000


async def _hover_and_collect(page) -> list[str]:
    """Hover all nav items to reveal dropdown links."""
    discovered: list[str] = []
    try:
        nav_items = await page.query_selector_all("nav a, header a, [role=navigation] a")
        for item in nav_items[:20]:
            try:
                await item.hover(timeout=1000)
                await page.wait_for_timeout(300)
            except Exception:
                pass

        # Collect any newly visible links
        all_links = await page.query_selector_all("a[href]")
        for link in all_links:
            href = await link.get_attribute("href")
            if href:
                discovered.append(href)
    except Exception as exc:
        logger.debug(f"hover_and_collect: {exc}")
    return discovered


async def _extract_page_text(page) -> dict:
    """Extract visible text, headings, meta from a loaded page."""
    try:
        title = await page.title()
        meta  = await page.evaluate(
            "() => document.querySelector('meta[name=description]')?.content || ''"
        )
        h1s   = await page.evaluate(
            "() => [...document.querySelectorAll('h1')].map(e => e.innerText.trim())"
        )
        h2s   = await page.evaluate(
            "() => [...document.querySelectorAll('h2')].map(e => e.innerText.trim())"
        )
        body  = await page.evaluate(
            "() => document.body?.innerText || ''"
        )
        return {
            "title":    title,
            "meta":     meta,
            "h1":       h1s,
            "h2":       h2s,
            "body_text": body[:8000],  # cap per page
        }
    except Exception as exc:
        logger.debug(f"extract_page_text: {exc}")
        return {}


def _same_origin(base: str, href: str) -> str | None:
    """Return absolute URL if same origin, else None."""
    try:
        abs_url = urljoin(base, href)
        b = urlparse(base)
        u = urlparse(abs_url)
        if b.netloc == u.netloc and u.scheme in ("http", "https"):
            # Skip anchors, query-only, common asset extensions
            if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|css|js|ico|woff|xml|zip)$", u.path, re.I):
                return None
            return abs_url
    except Exception:
        pass
    return None


async def deep_crawl(url: str, max_pages: int = _MAX_PAGES) -> dict:
    """
    Launch Playwright Chromium, crawl `url` and up to `max_pages` internal links.
    Returns aggregated structured data.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed — deep crawl unavailable")
        return {"error": "playwright not installed", "pages": []}

    pages_data: list[dict] = []
    visited: set[str] = set()
    queue: list[str] = [url]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

        while queue and len(pages_data) <= max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            page = await context.new_page()
            try:
                await page.goto(current_url, timeout=_PAGE_TIMEOUT, wait_until="domcontentloaded")
                await page.wait_for_timeout(800)  # let JS settle

                data = await _extract_page_text(page)
                data["url"] = current_url
                pages_data.append(data)

                # Only hover-discover on the main page
                if current_url == url:
                    raw_hrefs = await _hover_and_collect(page)
                    for href in raw_hrefs:
                        abs_url = _same_origin(url, href)
                        if abs_url and abs_url not in visited and abs_url not in queue:
                            queue.append(abs_url)
                    # Deduplicate + cap queue
                    queue = list(dict.fromkeys(queue))[:max_pages * 3]

            except Exception as exc:
                logger.warning(f"deep_crawl page error {current_url}: {exc}")
                pages_data.append({"url": current_url, "error": str(exc)})
            finally:
                await page.close()

        await context.close()
        await browser.close()

    return _aggregate(url, pages_data)


def _aggregate(root_url: str, pages: list[dict]) -> dict:
    """Merge per-page data into a single crawl result."""
    all_text   = []
    all_h1     = []
    all_h2     = []
    sub_pages  = []

    for p in pages:
        if "error" in p and "body_text" not in p:
            continue
        body = p.get("body_text", "")
        if body:
            all_text.append(body)
        all_h1.extend(p.get("h1", []))
        all_h2.extend(p.get("h2", []))
        if p.get("url") != root_url:
            sub_pages.append({
                "url":   p.get("url"),
                "title": p.get("title", ""),
                "h1":    p.get("h1", []),
            })

    combined_text = "\n\n".join(all_text)

    return {
        "pages_crawled":  len(pages),
        "combined_text":  combined_text[:20000],  # hard cap for HF calls
        "all_h1":         list(dict.fromkeys(all_h1))[:30],
        "all_h2":         list(dict.fromkeys(all_h2))[:60],
        "sub_pages":      sub_pages,
        "pages_detail":   pages,
    }
