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

# Ordre canonique des 10 étapes (mission Finalisation 2026-04-29 :
# `translate` remplace `pages` à la position 7 — les pages essentielles sont
# désormais générées automatiquement au launch-auto, donc plus besoin d'en
# faire une étape Cockpit séparée. La traduction multilingue est en revanche
# le point clé pour passer en GO sur 6 langues × 11 pays.)
STEP_ORDER = [
    "pricing", "import", "upsells", "forecast", "branding",
    "domain", "translate", "content", "seo", "qa",
]

STEP_LABELS = {
    "pricing":   "Analyse concurrence & pricing",
    "import":    "Import du catalogue",
    "upsells":   "Upsells & accessoires",
    "forecast":  "Étude financière 30j",
    "branding":  "Identité & branding",
    "domain":    "Nom de domaine",
    "translate": "Traduction multilingue",
    "content":   "Blog & contenu SEO",
    "seo":       "Santé SEO / AEO",
    "qa":        "QA & mise en ligne",
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


async def _check_pages(site_id: str, site: dict) -> dict:
    """Pages légales (mentions, cgv, confidentialite, cookies) + 3 éditoriales
    (about, faq, contact) toutes non-vides."""
    pages = (site.get("design") or {}).get("pages") or {}
    required_legal = ["mentions_legales", "cgv", "confidentialite", "cookies"]
    required_editorial = ["about", "faq", "contact"]
    filled_legal = [k for k in required_legal if _page_has_content(pages.get(k))]
    filled_editorial = [k for k in required_editorial if _page_has_content(pages.get(k))]
    missing = [
        k for k in (required_legal + required_editorial)
        if k not in (filled_legal + filled_editorial)
    ]
    completed = len(missing) == 0
    reason = (
        "Toutes les pages essentielles remplies"
        if completed
        else f"Pages manquantes : {', '.join(missing)}"
    )
    return {
        "key": "pages",
        "label": STEP_LABELS["pages"],
        "completed": completed,
        "reason": reason,
        "counters": {"filled": filled_legal + filled_editorial, "missing": missing},
    }


async def _check_content(site_id: str, site: dict) -> dict:
    """≥1 pillar + ≥3 satellites dans blog_posts."""
    posts = (site.get("design") or {}).get("blog_posts") or []
    pillars = [p for p in posts if (p.get("type") == "pillar" or p.get("role") == "pillar")]
    satellites = [p for p in posts if (p.get("type") == "satellite" or p.get("role") == "satellite")]
    # Fallback : si pas de type explicite, considère le 1er comme pillar
    if not pillars and posts:
        pillars = posts[:1]
        satellites = posts[1:]
    pillar_ok = len(pillars) >= 1
    satellite_ok = len(satellites) >= 3
    completed = pillar_ok and satellite_ok
    reason = (
        f"{len(pillars)} pillar(s) + {len(satellites)} satellite(s)"
        if completed
        else f"Requis : 1 pillar + 3 satellites · actuel : {len(pillars)} pillar / {len(satellites)} satellites"
    )
    return {
        "key": "content",
        "label": STEP_LABELS["content"],
        "completed": completed,
        "reason": reason,
        "counters": {"pillars": len(pillars), "satellites": len(satellites)},
    }


async def _check_seo(site_id: str, site: dict) -> dict:
    """SEO studio rempli (seo_score ≥ 70)."""
    score = int((site.get("design") or {}).get("seo_score") or 0)
    threshold = 70
    completed = score >= threshold
    reason = f"Score SEO {score}/100 (seuil {threshold})"
    return {
        "key": "seo",
        "label": STEP_LABELS["seo"],
        "completed": completed,
        "reason": reason,
        "counters": {"score": score, "threshold": threshold},
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
    "domain":    _check_domain,        # Lot D — étape 6 (optional)
    "translate": _check_translate,     # Mission Finalisation — étape 7 (remplace `pages`)
    "pages":     _check_pages,         # déprécié mais conservé pour back-compat (route /sites/:id/pages)
    "content":   _check_content,
    "seo":       _check_seo,
    "qa":        _check_qa,
}


async def compute_step_statuses(site_id: str) -> list[dict]:
    """Calcule le statut des 10 étapes pour un site (Lot D — domain inséré).
    Retourne la liste ordonnée [pricing, import, …, qa] avec
    `blocked_by_previous` pour chaque étape.

    L'étape `domain` est marquée `optional: true` : elle ne bloque pas la
    suite (le concepteur peut la skipper et utiliser le sous-domaine plateforme).
    """
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    statuses: list[dict] = []
    previous_completed = True  # première étape toujours accessible
    for key in STEP_ORDER:
        checker = _CHECKERS[key]
        s = await checker(site_id, site)
        s["order"] = STEP_ORDER.index(key) + 1
        s["blocked_by_previous"] = not previous_completed
        statuses.append(s)
        # Lot D — Une étape optionnelle ne bloque pas l'étape suivante :
        # même si `domain` n'est pas complété, `pages` reste accessible.
        if s.get("optional"):
            # propage le previous_completed précédent
            pass
        else:
            previous_completed = s["completed"]
    return statuses


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
        if s["completed"]:
            status_token = "complete"
        elif i == current_idx:
            status_token = "current"
        else:
            status_token = "locked"
        steps.append({
            "slug": SLUG_MAP.get(s["key"], s["key"]),
            "key": s["key"],
            "label": s["label"],
            "status": status_token,
            "completed": s["completed"],
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


# ────────── Compatibilité legacy : déprécier validate-step manuel ────────── #

@router.post("/sites/{site_id}/journey/validate-step", deprecated=True)
async def deprecated_validate_step(
    site_id: str,
    user: dict = Depends(get_current_user),
    body: Optional[dict] = None,
) -> dict:
    """DEPRECATED (Chantier 1) — La validation manuelle est supprimée.

    Retourne 410 Gone pour forcer le client frontend à basculer sur le nouvel
    endpoint GET /sites/{id}/steps/status.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "La validation manuelle des étapes est supprimée. "
            "Les étapes sont désormais complétées automatiquement par les données "
            "(ex: 5 produits importés, design publié, etc.). "
            "Utilisez GET /api/sites/{site_id}/steps/status pour voir l'état."
        ),
    )
