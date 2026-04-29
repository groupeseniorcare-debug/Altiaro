"""
Générateur de fichiers HTML statiques pour les pages légales Altiaro.

Usage : `python backend/scripts/generate_static_legal.py`

Sortie :
  frontend/public/legal/retours.html
  frontend/public/legal/livraison.html
  frontend/public/legal/cgv.html
  frontend/public/legal/confidentialite.html
  frontend/public/legal/mentions.html
  + version SANS extension (pour matcher /legal/retours sans .html)
    frontend/public/legal/retours
    ...

Ces fichiers sont copiés à la racine du build CRA et servis en HTML statique.
Avantage : aucun routing dynamique requis, tout hébergeur (Cloudflare Pages,
nginx, Netlify, FastAPI static, etc.) sert correctement le HTML.

⚠️ À relancer manuellement à chaque mise à jour du contenu légal.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ajoute backend au sys.path pour importer les builders
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from routes.public_legal import (  # noqa: E402
    _render,
    _retours_body,
    _livraison_body,
    _cgv_body,
    _confidentialite_body,
    _mentions_body,
)

OUT = ROOT / "frontend" / "public" / "legal"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("retours",          "Politique de retour",            _retours_body),
    ("livraison",        "Politique de livraison",         _livraison_body),
    ("cgv",              "Conditions générales de vente",  _cgv_body),
    ("confidentialite",  "Politique de confidentialité",   _confidentialite_body),
    ("mentions",         "Mentions légales",               _mentions_body),
]


def _adjust_links_for_static(html: str) -> str:
    """Sur les fichiers statiques on a besoin que les liens entre pages
    fonctionnent à la fois pour `/legal/cgv` (sans extension) et pour
    `/legal/cgv.html`. On choisit la version sans extension partout
    (couvre les 2 cas via les fichiers générés des 2 façons).
    """
    # Le builder utilise déjà des hrefs `/legal/{slug}` sans extension. Rien
    # à faire pour le moment. Si on voulait pointer sur les .html on
    # remplacerait ici.
    return html


def main() -> None:
    written: list[str] = []
    for slug, title, builder in PAGES:
        # Le _render renvoie un HTMLResponse FastAPI. On accède au body brut.
        response = _render(
            title=title,
            eyebrow="Altiaro · Légal",
            current_slug=slug,
            body_html=builder(),
        )
        # Selon la version FastAPI, le body est en `body` (bytes) ou `_body`.
        raw = getattr(response, "body", None) or getattr(response, "_body", None)
        if raw is None:
            raise RuntimeError(f"Impossible d'extraire le body HTML pour {slug}")
        html = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        html = _adjust_links_for_static(html)

        # Version avec extension .html (toujours servie en text/html par
        # webpack-dev-server, nginx, Cloudflare Pages, FastAPI static, etc.).
        path_html = OUT / f"{slug}.html"
        path_html.write_text(html, encoding="utf-8")
        written.append(str(path_html.relative_to(ROOT)))

        # 2026-04-29 — On NE génère PLUS la version sans extension : sur
        # webpack-dev-server elle sortait en `application/octet-stream`
        # (problème pour Google MCA). À la place :
        #   • prod Cloudflare Pages : `_redirects` rewrite `/legal/{slug}`
        #     → `/legal/{slug}.html` (200, URL inchangée).
        #   • preview : le SPA React (App.js) a les routes /legal/* via
        #     les composants PlatformLegal* → 200 text/html garanti.
        #   • prod FastAPI native : `routes/public_legal.py` répond directement.

    # 2026-04-29 — Plus besoin de sidecar `_headers` pour les versions sans
    # extension : on ne les génère plus. Le rewrite Cloudflare Pages se fait
    # dans `frontend/public/_redirects` (géré manuellement).

    print("✅ Fichiers HTML statiques générés :")
    for w in written:
        print(f"  • {w}")


if __name__ == "__main__":
    main()
