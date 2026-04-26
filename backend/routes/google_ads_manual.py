"""
Phase 7 — Google Ads Manual (pixel natif + export assets pour campagne manuelle).

Endpoints :
  GET    /api/sites/{id}/google-ads/config                 — concepteur + admin
  PATCH  /api/sites/{id}/google-ads/config                 — concepteur + admin
  GET    /api/public/sites/{id}/google-ads/public-config   — public (consommé par le storefront)
  POST   /api/sites/{id}/google-ads/generate-export        — concepteur + admin
  GET    /api/sites/{id}/google-ads/export/{export_id}/{file}   — concepteur + admin
  GET    /api/sites/{id}/google-ads/exports                — concepteur + admin (historique)

Cohabitation avec `routes/google_ads.py` (OAuth + Ads API) : les préfixes ne
collisionnent pas grâce à `/sites/{id}/` dans les routes ci-dessous.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from deps import db, get_current_user

logger = logging.getLogger("conceptfactory.google_ads_manual")
router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "").strip()

# Storage filesystem : idempotent
EXPORTS_ROOT = Path("/app/backend/uploads/google_ads_exports")
EXPORTS_ROOT.mkdir(parents=True, exist_ok=True)

# Throttle Claude global — réutilise le même pattern que Phase 6
_claude_semaphore = asyncio.Semaphore(2)


# --------------------------------------------------------------------------
#  MODELS
# --------------------------------------------------------------------------
class GoogleAdsConfig(BaseModel):
    conversion_id: Optional[str] = Field(default=None, description="Ex: AW-123456789")
    conversion_label: Optional[str] = Field(default=None, description="Ex: abc_defGhi")
    enabled: bool = False


class GenerateExportInput(BaseModel):
    campaign_type: str = Field(default="both", pattern="^(search|shopping|both)$")
    target_country: Optional[str] = None


# --------------------------------------------------------------------------
#  HELPERS
# --------------------------------------------------------------------------
async def _check_site_access(site_id: str, user: dict) -> dict:
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site not found")
    if user.get("role") != "admin" and site.get("operator_id") != user.get("id"):
        raise HTTPException(403, "Forbidden")
    return site


def _validate_conversion_id(cid: str) -> str:
    cid = (cid or "").strip()
    if not cid:
        return ""
    if not re.match(r"^AW-[0-9]{6,12}$", cid):
        raise HTTPException(422, "Conversion ID must match pattern 'AW-XXXXXXXXX'")
    return cid


async def _claude_call(system: str, user: str, timeout: int = 150) -> Optional[dict]:
    """Phase 0 — délègue à `safe_claude_json` (retry + circuit breaker).

    Conserve le sémaphore global (concurrence Claude limitée à ce module pour
    ne pas saturer le proxy lors d'un export massif).
    """
    if not EMERGENT_LLM_KEY:
        return None
    from services.llm_resilience import safe_claude_json, LLMUnavailableError
    async with _claude_semaphore:
        t0 = time.time()
        try:
            parsed = await safe_claude_json(
                system, user,
                session_id=f"gads-export-{uuid.uuid4().hex[:8]}",
                timeout=timeout,
            )
            duration = time.time() - t0
            tokens = (len(system) + len(user)) // 4
            logger.info(f"[gads-export/claude] OK {duration:.1f}s ~{tokens}tok")
            return parsed
        except (LLMUnavailableError, ValueError) as e:
            logger.warning(f"[gads-export/claude] FAIL in {time.time()-t0:.1f}s (resilience): {str(e)[:200]}")
            return None
        except Exception as e:
            logger.warning(f"[gads-export/claude] FAIL in {time.time()-t0:.1f}s : {str(e)[:200]}")
            return None


# --------------------------------------------------------------------------
#  ENDPOINTS — Config pixel
# --------------------------------------------------------------------------
@router.get("/sites/{site_id}/google-ads/config")
async def get_gads_config(site_id: str, user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    cfg = site.get("google_ads") or {}
    return {
        "conversion_id": cfg.get("conversion_id") or None,
        "conversion_label": cfg.get("conversion_label") or None,
        "enabled": bool(cfg.get("enabled")),
        "updated_at": (cfg.get("updated_at").isoformat()
                        if isinstance(cfg.get("updated_at"), datetime) else cfg.get("updated_at")),
    }


@router.patch("/sites/{site_id}/google-ads/config")
async def patch_gads_config(site_id: str, payload: GoogleAdsConfig,
                             user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    cid = _validate_conversion_id(payload.conversion_id or "")
    label = (payload.conversion_label or "").strip()
    if cid and not label:
        # Ok : on peut configurer l'ID sans label (tag global sans conversion)
        pass
    now = datetime.now(timezone.utc)
    new_cfg = {
        "conversion_id": cid or None,
        "conversion_label": label or None,
        "enabled": bool(payload.enabled),
        "updated_at": now,
    }
    await db.sites.update_one(
        {"id": site_id},
        # On écrit à la fois dans `google_ads` (Phase 7) ET dans `design.tracking`
        # pour que le tracker storefront existant (StorefrontTracking.jsx) fonctionne
        # sans modification de lecture.
        {"$set": {
            "google_ads": new_cfg,
            "design.tracking.gads_conversion_id": cid or "",
            "design.tracking.gads_conversion_label": label or "",
            "design.tracking.gads_enabled": bool(payload.enabled),
        }},
    )
    return {**new_cfg, "updated_at": now.isoformat()}


@router.get("/public/sites/{site_id}/google-ads/public-config")
async def public_gads_config(site_id: str):
    """Public — consommé par le storefront pour injecter le pixel."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0, "google_ads": 1})
    if not site:
        return {"enabled": False}
    cfg = site.get("google_ads") or {}
    if not cfg.get("enabled") or not cfg.get("conversion_id"):
        return {"enabled": False}
    return {
        "enabled": True,
        "conversion_id": cfg["conversion_id"],
        "conversion_label": cfg.get("conversion_label") or "",
    }


# --------------------------------------------------------------------------
#  ENDPOINTS — Export assets
# --------------------------------------------------------------------------
GOOGLE_ADS_SYSTEM_PROMPT = (
    "Tu es un expert Google Ads senior. Tu génères des assets Responsive Search Ads "
    "conformes aux limites Google (Headline ≤30 chars, Description ≤90 chars, pas "
    "de ponctuation répétée). Tu réponds STRICTEMENT en JSON valide, sans commentaires."
)


CAMPAIGN_INTENTS = [
    {"intent": "transactional", "name": "Search — Transactionnel",
     "hint": "acheter, commander, prix, livraison, meilleur prix — utilisateurs prêts à acheter"},
    {"intent": "informational", "name": "Search — Informationnel",
     "hint": "comment choisir, guide, comparatif, avantages, avis — utilisateurs en recherche"},
    {"intent": "local", "name": "Search — Local",
     "hint": "près de chez moi, ville, code postal, magasin, livraison locale — intention géolocalisée"},
    {"intent": "brand", "name": "Search — Brand",
     "hint": "mots-clés liés à la marque du site (nom du site, promesse unique)"},
    {"intent": "competitor", "name": "Search — Concurrents",
     "hint": "noms/alternatives aux concurrents principaux dans la niche"},
]


async def _generate_one_campaign(site: dict, country: str, site_url: str,
                                  intent_info: dict, top_keywords: list[str]) -> Optional[dict]:
    """Génère UNE campagne (1 ad_group complet : 20 kw + 15 headlines + 4 desc)
    via un appel Claude court et stable (~1500 tokens output)."""
    niche = site.get("niche") or "produits senior"
    user_prompt = (
        f"Génère 1 ad_group Google Ads **{intent_info['intent']}** pour la niche "
        f"'{niche}' en {country}. Hint : {intent_info['hint']}.\n"
        f"URL finale : {site_url}\n"
        f"Mots-clés seed : {top_keywords[:15]}\n\n"
        "JSON STRICT :\n"
        "{\n"
        '  "ad_group_name": "Nom court du groupe",\n'
        '  "keywords": [{"keyword":"...","match_type":"Phrase","max_cpc":0.85}, ...20 items],\n'
        '  "headlines": ["...≤30c", ...15 items],\n'
        '  "descriptions": ["...≤90c", ...4 items],\n'
        '  "final_url": "' + site_url + '"\n'
        "}\n\n"
        "CONTRAINTES :\n"
        "- EXACTEMENT 20 keywords (match_type variés Phrase/Exact/Broad, max_cpc 0.30-1.80€)\n"
        "- EXACTEMENT 15 headlines (≤30 caractères)\n"
        "- EXACTEMENT 4 descriptions (≤90 caractères)\n"
        "- Pas de répétition, pas de ponctuation excessive, français naturel"
    )
    return await _claude_call(GOOGLE_ADS_SYSTEM_PROMPT, user_prompt, timeout=120)


async def _generate_assets(site: dict, campaign_type: str, country: str,
                            top_keywords: list[str], top_products: list[dict]) -> Optional[dict]:
    """Génère 5 campagnes en parallèle (semaphore 2 = 2 calls concurrents max).
    Plus rapide qu'un seul gros call qui time out toujours."""
    site_url = site.get("custom_domain") or site.get("default_domain") or f"/shop/{site['id']}"
    tasks = [
        _generate_one_campaign(site, country, site_url, intent, top_keywords)
        for intent in CAMPAIGN_INTENTS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    campaigns = []
    for intent, res in zip(CAMPAIGN_INTENTS, results):
        if isinstance(res, Exception) or not res:
            logger.warning(f"[gads-export] campaign {intent['intent']} failed, skipping")
            continue
        if not res.get("keywords"):
            continue
        campaigns.append({
            "name": intent["name"],
            "intent": intent["intent"],
            "ad_groups": [{
                "name": res.get("ad_group_name") or intent["intent"].capitalize(),
                "keywords": res.get("keywords") or [],
                "headlines": res.get("headlines") or [],
                "descriptions": res.get("descriptions") or [],
                "final_url": res.get("final_url") or site_url,
            }],
        })
    if not campaigns:
        return None
    return {"campaigns": campaigns}


def _trim_h(s: str, max_len: int) -> str:
    s = (s or "").strip().replace("\n", " ").replace("  ", " ")
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _build_keywords_csv(assets: dict) -> str:
    """Format Google Ads Editor — headers officiels."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    w.writerow(["Campaign", "Ad group", "Keyword", "Match type", "Max CPC"])
    for camp in assets.get("campaigns", []):
        cname = camp.get("name", "Campaign")
        for ag in camp.get("ad_groups", []):
            aname = ag.get("name", "Ad group")
            for kw in ag.get("keywords", []):
                w.writerow([
                    cname, aname,
                    (kw.get("keyword") or "").strip(),
                    (kw.get("match_type") or "Phrase").strip(),
                    f"{float(kw.get('max_cpc') or 0.80):.2f}",
                ])
    return buf.getvalue()


def _build_ads_csv(assets: dict) -> str:
    """Responsive Search Ads — 15 headlines + 4 descriptions + Final URL."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    headers = ["Campaign", "Ad group"] + [f"Headline {i}" for i in range(1, 16)] \
        + [f"Description {i}" for i in range(1, 5)] + ["Final URL"]
    w.writerow(headers)
    for camp in assets.get("campaigns", []):
        cname = camp.get("name", "Campaign")
        for ag in camp.get("ad_groups", []):
            aname = ag.get("name", "Ad group")
            heads = [_trim_h(h, 30) for h in (ag.get("headlines") or [])][:15]
            heads += [""] * (15 - len(heads))
            descs = [_trim_h(d, 90) for d in (ag.get("descriptions") or [])][:4]
            descs += [""] * (4 - len(descs))
            w.writerow([cname, aname] + heads + descs + [ag.get("final_url", "")])
    return buf.getvalue()


def _build_guide_md(site: dict, assets: dict, files: dict, campaign_type: str, country: str) -> str:
    name = site.get("name", "ton site")
    summary = {
        "campaigns": len(assets.get("campaigns", [])),
        "ad_groups": sum(len(c.get("ad_groups", [])) for c in assets.get("campaigns", [])),
        "keywords": sum(len(ag.get("keywords", []))
                        for c in assets.get("campaigns", [])
                        for ag in c.get("ad_groups", [])),
    }
    lines = [
        f"# Guide Google Ads — Campagne manuelle pour {name}",
        "",
        f"> Export généré pour **{campaign_type}** · pays cible **{country}**  ",
        f"> {summary['campaigns']} campagnes · {summary['ad_groups']} groupes d'annonces · "
        f"{summary['keywords']} mots-clés · ~{summary['ad_groups'] * 15} headlines · "
        f"~{summary['ad_groups'] * 4} descriptions",
        "",
        "## 🚀 En 10 minutes, tu crées ta campagne manuellement",
        "",
        "### Étape 1 — Installe Google Ads Editor",
        "",
        "Télécharge [Google Ads Editor](https://ads.google.com/home/tools/ads-editor/) (gratuit, Mac/Windows).",
        "Connecte-toi avec le compte Google Ads lié à ton entreprise.",
        "",
        "### Étape 2 — Importe le CSV des mots-clés",
        "",
        "1. **Compte → Comptes → Importer depuis un fichier**",
        "2. Sélectionne `keywords.csv` (téléchargé depuis Altiaro)",
        "3. Valide la correspondance des colonnes : Campaign, Ad group, Keyword, Match type, Max CPC — tout doit mapper automatiquement.",
        "4. Clique **Étape suivante** → **Appliquer**. Les 5 campagnes et leurs groupes d'annonces sont créés d'un coup.",
        "",
        "### Étape 3 — Importe le CSV des annonces RSA",
        "",
        "1. Répète **Importer depuis un fichier** avec `ads.csv`.",
        "2. Google Ads Editor reconnaît les colonnes Headline 1-15 et Description 1-4.",
        "3. Les **Responsive Search Ads** sont créés dans chacun des 5 groupes. Pas besoin de les retaper.",
        "",
        "### Étape 4 — Paramètres de campagne",
        "",
        "Pour chaque campagne nouvellement importée :",
        "",
        "- **Pays ciblé** : 🇫🇷/🇩🇪/etc. selon la campagne (voir le nom, Altiaro t'a rangé par intent pas par pays ; duplique et ajuste si besoin)",
        "- **Budget quotidien** : démarre à **10 €/jour** par campagne (5×10 = 50 €/jour total)",
        "- **Enchères** : sélectionne **Maximiser les conversions** (même si tes conversions ne sont pas encore trackées ; on active le pixel à l'étape 5)",
        "- **Appareils** : Desktop + Mobile + Tablet (pas d'exclusion pour l'instant)",
        "- **Calendrier** : actif 24/7 (on affinera après 7 jours de données)",
        "",
        "### Étape 5 — Active le pixel de conversion dans Altiaro",
        "",
        "1. Dans Google Ads : **Outils & paramètres → Mesure → Conversions → Nouvelle action de conversion → Site web**",
        "2. URL : l'URL de ton site Altiaro (ex. `https://toncustom-domain.com`)",
        "3. Catégorie : **Achat**",
        "4. Valeur : **Utiliser des valeurs différentes** (Altiaro envoie la vraie valeur de la commande)",
        "5. Après création, Google affiche le **tag de suivi** :",
        "   - `Identifiant de conversion` (format `AW-XXXXXXXXX`)",
        "   - `Étiquette de conversion` (ex. `abc_defGhi`)",
        "6. Retourne dans Altiaro : **Admin → Site → Google Ads**, colle ces deux valeurs, coche **Activer le pixel**, sauvegarde.",
        "7. Le storefront d'Altiaro injecte automatiquement le `gtag.js` + `gtag('event','conversion',…)` au moment du purchase. Pas de dev à faire.",
        "",
        "### Étape 6 — Publie tes campagnes",
        "",
        "Dans Google Ads Editor, clique sur **Publier** en haut à droite.",
        "Les campagnes passent en statut **Actif** dans les 5-10 min.",
        "Bon launch 🎯",
        "",
        "---",
        "",
        "## 📁 Fichiers joints",
        "",
        "- `keywords.csv` → format **Google Ads Editor** — headers exacts : Campaign, Ad group, Keyword, Match type, Max CPC",
        "- `ads.csv` → format **Responsive Search Ads** — 15 headlines + 4 descriptions par groupe",
        "- `guide.md` → ce document",
    ]
    if campaign_type in ("shopping", "both"):
        lines += [
            "",
            "## 🛒 Shopping — Feed produits Google Merchant Center",
            "",
            "Le site expose un feed XML Merchant conforme :",
            f"- URL publique : `/api/sites/{site['id']}/merchant-feed.xml` (si endpoint merchant existant)",
            "",
            "Dans Merchant Center : **Produits → Flux → Créer un flux → URL planifiée** et colle l'URL ci-dessus. "
            "Une fois les produits approuvés, active la campagne Shopping dans Google Ads (elle utilisera automatiquement ce feed).",
        ]
    return "\n".join(lines)


async def _site_top_keywords_and_products(site_id: str, country: str) -> tuple[list[str], list[dict]]:
    # Top keywords : last QuickScan for the site
    qs = await db.quick_scans.find_one(
        {"site_id": site_id}, sort=[("created_at", -1)]
    ) or await db.quick_scans.find_one(sort=[("created_at", -1)])
    kws: list[str] = []
    if qs:
        for k in (qs.get("keywords") or qs.get("serp_keywords") or [])[:40]:
            if isinstance(k, str):
                kws.append(k)
            elif isinstance(k, dict):
                kws.append(k.get("keyword") or k.get("term") or "")
    # Emerging kw en fallback
    if len(kws) < 10:
        async for d in db.emerging_keywords.find({"site_id": site_id}, {"_id": 0, "keyword": 1}).limit(20):
            if d.get("keyword"):
                kws.append(d["keyword"])
    kws = [k.strip() for k in kws if k and k.strip()]
    kws = list(dict.fromkeys(kws))  # dedupe preserve order

    # Top products
    products: list[dict] = []
    async for p in db.products.find({"site_id": site_id}, {"_id": 0, "id": 1, "name": 1}).limit(5):
        n = p.get("name")
        title = n.get("fr") if isinstance(n, dict) else str(n or "")
        if title:
            products.append({"id": p["id"], "name": title})
    return kws, products


@router.post("/sites/{site_id}/google-ads/generate-export")
async def generate_export(site_id: str, payload: GenerateExportInput,
                           user: dict = Depends(get_current_user)):
    site = await _check_site_access(site_id, user)
    country = (payload.target_country or (site.get("selected_countries") or ["FR"])[0]).upper()

    # Préparer inputs
    top_keywords, top_products = await _site_top_keywords_and_products(site_id, country)
    if not top_keywords:
        # Fallback ultra-safe
        niche = site.get("niche") or "produits senior"
        top_keywords = [niche, f"{niche} pas cher", f"{niche} livraison rapide",
                        f"meilleur {niche}", f"avis {niche}"]

    assets = await _generate_assets(site, payload.campaign_type, country, top_keywords, top_products)
    if not assets or not assets.get("campaigns"):
        raise HTTPException(502, "Claude n'a pas retourné d'assets valides. Réessaie dans quelques secondes.")

    # Build files
    export_id = str(uuid.uuid4())
    folder = EXPORTS_ROOT / site_id / export_id
    folder.mkdir(parents=True, exist_ok=True)

    keywords_csv = _build_keywords_csv(assets)
    ads_csv = _build_ads_csv(assets)
    guide_md = _build_guide_md(site, assets, {}, payload.campaign_type, country)

    (folder / "keywords.csv").write_text(keywords_csv, encoding="utf-8")
    (folder / "ads.csv").write_text(ads_csv, encoding="utf-8")
    (folder / "guide.md").write_text(guide_md, encoding="utf-8")

    summary = {
        "campaigns_count": len(assets.get("campaigns", [])),
        "ad_groups_count": sum(len(c.get("ad_groups", [])) for c in assets.get("campaigns", [])),
        "keywords_count": sum(len(ag.get("keywords", []))
                              for c in assets.get("campaigns", [])
                              for ag in c.get("ad_groups", [])),
        "ads_count": sum(len(c.get("ad_groups", [])) for c in assets.get("campaigns", [])),
    }

    now = datetime.now(timezone.utc)
    doc = {
        "id": export_id,
        "site_id": site_id,
        "user_id": user.get("id"),
        "campaign_type": payload.campaign_type,
        "target_country": country,
        "summary": summary,
        "files_paths": {
            "keywords_csv": str(folder / "keywords.csv"),
            "ads_csv": str(folder / "ads.csv"),
            "guide_md": str(folder / "guide.md"),
        },
        "created_at": now,
        "expires_at": now + timedelta(days=30),
    }
    await db.google_ads_exports.insert_one(doc.copy())

    base = f"/api/sites/{site_id}/google-ads/export/{export_id}"
    return {
        "export_id": export_id,
        "created_at": now.isoformat(),
        "campaign_type": payload.campaign_type,
        "target_country": country,
        "files": {
            "keywords_csv": f"{base}/keywords.csv",
            "ads_csv": f"{base}/ads.csv",
            "guide_md": f"{base}/guide.md",
            "shopping_feed_url": f"/api/sites/{site_id}/merchant-feed.xml"
                if payload.campaign_type in ("shopping", "both") else None,
        },
        "summary": summary,
    }


@router.get("/sites/{site_id}/google-ads/exports")
async def list_exports(site_id: str, limit: int = 20,
                        user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    out = []
    async for d in db.google_ads_exports.find({"site_id": site_id}, {"_id": 0})\
            .sort([("created_at", -1)]).limit(min(limit, 50)):
        out.append({
            "id": d["id"],
            "campaign_type": d.get("campaign_type"),
            "target_country": d.get("target_country"),
            "summary": d.get("summary") or {},
            "created_at": d["created_at"].isoformat() if isinstance(d.get("created_at"), datetime) else d.get("created_at"),
            "files": {
                "keywords_csv": f"/api/sites/{site_id}/google-ads/export/{d['id']}/keywords.csv",
                "ads_csv": f"/api/sites/{site_id}/google-ads/export/{d['id']}/ads.csv",
                "guide_md": f"/api/sites/{site_id}/google-ads/export/{d['id']}/guide.md",
            },
        })
    return {"site_id": site_id, "total": len(out), "exports": out}


@router.get("/sites/{site_id}/google-ads/export/{export_id}/{filename}")
async def download_export(site_id: str, export_id: str, filename: str,
                           user: dict = Depends(get_current_user)):
    await _check_site_access(site_id, user)
    if filename not in {"keywords.csv", "ads.csv", "guide.md"}:
        raise HTTPException(400, "Invalid filename")
    doc = await db.google_ads_exports.find_one({"id": export_id, "site_id": site_id})
    if not doc:
        raise HTTPException(404, "Export not found")
    path = EXPORTS_ROOT / site_id / export_id / filename
    if not path.exists():
        raise HTTPException(404, "File not found on disk")
    media_type = "text/csv" if filename.endswith(".csv") else "text/markdown"
    # Pour le .md on renvoie en plain-text pour permettre preview, CSV en download
    if filename == "guide.md":
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type=media_type)
    return FileResponse(path, media_type=media_type, filename=f"{site_id[:8]}-{filename}")


# --------------------------------------------------------------------------
#  Indexes
# --------------------------------------------------------------------------
async def ensure_gads_manual_indexes() -> None:
    try:
        await db.google_ads_exports.create_index(
            [("site_id", 1), ("created_at", -1)], name="site_created_idx"
        )
        logger.info("[gads-manual] indexes ensured")
    except Exception:
        logger.exception("[gads-manual] indexes failed")
