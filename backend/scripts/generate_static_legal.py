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

        # Version avec extension .html (toujours servie correctement)
        path_html = OUT / f"{slug}.html"
        path_html.write_text(html, encoding="utf-8")
        written.append(str(path_html.relative_to(ROOT)))

        # Version sans extension (pour /legal/{slug})
        # CRA copie les fichiers tels quels ; serveurs statiques modernes
        # détectent le content-type via le contenu (mais on ajoute un sidecar
        # `_headers` Cloudflare Pages plus bas pour forcer text/html).
        path_noext = OUT / slug
        path_noext.write_text(html, encoding="utf-8")
        written.append(str(path_noext.relative_to(ROOT)))

    # Sidecar Cloudflare Pages : force le Content-Type sur les versions sans
    # extension. Ignoré silencieusement par les autres hébergeurs.
    headers_path = ROOT / "frontend" / "public" / "_headers"
    headers_block = (
        "# Force text/html pour les pages légales sans extension\n"
        + "\n".join(
            f"/legal/{slug}\n  Content-Type: text/html; charset=utf-8\n"
            for slug, _, _ in PAGES
        )
    )
    # On préserve le contenu existant si présent (autres règles).
    existing = headers_path.read_text(encoding="utf-8") if headers_path.exists() else ""
    marker = "# === ALTIARO LEGAL STATIC ==="
    if marker in existing:
        # Remplace la section existante
        before = existing.split(marker)[0].rstrip() + "\n\n"
        after_parts = existing.split(marker, 1)[1].split("# === END ALTIARO LEGAL STATIC ===", 1)
        after = after_parts[1] if len(after_parts) > 1 else ""
        new_content = (
            before
            + marker
            + "\n"
            + headers_block
            + "\n# === END ALTIARO LEGAL STATIC ===\n"
            + after
        )
    else:
        new_content = (
            (existing.rstrip() + "\n\n" if existing else "")
            + marker
            + "\n"
            + headers_block
            + "\n# === END ALTIARO LEGAL STATIC ===\n"
        )
    headers_path.write_text(new_content, encoding="utf-8")
    written.append(str(headers_path.relative_to(ROOT)))

    print("✅ Fichiers HTML statiques générés :")
    for w in written:
        print(f"  • {w}")


if __name__ == "__main__":
    main()
