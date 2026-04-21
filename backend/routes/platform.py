"""Public routes for Altiaro platform (landing, legal pages).
No auth required — crawlable by Google, Mollie reviewers, etc."""

from fastapi import APIRouter, HTTPException
from altiaro_legal import get_legal_page
from platform_policy import get_platform_policy

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/legal/{slug}")
async def public_legal_page(slug: str):
    """Return the platform-level legal page content as JSON.
    Available slugs: mentions-legales, cgu, confidentialite, cookies."""
    page = get_legal_page(slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page non trouvée")
    return page


@router.get("/info")
async def platform_info():
    """Public meta about the Altiaro platform — consumed by the landing page."""
    return {
        "name": "Altiaro",
        "legal_name": "Robin Zuchiatti (entrepreneur individuel)",
        "tagline": "La plateforme e-commerce des partenariats éclairés.",
        "value_prop": (
            "Altiaro accompagne les entrepreneurs qui lancent des marques "
            "e-commerce premium dans la Silver Economy — 50% de la marge brute "
            "partagée équitablement, sites générés par IA, scan de niches "
            "multi-marchés et cockpit de pilotage complet."
        ),
        "email": "contact@altiaro.com",
        "website": "https://altiaro.com",
        "founded": 2026,
        "markets": ["FR", "DE", "BL", "NL", "CH", "UK"],
    }


@router.get("/policy")
async def platform_policy_admin():
    """Politique plateforme Altiaro exposée aux Concepteurs (lecture seule)."""
    return get_platform_policy()


@router.get("/public/policy")
async def platform_policy_public():
    """Subset de la politique exposé sur tous les storefronts (FAQ, checkout, footer)."""
    p = get_platform_policy()
    return {
        "shipping": {
            "label": p["shipping"]["label"],
            "covered_countries": p["shipping"]["covered_countries"],
            "delivery_estimate": p["shipping"]["delivery_estimate"],
        },
        "payment": {
            "provider": p["payment"]["provider"],
            "methods_enabled": p["payment"]["methods_enabled"],
        },
        "returns": {"label": p["returns"]["label"]},
        "warranty": {"label": p["warranty"]["label"], "years": p["warranty"]["years"]},
        "customer_service": p["customer_service"],
    }

