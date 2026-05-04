"""Bing Webmaster Tools — ownership verification.

Sert `/BingSiteAuth.xml` depuis FastAPI (preview + prod Emergent native
deploy). Pair avec `frontend/public/BingSiteAuth.xml` (CRA statique en
preview dev, et Approximated en prod custom domain).

Le backend route garantit un 200 même si le build React n'a pas encore
intégré le fichier static (ex. preview Emergent sur `/` servi par FastAPI
en native deploy).

IMPORTANT : ce router est monté DIRECTEMENT DANS `app` sans préfixe /api.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(include_in_schema=False)

BING_AUTH_CODE = "A5B253755223EA9AF2CC5650871274E9"

BING_AUTH_XML = (
    '<?xml version="1.0"?>\n'
    '<users>\n'
    f'\t<user>{BING_AUTH_CODE}</user>\n'
    '</users>\n'
)


@router.get("/BingSiteAuth.xml")
async def bing_site_auth() -> Response:
    """Return the Bing Webmaster Tools verification file."""
    return Response(
        content=BING_AUTH_XML,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Robots-Tag": "noindex",
        },
    )
