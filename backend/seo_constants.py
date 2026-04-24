"""
Source de vérité UNIQUE pour la liste des pays/langues supportés SEO/AEO.
Utilisé par :
  - routes/seo.py         (sitemap + hreflang + robots + llms.txt)
  - routes/sites.py       (default seo_countries à la création)
  - routes/sourcing.py    (cible des traductions produit)
  - routes/blog_posts.py  (cible des traductions blog)

Dissociation explicite :
  - `ads_countries` (alias `selected_countries`) : drive Google Ads + budget quotidien.
    Limité par la volonté budgétaire du concepteur (souvent 1-3 pays).
  - `seo_countries` : drive le SEO organique. Par défaut = TOUS les pays supportés.
    Le SEO est "gratuit" : pas de raison de se restreindre.
"""
from typing import Iterable

# 11 pays supportés par la plateforme (sitemap, hreflang, llms.txt, translations)
ALL_SUPPORTED_COUNTRIES: list[str] = [
    "FR", "BE", "LU", "CH", "DE", "AT", "UK", "IE", "NL", "IT", "ES",
]

# Mapping pays → langue principale (celle du contenu servi)
LANG_BY_COUNTRY: dict[str, str] = {
    "FR": "fr", "BE": "fr", "LU": "fr", "CH": "fr",
    "DE": "de", "AT": "de",
    "UK": "en", "IE": "en",
    "NL": "nl",
    "IT": "it",
    "ES": "es",
}

# 6 langues distinctes
ALL_SUPPORTED_LANGS: list[str] = ["fr", "de", "en", "nl", "it", "es"]

# Devise par pays (utile pour JSON-LD Product + Merchant feed)
CURRENCY_BY_COUNTRY: dict[str, str] = {
    "FR": "EUR", "BE": "EUR", "LU": "EUR", "NL": "EUR",
    "DE": "EUR", "AT": "EUR", "IT": "EUR", "ES": "EUR", "IE": "EUR",
    "CH": "CHF",
    "UK": "GBP",
}


def normalize_country(c: str) -> str:
    return (c or "").strip().upper()


def get_seo_countries(site: dict) -> list[str]:
    """Retourne la liste de pays SEO d'un site.

    Priorité :
      1. `site.seo_countries` si explicitement défini (même vide → respecter)
         → utilisé si c'est une liste non-vide
      2. Fallback runtime sur ALL_SUPPORTED_COUNTRIES (couverture maximale par défaut)

    Les anciens sites (avant Chantier 5) n'ont pas `seo_countries` → bénéficient
    automatiquement de la couverture complète sans migration DB.
    """
    raw = site.get("seo_countries")
    if isinstance(raw, list) and raw:
        return [normalize_country(c) for c in raw if c]
    return list(ALL_SUPPORTED_COUNTRIES)


def get_seo_langs(site: dict) -> list[str]:
    """Retourne les langues uniques SEO d'un site (dérivées de seo_countries)."""
    seen: list[str] = []
    for cc in get_seo_countries(site):
        lg = LANG_BY_COUNTRY.get(cc)
        if lg and lg not in seen:
            seen.append(lg)
    return seen or ["fr"]


def get_ads_countries(site: dict) -> list[str]:
    """Pays Google Ads (ceux qu'on cible activement, avec budget). Peut être vide."""
    raw = site.get("selected_countries") or site.get("ads_countries") or []
    return [normalize_country(c) for c in raw if c]


def filter_supported(countries: Iterable[str]) -> list[str]:
    """Filtre une liste de codes pays pour ne garder que les supportés."""
    seen: list[str] = []
    for c in countries or []:
        cc = normalize_country(c)
        if cc in ALL_SUPPORTED_COUNTRIES and cc not in seen:
            seen.append(cc)
    return seen
