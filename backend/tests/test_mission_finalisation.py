"""Smoke tests pour la mission Finalisation 2026-04-28.

Vérifie qu'aucun import n'est cassé sur les nouveaux modules
+ que le service `seo_jsonld` produit du JSON-LD valide.
"""
import sys
from pathlib import Path

# Ajoute /app/backend au path pour permettre les imports relatifs
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_import_phase_finalisation():
    """Tous les modules de la mission s'importent sans crash."""
    from routes import blog_queue, seo_factory, site_qa, geo  # noqa: F401
    from services import blog_worker, site_qa_checklist, seo_jsonld  # noqa: F401
    import geo_mapping  # noqa: F401


def test_seo_jsonld_organization():
    """Le builder Organization renvoie un objet schema.org valide."""
    from services import seo_jsonld
    site = {
        "id": "test",
        "public_url": "https://example.com",
        "design": {"brand": {"name": "Altea", "logo_url": "https://x/logo.png"}},
    }
    out = seo_jsonld.organization(site)
    assert out["@context"] == "https://schema.org"
    assert out["@type"] == "Organization"
    assert out["name"] == "Altea"
    assert out["logo"] == "https://x/logo.png"


def test_seo_jsonld_product_with_currency():
    """Product builder honore la devise demandée (1:1 EUR/GBP)."""
    from services import seo_jsonld
    site = {"public_url": "https://example.com", "design": {"brand": {"name": "Altea"}}}
    product = {
        "id": "p1", "name": {"fr": "Fauteuil"}, "description": {"fr": "..."},
        "price": 199, "images": ["https://x/p.jpg"],
    }
    out = seo_jsonld.product(product, site, "fr", currency="GBP")
    assert out["offers"]["priceCurrency"] == "GBP"
    assert out["offers"]["price"] == "199"
    out2 = seo_jsonld.product(product, site, "fr", currency="EUR")
    assert out2["offers"]["priceCurrency"] == "EUR"
    # Parité 1:1 : même nombre, devise différente
    assert out["offers"]["price"] == out2["offers"]["price"]


def test_seo_jsonld_hreflang_alternates_x_default():
    """Hreflang inclut bien `x-default` pointant sur la langue par défaut."""
    from services import seo_jsonld
    alts = seo_jsonld.hreflang_alternates("https://x.com", "/p/123", ["fr", "en", "de"], default="fr")
    codes = [a["hreflang"] for a in alts]
    assert "x-default" in codes
    xd = next(a for a in alts if a["hreflang"] == "x-default")
    assert xd["href"] == "https://x.com/fr/p/123"


def test_geo_mapping_gb_returns_gbp():
    """Phase D' : pays GB → devise GBP, langue en, symbole £."""
    import geo_mapping
    out = geo_mapping.detect("GB")
    assert out["country"] == "GB"
    assert out["language"] == "en"
    assert out["currency"] == "GBP"
    assert out["currency_symbol"] == "£"


def test_geo_mapping_default_eur():
    """Phase D' : pays inconnu → fallback FR/EUR/€."""
    import geo_mapping
    out = geo_mapping.detect(None)
    assert out["currency"] == "EUR"
    assert out["currency_symbol"] == "€"


def test_purge_material_canonical_detection():
    """Phase E' : la regex repère bien microsuede/PU dans une description i18n."""
    from scripts.purge_material_consistency import _canonical_for_product
    p = {
        "name": {"fr": "Fauteuil microsuède"},
        "description": {"fr": "Tissu microsuède haut de gamme.", "en": "Microsuede fabric."},
        "tags": ["microsuede", "premium"],
    }
    canonical, all_detected, source = _canonical_for_product(p)
    assert canonical == "microsuede"
    assert "microsuede" in all_detected


def test_purge_material_contradiction_detected():
    """Phase E' : si description mentionne 2 matériaux différents, c'est flaggé."""
    from scripts.purge_material_consistency import _canonical_for_product
    p = {
        "name": {"fr": "Fauteuil microsuède"},
        "description": {"fr": "Tissu microsuède avec armature en simili-cuir PU pour les accoudoirs."},
    }
    canonical, all_detected, source = _canonical_for_product(p)
    assert canonical == "microsuede"
    assert len(all_detected) >= 2
