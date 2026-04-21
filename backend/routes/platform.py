"""Public routes for Altiaro platform (landing, legal pages).
No auth required — crawlable by Google, Mollie reviewers, etc."""

from fastapi import APIRouter, HTTPException
from altiaro_legal import get_legal_page

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
        "markets": ["FR", "DE", "IT", "BE", "CH", "NL"],
    }
