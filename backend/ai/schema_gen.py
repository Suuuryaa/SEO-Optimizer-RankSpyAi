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

    # FAQ
    faq_patterns = [r'\bfaq\b', r'frequently asked', r'question.*answer']
    if any(re.search(p, url_lower + text_lower) for p in faq_patterns):
        return "FAQPage"

    # Product
    product_patterns = [r'\$[\d,]+', r'add to cart', r'buy now', r'in stock', r'out of stock', r'/product', r'/shop']
    if any(re.search(p, url_lower + text_lower) for p in product_patterns):
        return "Product"

    # Local business
    local_patterns = [r'hours?:', r'open.*am', r'address:', r'phone:', r'\(\d{3}\)', r'directions']
    if any(re.search(p, text_lower) for p in local_patterns):
        return "LocalBusiness"

    # Article / blog
    article_patterns = [r'/blog/', r'/article', r'/post/', r'/news/', r'published', r'author:']
    if any(re.search(p, url_lower + text_lower) for p in article_patterns):
        return "Article"

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
