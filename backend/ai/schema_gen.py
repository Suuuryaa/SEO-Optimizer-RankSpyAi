"""
Automated JSON-LD Schema Markup Generator.

Detects page type from content signals and generates ready-to-paste
structured data. No AI model needed — pure heuristics.

Supported schemas:
  - WebPage (default)
  - Article / BlogPosting
  - Product
  - LocalBusiness
  - FAQPage
  - BreadcrumbList
"""

import json
import re
from urllib.parse import urlparse


def _detect_page_type(
    url: str,
    title: str,
    text: str,
    h1_tags: list,
    tech_seo: dict,
) -> str:
    url_lower  = url.lower()
    text_lower = text.lower()
    heading    = " ".join([title or ""] + list(h1_tags or [])).lower()

    def hits(patterns, haystack):
        return sum(1 for p in patterns if re.search(p, haystack))

    # FAQ — the page itself must be an FAQ (URL/title/H1) or contain real Q&A pairs.
    # A nav link labelled "FAQ" on a homepage is not enough.
    if (re.search(r'faq|frequently-asked', url_lower)
            or re.search(r'\bfaqs?\b|frequently asked', heading)
            or len(_extract_faq_pairs(text)) >= 3):
        return "FAQPage"

    # Product — product URL, or at least two commerce signals
    if re.search(r'/products?/|/shop/|/item/|/p/', url_lower):
        return "Product"
    if hits([r'add to (cart|bag|basket)', r'buy now', r'in stock', r'out of stock',
             r'[$€£₹]\s?\d[\d,]*(\.\d{2})?'], text_lower) >= 2:
        return "Product"

    # Article — article-style URL, or byline + publish date together
    if re.search(r'/(blog|article|articles|post|posts|news)/', url_lower):
        return "Article"
    if hits([r'\bby [a-z]+ [a-z]+', r'published( on)?\s', r'author:'], text_lower) >= 2:
        return "Article"

    # Local business — at least two of hours / address / phone / directions
    if hits([r'opening hours|hours:', r'address:', r'phone:|tel:', r'\(\d{3}\)\s?\d{3}',
             r'get directions'], text_lower) >= 2:
        return "LocalBusiness"

    return "WebPage"


def _extract_faq_pairs(text: str) -> list[dict]:
    """Very simple Q&A extractor — finds question-like sentences followed by answers."""
    pairs = []
    sentences = re.split(r'\n+', text)
    i = 0
    while i < len(sentences) - 1 and len(pairs) < 8:
        s = sentences[i].strip()
        if s.endswith('?') and 10 < len(s) < 200:
            answer = sentences[i + 1].strip()
            if len(answer) > 20:
                pairs.append({"question": s, "answer": answer[:500]})
                i += 2
                continue
        i += 1
    return pairs


def generate_schema(
    url: str,
    title: str,
    meta_description: str,
    h1_tags: list,
    page_text: str,
    tech_seo: dict,
    word_count: int,
) -> dict:
    """
    Generate JSON-LD schema markup for the page.

    Returns:
        {
            page_type: str,
            schemas: list[dict],   # list of JSON-LD objects
            schema_html: str,      # ready-to-paste <script> block
            count: int,
        }
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    page_type = _detect_page_type(url, title, page_text, h1_tags, tech_seo)

    schemas = []

    # ── Always add WebSite schema on homepage ─────────────────────────────────
    if parsed.path in ('', '/', '/index.html'):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": title or domain,
            "url": f"{parsed.scheme}://{domain}",
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{parsed.scheme}://{domain}/search?q={{search_term_string}}"
                },
                "query-input": "required name=search_term_string"
            }
        })

    # ── Page-type-specific schema ─────────────────────────────────────────────
    if page_type == "FAQPage":
        pairs = _extract_faq_pairs(page_text)
        if pairs:
            schemas.append({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": p["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": p["answer"]
                        }
                    }
                    for p in pairs
                ]
            })

    elif page_type == "Product":
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": h1_tags[0] if h1_tags else title,
            "description": meta_description or "",
            "url": url,
            "offers": {
                "@type": "Offer",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": url
            }
        })

    elif page_type == "LocalBusiness":
        schemas.append({
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": h1_tags[0] if h1_tags else title,
            "description": meta_description or "",
            "url": url,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "<!-- Add street address -->",
                "addressLocality": "<!-- Add city -->",
                "addressRegion": "<!-- Add state -->",
                "postalCode": "<!-- Add zip -->",
                "addressCountry": "US"
            },
            "telephone": "<!-- Add phone -->"
        })

    elif page_type == "Article":
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": h1_tags[0] if h1_tags else title,
            "description": meta_description or "",
            "url": url,
            "author": {
                "@type": "Person",
                "name": "<!-- Add author name -->"
            },
            "publisher": {
                "@type": "Organization",
                "name": domain,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{parsed.scheme}://{domain}/logo.png"
                }
            },
            "datePublished": "<!-- Add publish date -->",
            "dateModified": "<!-- Add modified date -->"
        })

    else:  # WebPage default
        schemas.append({
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title or "",
            "description": meta_description or "",
            "url": url,
            "breadcrumb": {
                "@type": "BreadcrumbList",
                "itemListElement": [{
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": f"{parsed.scheme}://{domain}"
                }]
            }
        })

    # ── Render <script> block ─────────────────────────────────────────────────
    blocks = "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, indent=2)}\n</script>'
        for s in schemas
    )

    return {
        "page_type":   page_type,
        "schemas":     schemas,
        "schema_html": blocks,
        "count":       len(schemas),
    }
