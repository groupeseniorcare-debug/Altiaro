"""
Journey gating — Chantier 1 (Altiaro).

Source de vérité UNIQUE pour le statut des 9 étapes du cockpit concepteur.
Pas de validation manuelle : chaque étape est considérée comme complétée
uniquement si les données correspondantes existent en DB.

Règles de completion (selon brief user) :
  1. pricing   — ≥1 QuickScan généré pour ce site avec verdict GO ou CAUTION
  2. import    — ≥5 produits dans db.products pour ce site
                 + couverture 100% des pays cibles (sinon "soft_blocked" avec override)
  3. upsells   — ≥3 produits typés upsell/accessoire
  4. forecast  — financial_forecast généré
  5. branding  — design.published == true
  6. pages     — pages légales + about/faq/contact remplies
  7. content   — ≥1 pillar + ≥3 satellites blog
  8. seo       — seo_score ≥ 70
  9. qa        — qa_audit ready_for_submission == true (envoyé à l'admin)

Pattern : un endpoint `GET /api/sites/{site_id}/steps/status` qui calcule
tout à chaque appel. Pas de cache. Pas de flag manuel en DB.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from deps import db, get_current_user, _check_site_access

logger = logging.getLogger(__name__)
router = APIRouter()

# Ordre canonique des 10 étapes (refonte 2026-04-29 :
# inversion 7/8 → `content` AVANT `translate` car on génère blog + landings +
# FAQ en langue primaire d'abord, puis on traduit TOUT d'un coup vers les
# 5 langues supplémentaires. Plus besoin d'un soft_unlocked : gating strict.)
STEP_ORDER = [
    "pricing", "import", "upsells", "forecast", "branding",
    "domain", "content", "translate", "seo", "qa",
]

STEP_LABELS = {
    "pricing":   "Analyse concurrence & pricing",
    "import":    "Import du catalogue",
    "upsells":   "Upsells & accessoires",
    "forecast":  "Étude financière 30j",
    "branding":  "Identité & branding",
    "domain":    "Nom de domaine",
    "content":   "Contenu SEO automatisé",
    "translate": "Traduction multilingue",
    "seo":       "Score SEO & connexions Google",
    "qa":        "QA & mise en ligne",
}

# Sous-titres explicatifs (utilisés sur les pages d'étape pour clarté UX)
STEP_SUBTITLES = {
    "pricing":   "Comparatif concurrentiel et fourchette de prix recommandée",
    "import":    "Importer 5+ produits depuis votre source",
    "upsells":   "Suggérer des accessoires pour augmenter le panier moyen",
    "forecast":  "Prévisionnel financier sur 30 jours",
    "branding":  "Logo, palette, ton de marque",
    "domain":    "Domaine personnalisé + DNS automatique",
    "content":   "Blog, pages d'atterrissage et FAQ — en langue primaire",
    "translate": "Tout votre site en 5 langues supplémentaires",
    "seo":       "Score SEO et activation du suivi Google",
    "qa":        "Vérification finale avant mise en ligne publique",
}

# ────────── Helpers de check par étape ────────── #

async def _check_pricing(site_id: str, site: dict) -> dict:
    """Étape 1 complétée dès qu'une analyse a été EXÉCUTÉE pour ce site.

    Deux sources acceptées (le cockpit utilise la 1ère, QuickScan standalone la 2nde) :
      (A) `site.design.pricing_analysis.generated_at` renseigné (endpoint
          `POST /sites/{id}/pricing-analysis`)
      (B) ≥1 document dans `db.quick_scans` avec ce `site_id` (endpoint
          `POST /quick-scan` ou `/quick-scan/multi`)

    Aucun seuil de verdict : le concepteur choisit lui-même son angle même si
    tous les marchés ressortent NO_GO (il prendra ses risques). Le message
    détaille toutefois le verdict par marché pour éclairer sa décision.
    """
    # Source A : analyse Claude "cockpit" persistée dans le site
    pa = (site.get("design") or {}).get("pricing_analysis") or {}
    pa_generated_at = pa.get("generated_at")

    # Source B : quick_scans rattachés au site
    scans = await db.quick_scans.find(
        {"site_id": site_id},
        {"_id": 0, "verdict": 1, "country": 1},
    ).to_list(length=500)
    count_total = len(scans)
    from collections import Counter
    verdict_counts = Counter((s.get("verdict") or "").upper() for s in scans)
    count_go = verdict_counts.get("GO", 0)
    count_caution = verdict_counts.get("GO_WITH_RESERVE", 0) + verdict_counts.get("CAUTION", 0)
    count_nogo = verdict_counts.get("NO_GO", 0)

    completed = bool(pa_generated_at) or (count_total >= 1)

    # Message humain
    if pa_generated_at and count_total == 0:
        niche = pa.get("niche") or "niche"
        n_competitors = len(pa.get("competitors") or [])
        n_ranges = len(pa.get("recommended_ranges") or [])
        reason = (
            f"Analyse pricing effectuée ({n_competitors} concurrents, "
            f"{n_ranges} fourchettes) · {niche}"
        )
    elif count_total >= 1:
        bits = []
        if count_go:      bits.append(f"{count_go} GO")
        if count_caution: bits.append(f"{count_caution} CAUTION")
        if count_nogo:    bits.append(f"{count_nogo} NO_GO")
        summary = " · ".join(bits) if bits else f"{count_total} scan(s)"
        if pa_generated_at:
            reason = f"Analyse effectuée ✓ — {summary}"
        elif count_go + count_caution == 0:
            reason = (
                f"Analyse effectuée ✓ — {summary} · "
                f"niche à risque, tu peux avancer mais vérifie ton angle"
            )
        else:
            reason = f"Analyse effectuée ✓ — {summary}"
    else:
        reason = "Lance l'analyse pricing IA (ou un QuickScan) pour débloquer la suite"

    return {
        "key": "pricing",
        "label": STEP_LABELS["pricing"],
        "completed": completed,
        "reason": reason,
        "counters": {
            "pricing_analysis_done": bool(pa_generated_at),
            "total_scans": count_total,
            "go": count_go,
            "caution": count_caution,
            "nogo": count_nogo,
        },
    }


async def _check_import(site_id: str, site: dict) -> dict:
    """≥5 produits dans db.products pour ce site + couverture pays."""
    product_count = await db.products.count_documents({"site_id": site_id})
    min_products = 5

    # Couverture pays : chaque pays cible du site doit être couvert
    # par au moins 1 produit livrable (champ future : product.shipping_countries[]).
    target_countries = site.get("countries") or []
    if not target_countries and site.get("country"):
        target_countries = [site["country"]]

    coverage: dict = {}
    missing: list = []
    if target_countries:
        # Récupère tous les produits pour calculer leur couverture agrégée.
        async for p in db.products.find(
            {"site_id": site_id},
            {"_id": 0, "id": 1, "shipping_countries": 1},
        ):
            for cc in (p.get("shipping_countries") or []):
                coverage[cc] = coverage.get(cc, 0) + 1
        for cc in target_countries:
            if coverage.get(cc, 0) == 0:
                missing.append(cc)

    has_enough_products = product_count >= min_products
    has_full_coverage = len(missing) == 0
    # Override : le concepteur peut forcer le passage même avec couverture
    # incomplète (option explicite persistée dans site.import_force_partial).
    force_partial = bool(site.get("import_force_partial"))

    if not has_enough_products:
        completed = False
        reason = f"{product_count}/{min_products} produits importés"
    elif not has_full_coverage and not force_partial:
        completed = False
        reason = (
            f"5+ produits OK, mais {len(missing)} pays sans couverture : "
            f"{', '.join(missing)} · ajoute un produit livrable OU confirme "
            f"le passage partiel"
        )
    else:
        completed = True
        if force_partial and not has_full_coverage:
            reason = f"{product_count} produits · couverture partielle assumée (manque : {', '.join(missing)})"
        else:
            reason = f"{product_count} produits · couverture 100% sur {len(target_countries)} pays"

    return {
        "key": "import",
        "label": STEP_LABELS["import"],
        "completed": completed,
        "reason": reason,
        "counters": {
            "product_count": product_count,
            "min_required": min_products,
            "target_countries": target_countries,
            "country_coverage": coverage,
            "missing_countries": missing,
            "force_partial": force_partial,
        },
    }


async def _check_upsells(site_id: str, site: dict) -> dict:
    """≥3 produits typés 'upsell' ou 'accessory'."""
    count = await db.products.count_documents({
        "site_id": site_id,
        "$or": [
            {"type": {"$in": ["upsell", "accessory", "addon"]}},
            {"is_upsell": True},
            {"role": {"$in": ["upsell", "accessory"]}},
        ],
    })
    min_upsells = 3
    completed = count >= min_upsells
    reason = (
        f"{count} upsell(s)/accessoire(s)"
        if completed
        else f"{count}/{min_upsells} upsells nécessaires · tagge 3 produits comme upsell/accessoire"
    )
    return {
        "key": "upsells",
        "label": STEP_LABELS["upsells"],
        "completed": completed,
        "reason": reason,
        "counters": {"upsell_count": count, "min_required": min_upsells},
    }


async def _check_forecast(site_id: str, site: dict) -> dict:
    """Forecast financier généré."""
    fc = (site.get("design") or {}).get("financial_forecast") or {}
    generated_at = fc.get("generated_at")
    completed = bool(generated_at)
    reason = (
        f"Prévisionnel généré le {generated_at[:10]}"
        if completed
        else "Lance le calcul du prévisionnel 30j"
    )
    return {
        "key": "forecast",
        "label": STEP_LABELS["forecast"],
        "completed": completed,
        "reason": reason,
    }


async def _check_branding(site_id: str, site: dict) -> dict:
    """design.published == true."""
    design = site.get("design") or {}
    published = bool(design.get("published"))
    has_brand = bool((design.get("brand") or {}).get("name"))
    has_logo = bool((design.get("brand") or {}).get("logo_url"))
    completed = published and has_brand
    reason = (
        "Design publié · branding complet" if completed
        else "Publie le design avec un nom + logo pour valider"
    )
    return {
        "key": "branding",
        "label": STEP_LABELS["branding"],
        "completed": completed,
        "reason": reason,
        "counters": {"published": published, "has_brand": has_brand, "has_logo": has_logo},
    }


async def _check_domain(site_id: str, site: dict) -> dict:
    """Lot D — Étape 6 Domaine.

    Considérée complète dès que le site a un `custom_domain` peuplé OU s'il
    a explicitement choisi de continuer avec le sous-domaine plateforme
    (`domain_skipped: true`) — étape OPTIONNELLE.
    """
    custom_domain = site.get("custom_domain") or site.get("domain")
    domain_skipped = bool(site.get("domain_skipped"))
    purchased_at = site.get("domain_purchased_at")
    has_domain = bool(custom_domain)
    completed = has_domain or domain_skipped
    if has_domain:
        reason = f"Domaine attaché : {custom_domain}"
    elif domain_skipped:
        reason = "Sous-domaine plateforme conservé (étape optionnelle skippée)"
    else:
        reason = "Choisis un domaine ou continue avec le sous-domaine plateforme."
    return {
        "key": "domain",
        "label": STEP_LABELS["domain"],
        "completed": completed,
        "reason": reason,
        "optional": True,  # Étape optionnelle — n'empêche pas la soumission QA
        "counters": {
            "custom_domain": custom_domain,
            "skipped": domain_skipped,
            "purchased_at": purchased_at,
        },
    }


def _page_has_content(page: dict) -> bool:
    """Helper conservé pour usage interne (analyse de pages CMS).
    Note 2026-05-04 : l'étape Cockpit `pages` a été retirée de STEP_ORDER ;
    cette fonction reste utile pour validation.py et autres consommateurs."""
    if not page:
        return False
    body = page.get("body")
    if isinstance(body, dict):
        return bool((body.get("content") or "").strip())
    if isinstance(body, str):
        return bool(body.strip())
    return False


async def _check_translate(site_id: str, site: dict) -> dict:
    """Étape 7 — la traduction est validée dès qu'au moins 2 langues
    sont activées (le site source + 1 traduction). Pour passer en go-live
    on recommandera 4-6 langues, mais le cockpit débloque la suite dès 2.
    """
    available = site.get("available_langs") or []
    primary = site.get("primary_lang") or (available[0] if available else "fr")
    extra = [lg for lg in available if lg != primary]
    completed = len(available) >= 2
    reason = (
        f"{len(available)} langues actives · principale : {primary} · +{len(extra)} traduction(s)"
        if completed
        else "Lance la traduction vers au moins 1 langue cible"
    )
    return {
        "key": "translate",
        "label": STEP_LABELS["translate"],
        "completed": completed,
        "reason": reason,
        "counters": {
            "available": available,
            "primary": primary,
            "extras_count": len(extra),
        },
    }


async def _check_content(site_id: str, site: dict) -> dict:
    """≥1 pillar + ≥3 satellites dans blog_posts (collection ou array site).

    2026-04-29 (refonte UX strict) : on agrège la collection `db.blog_posts`
    avec l'array historique `site.design.blog_posts`. Plus de `soft_unlocked` —
    l'étape est `completed=True` UNIQUEMENT si on a réellement 1 pilier + 3
    satellites publiés. Le concepteur peut sinon valider manuellement via
    "Valider et passer à l'étape suivante".
    """
    embedded = (site.get("design") or {}).get("blog_posts") or []
    blog_jobs_count = await db.blog_jobs.count_documents({"site_id": site_id})
    blog_posts_count = await db.blog_posts.count_documents({"site_id": site_id})
    automation_on = bool(((site.get("automation") or {}).get("content_enabled")))

    # Total publié = collection + embedded (dédoublonné par slug)
    seen_slugs: set[str] = set()
    pillars = 0
    satellites = 0
    cursor = db.blog_posts.find(
        {"site_id": site_id},
        {"_id": 0, "slug": 1, "type": 1, "role": 1},
    )
    async for p in cursor:
        slug = p.get("slug")
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        kind = p.get("type") or p.get("role")
        if kind == "pillar":
            pillars += 1
        else:
            satellites += 1
    for p in embedded:
        slug = p.get("slug")
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        kind = p.get("type") or p.get("role")
        if kind == "pillar":
            pillars += 1
        else:
            satellites += 1
    # Si total >= 1 mais aucun typage, considère le 1er comme pillar
    if pillars == 0 and (pillars + satellites) >= 1:
        pillars = 1
        satellites = max(0, (pillars + satellites) - 1)

    pillar_ok = pillars >= 1
    satellite_ok = satellites >= 3
    completed = pillar_ok and satellite_ok

    if completed:
        reason = f"{pillars} pillar(s) + {satellites} satellite(s) publié(s)"
    elif blog_jobs_count or blog_posts_count or automation_on:
        reason = (
            f"Génération en cours · {blog_jobs_count} job(s) en file, "
            f"{blog_posts_count} article(s) publié(s) — automatisation "
            f"{'active' if automation_on else 'inactive'}"
        )
    else:
        reason = "Lancez la génération de vos 3 premiers articles SEO"
    return {
        "key": "content",
        "label": STEP_LABELS["content"],
        "completed": completed,
        "reason": reason,
        "counters": {
            "pillars": pillars,
            "satellites": satellites,
            "blog_jobs_count": blog_jobs_count,
            "blog_posts_count": blog_posts_count,
            "automation_on": automation_on,
        },
    }


async def _check_seo(site_id: str, site: dict) -> dict:
    """SEO studio rempli (seo_score ≥ 70).

    2026-04-29 (refonte UX strict) : plus de soft_unlocked. L'étape est
    completed UNIQUEMENT si score >= 70. Sinon le concepteur peut valider
    manuellement via "Valider et passer à l'étape suivante" (override).
    """
    score = int((site.get("design") or {}).get("seo_score") or 0)
    threshold = 70
    completed = score >= threshold

    automation_seo = bool(((site.get("automation") or {}).get("seo_enabled")))
    landing_count = await db.landing_pages.count_documents({"site_id": site_id})
    keyword_universe_count = await db.keyword_universe.count_documents({"site_id": site_id})

    if completed:
        reason = f"Score SEO {score}/100 (seuil {threshold})"
    elif score > 0:
        reason = f"Score SEO {score}/100 — continuez d'enrichir pour atteindre {threshold}"
    elif automation_seo or landing_count or keyword_universe_count:
        reason = (
            f"SEO auto activé · {landing_count} landing(s), "
            f"{keyword_universe_count} mot(s)-clé(s) découvert(s)"
        )
    else:
        reason = "Lancez la santé SEO automatique (long-tail + landings)"
    return {
        "key": "seo",
        "label": STEP_LABELS["seo"],
        "completed": completed,
        "reason": reason,
        "counters": {
            "score": score,
            "threshold": threshold,
            "automation_seo": automation_seo,
            "landing_count": landing_count,
            "keyword_universe_count": keyword_universe_count,
        },
    }


async def _check_qa(site_id: str, site: dict) -> dict:
    """Status = approved (validé admin) OU soumis à review avec score OK."""
    status = (site.get("status") or "").lower()
    qa = site.get("qa_audit") or {}
    # 'approved' côté admin = étape terminale
    if status in ("approved", "published", "live"):
        return {
            "key": "qa",
            "label": STEP_LABELS["qa"],
            "completed": True,
            "reason": f"Site {status} par l'admin",
        }
    if status == "pending_review":
        return {
            "key": "qa",
            "label": STEP_LABELS["qa"],
            "completed": False,
            "reason": "En attente de validation admin",
        }
    if qa.get("ready_for_submission"):
        return {
            "key": "qa",
            "label": STEP_LABELS["qa"],
            "completed": False,
            "reason": f"QA score {qa.get('score', 0)}/100 · soumets à l'admin",
        }
    return {
        "key": "qa",
        "label": STEP_LABELS["qa"],
        "completed": False,
        "reason": "Lance le QA automatique pour finaliser",
    }


_CHECKERS = {
    "pricing":   _check_pricing,
    "import":    _check_import,
    "upsells":   _check_upsells,
    "forecast":  _check_forecast,
    "branding":  _check_branding,
    "domain":    _check_domain,        # Lot D — étape 6 (optional, skippable)
    "translate": _check_translate,     # Mission Finalisation — étape 8
    "content":   _check_content,       # étape 7
    "seo":       _check_seo,
    "qa":        _check_qa,
}


async def compute_step_statuses(site_id: str) -> list[dict]:
    """Calcule le statut des 10 étapes pour un site avec **gating en cascade STRICT**.

    Règle unique (2026-04-30) :
      Une étape N est débloquée UNIQUEMENT si l'étape N-1 est `completed`.
      Si l'étape N-1 n'est pas completed, alors N, N+1, …, 10 sont TOUTES
      `locked`, peu importe leurs signaux auto (domain, translate, etc.).

    Une étape est completed si :
      - `manual_step_overrides[key] == True` (cliqué "Valider et passer à l'étape suivante"), OU
      - ses checks data automatiques passent (`completed=True` retourné par le checker),
      MAIS en plus `blocked_by_previous=False` (chaîne intacte).

    Plus de `soft_unlocked`, plus d'exception `optional` : la chaîne est stricte.
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    statuses: list[dict] = []
    chain_broken = False  # dès qu'une étape n'est pas completed → tout ce qui suit est locked
    manual_overrides = await _load_manual_step_overrides(site_id)

    for key in STEP_ORDER:
        checker = _CHECKERS[key]
        s = await checker(site_id, site)
        s["order"] = STEP_ORDER.index(key) + 1
        s.pop("soft_unlocked", None)  # plus de notion floue

        # 1) Chain broken : cette étape et toutes les suivantes sont locked.
        #    On force `completed=False` et `is_clickable=False` pour éviter que
        #    les signaux auto (ex: domaine déjà créé) apparaissent comme
        #    "auto-validées" avant que les étapes précédentes soient faites.
        if chain_broken:
            s["completed"] = False
            s["manual_validated"] = False
            s["auto_validated"] = False
            s["blocked_by_previous"] = True
            s["is_clickable"] = False
            s["status"] = "locked"
            statuses.append(s)
            continue

        # 2) Chaîne intacte à ce stade.
        is_manual = manual_overrides.get(key) is True
        auto_completed = bool(s.get("completed"))
        is_completed = is_manual or auto_completed

        s["completed"] = is_completed
        s["manual_validated"] = is_manual
        s["auto_validated"] = auto_completed and not is_manual
        s["blocked_by_previous"] = False
        s["is_clickable"] = True
        s["status"] = "complete" if is_completed else "current"
        statuses.append(s)

        # 3) Si cette étape n'est PAS completed, la chaîne est rompue :
        #    toutes les suivantes seront locked.
        if not is_completed:
            chain_broken = True

    return statuses


async def _load_manual_step_overrides(site_id: str) -> dict[str, bool]:
    """Lit `db.sites.{id}.manual_step_overrides` (dict {step_key: bool})
    qui mémorise les "Valider et passer à l'étape suivante" cliqués par le
    concepteur. Permet de débloquer une étape même si les checks data
    automatiques ne passent pas (ex: étape SEO score < 70 mais le
    concepteur considère que c'est OK pour son cas).
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "manual_step_overrides": 1})
    return (site or {}).get("manual_step_overrides") or {}


# ────────── API publique ────────── #

@router.get("/sites/{site_id}/steps/status")
async def get_steps_status(
    site_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Renvoie l'état auto-calculé des 9 étapes pour ce site.

    Source de vérité unique pour le gating UI et les route guards. Aucune
    donnée n'est persistée ici — tout est dérivé de la DB à chaque appel.
    """
    await _check_site_access(site_id, user)
    statuses = await compute_step_statuses(site_id)
    completed_count = sum(1 for s in statuses if s["completed"])
    next_step = next((s["key"] for s in statuses if not s["completed"]), None)
    return {
        "site_id": site_id,
        "steps": statuses,
        "completed_count": completed_count,
        "total_count": len(statuses),
        "progress_pct": round((completed_count / len(statuses)) * 100),
        "next_step": next_step,
    }


# Mapping: la clé interne "content" est exposée côté frontend sous le slug "blog"
# (le modèle métier = articles de blog SEO, c'est plus naturel pour l'utilisateur).
# On garde "content" en interne pour ne pas casser la DB / les checkers existants.
SLUG_MAP = {"content": "blog"}


@router.get("/sites/{site_id}/journey")
async def get_journey(
    site_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Schéma "journey" de plus haut niveau pour les UIs modernes.

    Contrat stable (utilisé par SiteDetail, SiteAnalytics, PostValidationBanner,
    route guards). S'appuie sur compute_step_statuses — single source of truth.

    Réponse :
      {
        "site_id": str,
        "current_step": slug | null,
        "progress": {"complete": int, "total": int, "pct": int},
        "all_completed": bool,
        "steps": [
          {
            "slug": "pricing" | "import" | ... | "blog" | "seo" | "qa",
            "key":  "pricing" | ... | "content" | ...,   # legacy clé DB
            "label": str,
            "status": "complete" | "current" | "locked",
            "completed": bool,                           # backward-compat
            "reason": str,
            "order": int,
            "counters": dict,
          }, ...
        ]
      }
    """
    await _check_site_access(site_id, user)
    statuses = await compute_step_statuses(site_id)
    total = len(statuses)
    complete_count = sum(1 for s in statuses if s["completed"])
    current_idx = next((i for i, s in enumerate(statuses) if not s["completed"]), total)

    steps: list[dict] = []
    for i, s in enumerate(statuses):
        # 2026-04-29 (refonte UX strict) — `status` token simple :
        #   - "complete"  : étape strict completed (ou manuellement validée)
        #   - "locked"    : `blocked_by_previous=True`
        #   - "current"   : étape suivante non bloquée
        if s["completed"]:
            status_token = "complete"
        elif s.get("blocked_by_previous"):
            status_token = "locked"
        else:
            status_token = "current"
        blocked = bool(s.get("blocked_by_previous", False))
        # `is_clickable` = explicite pour le frontend (single source of truth)
        is_clickable = (not blocked) or bool(s["completed"])
        steps.append({
            "slug": SLUG_MAP.get(s["key"], s["key"]),
            "key": s["key"],
            "label": s["label"],
            "subtitle": STEP_SUBTITLES.get(s["key"]),
            "status": status_token,
            "completed": s["completed"],
            "manual_validated": bool(s.get("manual_validated", False)),
            "blocked_by_previous": blocked,
            "is_clickable": is_clickable,
            "reason": s.get("reason"),
            "order": s.get("order"),
            "counters": s.get("counters"),
        })

    current_slug = steps[current_idx]["slug"] if current_idx < total else None
    return {
        "site_id": site_id,
        "current_step": current_slug,
        "progress": {
            "complete": complete_count,
            "total": total,
            "pct": round((complete_count / total) * 100) if total else 0,
        },
        "all_completed": complete_count == total and total > 0,
        "steps": steps,
    }


@router.get("/sites/{site_id}/steps/can-access/{step_key}")
async def can_access_step(
    site_id: str,
    step_key: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Helper pour route guards frontend. Retourne si l'étape est accessible
    (= pas bloquée par la précédente) et la redirection conseillée sinon.
    """
    await _check_site_access(site_id, user)
    if step_key not in STEP_ORDER:
        raise HTTPException(400, f"Étape inconnue : {step_key}")
    statuses = await compute_step_statuses(site_id)
    idx = STEP_ORDER.index(step_key)
    target = statuses[idx]
    if target["blocked_by_previous"]:
        # Redirige vers la 1re étape non-complétée
        previous = next(
            (s for s in statuses if not s["completed"] and s["order"] < target["order"]),
            statuses[0],
        )
        return {
            "allowed": False,
            "reason": f"L'étape '{previous['label']}' n'est pas complétée.",
            "redirect_to_step": previous["key"],
            "redirect_reason": previous["reason"],
        }
    return {"allowed": True, "step": target}


# ────────── Override import "couverture partielle" ────────── #

@router.post("/sites/{site_id}/steps/import/force-partial")
async def force_partial_import(
    site_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Accepte explicitement de passer à l'étape 3 sans couverture 100% des
    pays. Persiste `site.import_force_partial = {value, forced_at, forced_by,
    missing_countries}` avec traçabilité complète.
    """
    await _check_site_access(site_id, user)
    # Recalcule la couverture actuelle pour figer le snapshot au moment du force
    from datetime import datetime, timezone
    statuses = await compute_step_statuses(site_id)
    import_step = next((s for s in statuses if s["key"] == "import"), None)
    missing = ((import_step or {}).get("counters") or {}).get("missing_countries") or []
    flag = {
        "value": True,
        "forced_at": datetime.now(timezone.utc).isoformat(),
        "forced_by": user.get("id"),
        "forced_by_email": user.get("email"),
        "missing_countries_at_time": missing,
    }
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {"import_force_partial": True, "import_force_partial_meta": flag}},
    )
    return {"ok": True, "import_force_partial": True, "meta": flag}


@router.post("/sites/{site_id}/steps/import/revoke-force-partial")
async def revoke_force_partial(
    site_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Annule la décision de couverture partielle. L'étape import redevient
    bloquée tant que la couverture pays n'est pas 100%."""
    await _check_site_access(site_id, user)
    await db.sites.update_one(
        {"id": site_id},
        {"$unset": {"import_force_partial": "", "import_force_partial_meta": ""}},
    )
    return {"ok": True, "import_force_partial": False}


# ────────── Gating hard HTTP 409 ────────── #

async def require_step(site_id: str, prev_step: str) -> None:
    """Dépendance FastAPI-friendly (à appeler manuellement dans les routes).
    Lève HTTPException(409) si l'étape `prev_step` n'est pas complétée.

    Usage :
        await require_step(site_id, "pricing")  # avant un product import
    """
    if prev_step not in STEP_ORDER:
        return  # no-op si la clé n'existe pas (compat)
    statuses = await compute_step_statuses(site_id)
    target = next((s for s in statuses if s["key"] == prev_step), None)
    if not target:
        return
    if not target["completed"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "step_not_completed",
                "required_step": prev_step,
                "reason": target["reason"],
                "message": (
                    f"Impossible d'effectuer cette action : "
                    f"l'étape '{target['label']}' doit être complétée d'abord. "
                    f"Détail : {target['reason']}"
                ),
            },
        )


# ────────── Validation manuelle des étapes (refonte UX 2026-04-29) ────────── #


@router.post("/sites/{site_id}/journey/validate-step")
async def validate_step(
    site_id: str,
    user: dict = Depends(get_current_user),
    body: Optional[dict] = None,
) -> dict:
    """Marque une étape comme manuellement validée par le concepteur.

    Body : `{"step_key": "content"}`. L'étape passe à `completed=true` quel
    que soit le résultat des checks data automatiques. Persisté dans
    `site.manual_step_overrides[step_key] = true`. Permet le pattern UX
    "Valider et passer à l'étape suivante" depuis chaque page d'étape.

    Sécurité : on n'autorise la validation que si l'étape n'est pas
    `blocked_by_previous` (= étape précédente strict completed). Sinon 409.
    """
    await _check_site_access(site_id, user)
    if not body or "step_key" not in body:
        raise HTTPException(400, "Body requis : {step_key: '<key>'}")
    step_key = body["step_key"]
    if step_key not in STEP_ORDER:
        raise HTTPException(400, f"Étape inconnue : {step_key}")
    statuses = await compute_step_statuses(site_id)
    target = next((s for s in statuses if s["key"] == step_key), None)
    if target and target.get("blocked_by_previous"):
        raise HTTPException(
            409,
            f"Impossible de valider '{step_key}' : l'étape précédente n'est pas complétée.",
        )
    from datetime import datetime, timezone
    await db.sites.update_one(
        {"id": site_id},
        {
            "$set": {
                f"manual_step_overrides.{step_key}": True,
                f"manual_step_overrides_meta.{step_key}": {
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "validated_by": user.get("id"),
                    "validated_by_email": user.get("email"),
                },
            }
        },
    )
    # Recompute pour retourner l'état actualisé (next step accessible)
    statuses = await compute_step_statuses(site_id)
    return {
        "ok": True,
        "step_key": step_key,
        "completed": True,
        "next_step": next(
            (s["key"] for s in statuses if not s["completed"] and not s.get("blocked_by_previous")),
            None,
        ),
        "all_completed": all(s["completed"] for s in statuses),
    }


@router.delete("/sites/{site_id}/journey/validate-step/{step_key}")
async def revoke_validate_step(
    site_id: str,
    step_key: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Annule la validation manuelle d'une étape (admin / debug)."""
    await _check_site_access(site_id, user)
    if step_key not in STEP_ORDER:
        raise HTTPException(400, f"Étape inconnue : {step_key}")
    await db.sites.update_one(
        {"id": site_id},
        {
            "$unset": {
                f"manual_step_overrides.{step_key}": "",
                f"manual_step_overrides_meta.{step_key}": "",
            }
        },
    )
    return {"ok": True, "step_key": step_key, "manual_validated": False}
