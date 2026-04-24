"""Unit tests for the internal linking engine."""
import re

import pytest

from routes.internal_linking import (
    _build_link_map,
    _inject_links_into_body,
    _normalize_keyword,
)


def make_site(blog_posts=None, collections=None):
    return {
        "id": "site-1",
        "design": {
            "blog_posts": blog_posts or [],
            "collections": collections or [],
        },
    }


def test_build_link_map_sorts_pillar_first():
    site = make_site(
        blog_posts=[
            {"slug": "entretien-fauteuil", "title": "Entretien du fauteuil releveur"},
            {"slug": "guide-ultime", "title": "Guide ultime des fauteuils releveurs", "is_pillar": True},
        ],
    )
    products = [{"id": "p-1", "name": "Fauteuil releveur XL"}]
    link_map = _build_link_map(site, products)
    # Pillar doit être devant le produit (priority 10 > 8)
    assert link_map[0]["type"] == "blog_pillar"
    # Le produit doit être avant le blog standard (priority 8 > 4)
    product_idx = next(i for i, e in enumerate(link_map) if e["type"] == "product")
    standard_idx = next(i for i, e in enumerate(link_map) if e["type"] == "blog")
    assert product_idx < standard_idx


def test_build_link_map_skips_upsells():
    site = make_site()
    products = [
        {"id": "p-1", "name": "Fauteuil releveur XL"},
        {"id": "p-2", "name": "Housse protection", "role": "upsell"},
    ]
    link_map = _build_link_map(site, products)
    assert len(link_map) == 1
    assert link_map[0]["ref_id"] == "p-1"


def test_build_link_map_filters_short_or_stop_words():
    site = make_site(
        blog_posts=[
            {"slug": "court", "title": "Le"},  # stop word
            {"slug": "ok", "title": "Bien"},  # trop court
            {"slug": "good", "title": "Bien choisir son matelas"},  # ok
        ],
    )
    link_map = _build_link_map(site, [])
    keywords = [e["keyword"] for e in link_map]
    assert "Bien choisir son matelas" in keywords
    assert "Le" not in keywords
    assert "Bien" not in keywords


def test_inject_links_respects_max():
    body = (
        "Le fauteuil releveur est essentiel. "
        "La collection fauteuil sommeil offre du confort. "
        "Choisir un fauteuil releveur adapté demande du soin."
    )
    link_map = [
        {"keyword": "fauteuil releveur", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    new_body, added = _inject_links_into_body(body, link_map, max_links=5)
    # Un seul lien, malgré 2 occurrences du keyword (one per document)
    assert len(added) == 1
    # Vérifie le markdown : [fauteuil releveur](/product/abc)
    assert "[fauteuil releveur](/product/abc)" in new_body
    # Seulement la PREMIÈRE occurrence remplacée
    assert new_body.count("/product/abc") == 1


def test_inject_links_skips_existing_markdown():
    body = "Voir [fauteuil releveur](/autre-url) pour plus de détails."
    link_map = [
        {"keyword": "fauteuil releveur", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    _, added = _inject_links_into_body(body, link_map, max_links=5)
    # Pas d'ajout car le keyword est déjà dans un lien existant
    assert len(added) == 0


def test_inject_links_skips_code_blocks():
    body = "```\nfauteuil releveur\n```\nLe fauteuil releveur ici."
    link_map = [
        {"keyword": "fauteuil releveur", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    new_body, added = _inject_links_into_body(body, link_map, max_links=5)
    # L'occurrence dans le code-block n'est pas liée, mais celle hors code-block l'est
    assert len(added) == 1
    # Le code block original intact
    assert "```\nfauteuil releveur\n```" in new_body


def test_inject_links_respects_self_url():
    body = "Le fauteuil releveur est génial."
    link_map = [
        {"keyword": "fauteuil releveur", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    _, added = _inject_links_into_body(body, link_map, self_url="/product/abc", max_links=5)
    # Pas d'auto-lien
    assert len(added) == 0


def test_inject_links_case_insensitive():
    body = "Le FAUTEUIL Releveur est populaire."
    link_map = [
        {"keyword": "fauteuil releveur", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    new_body, added = _inject_links_into_body(body, link_map, max_links=5)
    assert len(added) == 1
    # Case original preserved dans le texte du lien
    assert "[FAUTEUIL Releveur](/product/abc)" in new_body


def test_inject_links_respects_word_boundaries():
    # "fauteuil" ne doit PAS matcher "fauteuils" ou "fauteuilier"
    body = "Les fauteuils anciens ne sont pas fauteuil ergonomiques."
    link_map = [
        {"keyword": "fauteuil", "url": "/product/abc", "type": "product", "priority": 8},
    ]
    new_body, added = _inject_links_into_body(body, link_map, max_links=5)
    assert len(added) == 1
    # Doit avoir lié "fauteuil" (standalone) mais pas "fauteuils"
    assert "[fauteuil](/product/abc)" in new_body
    # "fauteuils" toujours intact
    assert "Les fauteuils anciens" in new_body


def test_normalize_keyword():
    assert _normalize_keyword("  Fauteuil  ") == "fauteuil"
    assert _normalize_keyword(None) == ""
    assert _normalize_keyword("ÉQUILIBRE") == "équilibre"


def test_inject_multiple_keywords_stops_at_max():
    body = "Alpha Beta Gamma Delta Epsilon sont cinq lettres grecques."
    link_map = [
        {"keyword": "Alpha", "url": "/a", "type": "blog", "priority": 4},
        {"keyword": "Beta", "url": "/b", "type": "blog", "priority": 4},
        {"keyword": "Gamma", "url": "/c", "type": "blog", "priority": 4},
        {"keyword": "Delta", "url": "/d", "type": "blog", "priority": 4},
        {"keyword": "Epsilon", "url": "/e", "type": "blog", "priority": 4},
    ]
    _, added = _inject_links_into_body(body, link_map, max_links=3)
    assert len(added) == 3
