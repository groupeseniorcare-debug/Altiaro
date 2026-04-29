"""
Générateur de fichiers HTML statiques pour les pages légales Altiaro.

Usage : `python backend/scripts/generate_static_legal.py`

Sortie (sous-dossiers `index.html`, structure attendue par Cloudflare Pages
qui sert `/legal/foo` via `/legal/foo/index.html` AVANT de tomber sur le
fallback SPA `/index.html`) :

  frontend/public/legal/index.html                    (hub d'accueil légal)
  frontend/public/legal/retours/index.html
  frontend/public/legal/livraison/index.html
  frontend/public/legal/cgv/index.html
  frontend/public/legal/confidentialite/index.html
  frontend/public/legal/mentions/index.html

Plus de doublons `.html` à la racine de `legal/` : c'est cette structure
sous-dossier + `index.html` qui garantit que Cloudflare Pages les sert
côté prod altiaro.com avant tout fallback SPA.

⚠️ À relancer manuellement à chaque mise à jour du contenu légal.
"""
from __future__ import annotations

import sys
from datetime import date
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


def _extract_html(response) -> str:
    raw = getattr(response, "body", None) or getattr(response, "_body", None)
    if raw is None:
        raise RuntimeError("Impossible d'extraire le body HTML")
    return raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)


def _hub_body() -> str:
    """Page d'accueil `/legal/` listant les 5 sous-pages."""
    cards = [
        ("mentions", "Mentions légales",
         "Identité de l'éditeur Altiaro, hébergeur, contact DPO, juridiction compétente."),
        ("cgv", "Conditions générales de vente",
         "Cadre contractuel des sites e-commerce générés via la plateforme Altiaro : commande, livraison, paiement, droit de rétractation, garanties légales, médiation."),
        ("confidentialite", "Politique de confidentialité",
         "Données collectées, finalités, base légale RGPD, durées de conservation, sous-traitants, droits d'accès, rectification, opposition, suppression."),
        ("livraison", "Politique de livraison",
         "Zones desservies, délais indicatifs, frais, suivi colis, retards, livraisons partielles."),
        ("retours", "Politique de retour",
         "Délai de rétractation L221-18, état du produit, remboursement, frais de retour, contact service client."),
    ]
    items = "\n".join(
        f'''<a class="legal-card" href="/legal/{slug}">
              <h2>{title}</h2>
              <p>{desc}</p>
              <span class="cta">Lire la page →</span>
            </a>'''
        for slug, title, desc in cards
    )
    return f'''
<section class="legal-hub">
  <p class="hub-intro">Cet espace regroupe les pages légales encadrant l'usage de la plateforme Altiaro et des sites e-commerce qui en sont issus. Conformes au droit français et au RGPD, mises à jour le {date.today().strftime("%d/%m/%Y")}.</p>
  <div class="hub-grid">
    {items}
  </div>
</section>
<style>
.legal-hub {{ padding: 8px 0 32px; }}
.hub-intro {{ font-size: 16px; color: #4A4A4A; max-width: 720px; margin: 0 0 32px; }}
.hub-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }}
.legal-card {{
  display: block;
  text-decoration: none;
  color: inherit;
  background: #FDFCF9;
  border: 1px solid #E8E2D5;
  border-radius: 6px;
  padding: 24px 22px;
  transition: border-color .2s ease, transform .2s ease;
}}
.legal-card:hover {{ border-color: #0F6E4D; transform: translateY(-2px); }}
.legal-card h2 {{
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 22px; font-weight: 500;
  margin: 0 0 10px; color: #1A1A1A;
}}
.legal-card p {{ font-size: 14px; line-height: 1.6; margin: 0 0 14px; color: #555; }}
.legal-card .cta {{ font-size: 13px; font-weight: 600; color: #0F6E4D; }}
</style>
'''


def main() -> None:
    written: list[str] = []

    # 1) Sous-pages : `legal/{slug}/index.html`
    for slug, title, builder in PAGES:
        response = _render(
            title=title,
            eyebrow="Altiaro · Légal",
            current_slug=slug,
            body_html=builder(),
        )
        html = _extract_html(response)

        sub_dir = OUT / slug
        sub_dir.mkdir(parents=True, exist_ok=True)
        path_index = sub_dir / "index.html"
        path_index.write_text(html, encoding="utf-8")
        written.append(str(path_index.relative_to(ROOT)))

    # 2) Hub : `legal/index.html` listant les 5 pages
    hub_response = _render(
        title="Pages légales",
        eyebrow="Altiaro · Légal",
        current_slug="__hub__",  # aucun lien sidebar actif
        body_html=_hub_body(),
    )
    hub_html = _extract_html(hub_response)
    hub_path = OUT / "index.html"
    hub_path.write_text(hub_html, encoding="utf-8")
    written.append(str(hub_path.relative_to(ROOT)))

    # 3) Nettoyage des anciens fichiers `.html` à la racine de `legal/`
    legacy_files = [
        OUT / f"{slug}.html" for slug, _, _ in PAGES
    ]
    removed: list[str] = []
    for fp in legacy_files:
        if fp.exists():
            fp.unlink()
            removed.append(str(fp.relative_to(ROOT)))

    print("✅ Fichiers HTML statiques générés :")
    for w in written:
        print(f"  • {w}")
    if removed:
        print("🗑️  Anciens fichiers supprimés :")
        for r in removed:
            print(f"  • {r}")


if __name__ == "__main__":
    main()
