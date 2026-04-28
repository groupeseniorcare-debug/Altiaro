"""Phase B1 — Helpers JSON-LD multilingues."""
from __future__ import annotations
from typing import List


def _val(v, lang: str, fallback: str = "fr"):
    """Picks the right language from a dict or returns the raw scalar."""
    if isinstance(v, dict):
        if not v:
            return ""
        return v.get(lang) or v.get(fallback) or v.get("en") or next(iter(v.values()), "")
    return v or ""


def organization(site: dict) -> dict:
    brand = (site.get("design") or {}).get("brand") or {}
    name = _val(brand.get("name") or site.get("name"), "fr")
    return {
        "@context": "https://schema.org", "@type": "Organization",
        "name": name, "url": site.get("public_url") or "",
        "logo": brand.get("logo_url") or "",
    }


def website(site: dict) -> dict:
    base = site.get("public_url") or ""
    return {
        "@context": "https://schema.org", "@type": "WebSite",
        "url": base, "name": _val(site.get("name"), "fr"),
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{base}/search?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }


def breadcrumbs(items: List[dict]) -> dict:
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": it["name"], "item": it["url"]} for i, it in enumerate(items)],
    }


def product(product: dict, site: dict, lang: str, currency: str = "EUR") -> dict:
    name = _val(product.get("name"), lang)
    desc = _val(product.get("description"), lang)
    base = site.get("public_url") or ""
    images = product.get("images") or []
    return {
        "@context": "https://schema.org", "@type": "Product",
        "name": name, "description": (desc or "")[:5000],
        "sku": product.get("sku") or product.get("id"),
        "brand": {"@type": "Brand", "name": _val((site.get("design") or {}).get("brand", {}).get("name"), "fr")},
        "image": images[:5],
        "material": product.get("material_canonical") or product.get("material"),
        "offers": {
            "@type": "Offer", "priceCurrency": currency,
            "price": str(product.get("price") or 0),
            "availability": "https://schema.org/InStock",
            "url": f"{base}/product/{product.get('id')}",
        },
    }


def faq_page(faqs: List[dict], lang: str) -> dict:
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": _val(f.get("q"), lang), "acceptedAnswer": {"@type": "Answer", "text": _val(f.get("a"), lang)}} for f in (faqs or [])],
    }


def howto(steps: List[dict], lang: str) -> dict:
    return {
        "@context": "https://schema.org", "@type": "HowTo",
        "step": [{"@type": "HowToStep", "position": i + 1, "name": _val(s.get("title"), lang), "text": _val(s.get("detail") or s.get("description"), lang)} for i, s in enumerate(steps or [])],
    }


def article(post: dict, lang: str) -> dict:
    return {
        "@context": "https://schema.org", "@type": "Article",
        "headline": _val(post.get("title"), lang),
        "description": _val(post.get("excerpt"), lang),
        "datePublished": post.get("created_at"),
        "dateModified": post.get("updated_at") or post.get("created_at"),
        "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", ".article-tldr"]},
    }


def hreflang_alternates(base_url: str, path: str, available_langs: List[str], default: str = "fr") -> List[dict]:
    out = []
    for lang in available_langs:
        out.append({"hreflang": lang, "href": f"{base_url}/{lang}{path}"})
    out.append({"hreflang": "x-default", "href": f"{base_url}/{default}{path}"})
    return out
