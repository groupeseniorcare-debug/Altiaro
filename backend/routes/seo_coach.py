"""SEO Coach — alertes proactives hebdomadaires.

Calcule à partir du Pulse SEO existant un ensemble d'alertes éditoriales
intelligentes (score E-E-A-T, couverture keywords, cadence cluster) et envoie
un digest email Resend chaque lundi matin 09h CET (08h UTC).

L'agent ne spam PAS : seules les alertes avec `severity >= info` sont envoyées,
et seulement si au moins 1 alerte `warn` ou `critical` est présente pour le site.

Endpoints publics
-----------------
- GET  /api/sites/{id}/seo/alerts           → alertes calculées (pour le cockpit)
- GET  /api/sites/{id}/seo/alerts/unread    → compteur pour le badge 🔔 topbar
- POST /api/sites/{id}/seo/alerts/mark-read → marque la dernière dispatch comme lue
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import os
import logging

import resend

from deps import db, get_current_user
from routes.design import seo_pulse  # reuse the pulse calculation

router = APIRouter(tags=["seo-coach"])
logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_DEFAULT_FROM", "onboarding@resend.dev")
RESEND_OWNER_EMAIL = os.environ.get("RESEND_OWNER_EMAIL", "")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# =====================================================================
# Core rule engine
# =====================================================================
def _compute_alerts(pulse: dict, site: dict) -> list[dict]:
    """Transforme un Pulse SEO en liste d'alertes actionnables.

    Chaque alerte : {id, severity, title, message, cta_label, cta_href, metric}
    """
    alerts = []
    site_id = site.get("id")

    avg = int(pulse.get("avg_eeat_score") or 0)
    coverage = int(pulse.get("coverage_pct") or 0)
    articles_month = int(pulse.get("articles_this_month") or 0)
    total_articles = int(pulse.get("articles_total") or 0)
    recent = pulse.get("recent_articles") or []
    bc_next = pulse.get("next_cluster_at")
    cluster_href = f"/sites/{site_id}/blog-posts"

    # --- A. E-E-A-T score ---
    if total_articles > 0:
        if avg < 55:
            alerts.append({
                "id": f"eeat-critical-{site_id}",
                "severity": "critical",
                "title": f"Votre score E-E-A-T moyen est tombé à {avg}/100",
                "message": (
                    "Google valorise les articles longs, structurés et qui citent d'autres pages. "
                    "Ajoutez des H2, des listes à puces et des liens internes sur vos derniers "
                    "articles pour remonter au-dessus de 70."
                ),
                "cta_label": "Ouvrir le blog →",
                "cta_href": cluster_href,
                "metric": avg,
            })
        elif avg < 70:
            low_posts = [r for r in recent if int(r.get("eeat_score") or 0) < 60]
            if low_posts:
                titles = ", ".join(
                    f"« {(r.get('title') or '')[:45]} »" for r in low_posts[:3]
                )
                alerts.append({
                    "id": f"eeat-warn-{site_id}",
                    "severity": "warn",
                    "title": f"Score E-E-A-T {avg}/100 — {len(low_posts)} article(s) à enrichir",
                    "message": f"À retravailler en priorité : {titles}.",
                    "cta_label": "Enrichir ces articles →",
                    "cta_href": cluster_href,
                    "metric": avg,
                })
    else:
        alerts.append({
            "id": f"no-articles-{site_id}",
            "severity": "warn",
            "title": "Aucun article publié",
            "message": (
                "Les boutiques e-commerce qui publient au moins 1 cluster de contenu "
                "captent en moyenne 3× plus de trafic organique sur 90 jours. "
                "Lancez votre premier cluster en un clic."
            ),
            "cta_label": "Générer mon premier cluster →",
            "cta_href": cluster_href,
            "metric": 0,
        })

    # --- B. Couverture keywords ---
    if pulse.get("keywords_total_informational", 0) > 0:
        if coverage == 0:
            alerts.append({
                "id": f"coverage-zero-{site_id}",
                "severity": "warn",
                "title": "Couverture keywords à 0 %",
                "message": (
                    "Vous avez "
                    f"{pulse.get('keywords_total_informational', 0)} keywords informationnels "
                    "identifiés à l'étape 8, mais aucun n'est encore utilisé par vos articles. "
                    "Lancer le cluster mensuel va commencer à les convertir en trafic."
                ),
                "cta_label": "Activer le cluster auto →",
                "cta_href": cluster_href,
                "metric": 0,
            })
        elif coverage < 35:
            alerts.append({
                "id": f"coverage-low-{site_id}",
                "severity": "info",
                "title": f"Couverture keywords à {coverage} %",
                "message": (
                    "Vous avez encore de la marge. Chaque cluster mensuel couvre 4-5 "
                    "nouveaux keywords — gardez le rythme."
                ),
                "cta_label": "Voir les keywords →",
                "cta_href": cluster_href,
                "metric": coverage,
            })

    # --- C. Cadence mensuelle ---
    if articles_month == 0 and total_articles > 0:
        alerts.append({
            "id": f"cadence-{site_id}",
            "severity": "info",
            "title": "Aucun article publié ce mois-ci",
            "message": (
                "Le SEO se gagne à la régularité. Activez la publication automatique "
                "mensuelle pour rester dans le radar Google et Perplexity."
            ),
            "cta_label": "Activer le cluster auto →",
            "cta_href": cluster_href,
            "metric": 0,
        })

    # --- D. Proximité prochain cluster (info pacing) ---
    if bc_next and total_articles > 0:
        try:
            next_dt = datetime.fromisoformat(bc_next.replace("Z", "+00:00"))
            days = (next_dt - datetime.now(timezone.utc)).days
            if 0 <= days <= 7:
                alerts.append({
                    "id": f"cluster-upcoming-{site_id}",
                    "severity": "info",
                    "title": f"Prochain cluster dans {days} jour(s)",
                    "message": (
                        "Profitez-en pour relancer l'analyse SEO (étape 8) ou ajouter "
                        "un keyword prioritaire avant la génération automatique."
                    ),
                    "cta_label": "Préparer les keywords →",
                    "cta_href": f"/sites/{site_id}/seo",
                    "metric": days,
                })
        except Exception:
            pass

    return alerts


def _severity_rank(s: str) -> int:
    return {"critical": 3, "warn": 2, "info": 1}.get(s, 0)


# =====================================================================
# HTTP endpoints
# =====================================================================
@router.get("/sites/{site_id}/seo/alerts")
async def get_seo_alerts(site_id: str, user=Depends(get_current_user)):
    """Retourne les alertes SEO Coach courantes pour le site."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    # Reuse the seo_pulse function to stay DRY
    pulse = await seo_pulse(site_id, user)
    alerts = _compute_alerts(pulse, site)
    alerts.sort(key=lambda a: -_severity_rank(a.get("severity")))
    return {
        "alerts": alerts,
        "max_severity": alerts[0]["severity"] if alerts else "none",
        "count": len(alerts),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sites/{site_id}/seo/alerts/unread")
async def unread_alerts_count(site_id: str, user=Depends(get_current_user)):
    """Compteur pour le badge cloche 🔔 dans le cockpit.
    Retourne 0 si le user a déjà lu la dernière dispatch."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    pulse = await seo_pulse(site_id, user)
    alerts = _compute_alerts(pulse, site)
    # Remove 'info' from the bell badge — only surface warn/critical
    actionable = [a for a in alerts if a["severity"] in ("warn", "critical")]

    # Filter out alerts already marked as read by this user
    read_ids = set(
        (((site.get("design") or {}).get("seo_coach") or {}).get("read_alert_ids"))
        or []
    )
    unread = [a for a in actionable if a["id"] not in read_ids]

    return {
        "unread_count": len(unread),
        "max_severity": unread[0]["severity"] if unread else "none",
        "total_actionable": len(actionable),
    }


@router.post("/sites/{site_id}/seo/alerts/mark-read")
async def mark_alerts_read(site_id: str, user=Depends(get_current_user)):
    """Marque toutes les alertes actuelles comme lues."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    pulse = await seo_pulse(site_id, user)
    alerts = _compute_alerts(pulse, site)
    ids = [a["id"] for a in alerts]
    await db.sites.update_one(
        {"id": site_id},
        {"$set": {
            "design.seo_coach.read_alert_ids": ids,
            "design.seo_coach.last_read_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "marked_read": len(ids)}


# =====================================================================
# Email dispatch — called by APScheduler every Monday 08:00 UTC
# =====================================================================
def _render_digest_html(site: dict, alerts: list, pulse: dict) -> str:
    site_name = site.get("name") or "votre boutique"
    site_id = site.get("id")
    backend_origin = (
        os.environ.get("PUBLIC_ORIGIN") or "https://senior-france.preview.emergentagent.com"
    )
    alerts_html = ""
    for a in alerts:
        color = {"critical": "#991B1B", "warn": "#92400E", "info": "#065F46"}.get(a["severity"], "#0A0A0A")
        tag_bg = {"critical": "#FEE2E2", "warn": "#FEF3C7", "info": "#D1FAE5"}.get(a["severity"], "#F5F5F5")
        alerts_html += f"""
<div style="border:1px solid #E5E5E5; border-radius:2px; padding:20px; margin-bottom:12px; background:#FFFFFF">
  <span style="display:inline-block; font-size:10px; letter-spacing:0.25em; text-transform:uppercase; padding:3px 8px; background:{tag_bg}; color:{color}; border-radius:2px; font-weight:600">
    {a['severity']}
  </span>
  <h3 style="margin:12px 0 8px; font-family:Georgia, serif; font-size:19px; line-height:1.3; color:#0A0A0A">
    {a['title']}
  </h3>
  <p style="margin:0 0 14px; font-size:14px; line-height:1.55; color:#525252">{a['message']}</p>
  <a href="{backend_origin}{a['cta_href']}"
     style="display:inline-block; padding:10px 18px; background:#0A0A0A; color:#FFFFFF;
            font-size:12px; font-weight:600; text-decoration:none; border-radius:2px;
            letter-spacing:0.04em">
    {a['cta_label']}
  </a>
</div>
"""
    return f"""<!DOCTYPE html>
<html><body style="margin:0; padding:0; background:#FAFAFA; font-family:'Helvetica Neue', Arial, sans-serif; color:#0A0A0A">
<div style="max-width:640px; margin:0 auto; padding:48px 24px">
  <div style="text-align:center; margin-bottom:32px">
    <div style="font-size:10px; letter-spacing:0.4em; text-transform:uppercase; color:#737373; margin-bottom:12px">
      Pulse SEO · Hebdo
    </div>
    <h1 style="font-family:Georgia, serif; font-size:32px; line-height:1.15; color:#0A0A0A; margin:0; letter-spacing:-0.01em">
      Votre coach SEO a {len(alerts)} recommandation{'s' if len(alerts) > 1 else ''} pour {site_name}.
    </h1>
  </div>

  <div style="background:#FFFFFF; border:1px solid #E5E5E5; padding:20px; border-radius:2px; margin-bottom:24px">
    <table style="width:100%; border-collapse:collapse">
      <tr>
        <td style="width:33%; padding:8px">
          <div style="font-size:10px; letter-spacing:0.3em; text-transform:uppercase; color:#737373">Articles ce mois</div>
          <div style="font-family:Georgia, serif; font-size:28px; margin-top:4px">{pulse.get('articles_this_month', 0)}</div>
        </td>
        <td style="width:33%; padding:8px; border-left:1px solid #E5E5E5">
          <div style="font-size:10px; letter-spacing:0.3em; text-transform:uppercase; color:#737373">Score E-E-A-T</div>
          <div style="font-family:Georgia, serif; font-size:28px; margin-top:4px">{pulse.get('avg_eeat_score', 0)}</div>
        </td>
        <td style="width:33%; padding:8px; border-left:1px solid #E5E5E5">
          <div style="font-size:10px; letter-spacing:0.3em; text-transform:uppercase; color:#737373">Couverture kw</div>
          <div style="font-family:Georgia, serif; font-size:28px; margin-top:4px">{pulse.get('coverage_pct', 0)}%</div>
        </td>
      </tr>
    </table>
  </div>

  {alerts_html}

  <div style="margin-top:40px; padding-top:20px; border-top:1px solid #E5E5E5; text-align:center; font-size:11px; color:#A3A3A3; line-height:1.6">
    Pulse SEO · Altiaro — envoyé chaque lundi à 09h<br/>
    <a href="{backend_origin}/sites/{site_id}" style="color:#737373">Ouvrir mon cockpit</a>
    &nbsp;·&nbsp;
    <a href="{backend_origin}/sites/{site_id}/blog-posts" style="color:#737373">Désactiver les alertes</a>
  </div>
</div>
</body></html>"""


async def send_weekly_seo_digests() -> dict:
    """APScheduler entry — itère les sites `seo_coach.email_enabled != False`
    et envoie un digest Resend si au moins 1 alerte warn/critical.
    Snapshot le Pulse de chaque site (pour l'historique + sparkline)."""
    sent, skipped = 0, 0
    # First — snapshot ALL sites (even the ones with no email), because
    # the history graph matters for every Concepteur.
    await _snapshot_all_sites()

    if not RESEND_API_KEY:
        logger.warning("[seo-coach] RESEND_API_KEY missing — skipping email phase")
        return {"sent": 0, "skipped": "no_api_key", "snapshots": "done"}

    sent, skipped = 0, 0
    cursor = db.sites.find({}, {"_id": 0})
    async for site in cursor:
        try:
            coach_cfg = ((site.get("design") or {}).get("seo_coach")) or {}
            if coach_cfg.get("email_enabled") is False:
                continue

            # Compute alerts without requiring an authenticated user context
            # by inlining the pulse logic — we cheat by using a fake "admin user"
            # shape since seo_pulse uses `_check_site_access` which we must bypass.
            # Easiest: call the rule engine directly using a lightweight pulse
            # computed from the site doc we already have.
            pulse = await _pulse_from_site_doc(site)
            alerts = _compute_alerts(pulse, site)
            actionable = [a for a in alerts if a["severity"] in ("warn", "critical")]
            if not actionable:
                skipped += 1
                continue

            # Find the site owner email (supports both `id` string keys and
            # legacy ObjectId `_id` primary keys).
            owner_email = None
            owner_id = site.get("owner_id") or site.get("user_id") or site.get("created_by")
            if owner_id:
                owner = await db.users.find_one({"id": owner_id}, {"_id": 0, "email": 1})
                if not owner:
                    try:
                        from bson import ObjectId
                        owner = await db.users.find_one({"_id": ObjectId(owner_id)}, {"email": 1})
                    except Exception:
                        owner = None
                if owner:
                    owner_email = owner.get("email")
            if not owner_email:
                skipped += 1
                continue

            html = _render_digest_html(site, alerts, pulse)
            subject = f"[Pulse SEO] {len(actionable)} recommandation(s) pour {site.get('name') or 'votre boutique'}"
            target = owner_email
            if RESEND_OWNER_EMAIL and owner_email.lower() != RESEND_OWNER_EMAIL.lower():
                target = RESEND_OWNER_EMAIL
                logger.info("[seo-coach] sandbox: rerouting digest for %s → %s", owner_email, target)

            resend.Emails.send({
                "from": RESEND_FROM,
                "to": [target],
                "subject": subject,
                "html": html,
            })
            await db.sites.update_one(
                {"id": site.get("id")},
                {"$set": {"design.seo_coach.last_email_sent_at": datetime.now(timezone.utc).isoformat()}},
            )
            sent += 1
        except Exception:
            logger.exception(f"[seo-coach] digest skipped for site {site.get('id')}")
            skipped += 1

    logger.info(f"[seo-coach] weekly digest: sent={sent} skipped={skipped}")
    return {"sent": sent, "skipped": skipped}


async def _pulse_from_site_doc(site: dict) -> dict:
    """Version autonome du Pulse — n'a pas besoin d'auth context.
    Reproduit exactement la logique de `seo_pulse()` dans design.py."""
    import re
    design = site.get("design") or {}
    posts = design.get("blog_posts") or []
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    posts_month = [p for p in posts if (p.get("published_at") or "").startswith(month_key)]

    covered_kws = set()
    for p in posts:
        for f in ("pillar_keyword", "satellite_keyword"):
            if p.get(f):
                covered_kws.add(str(p[f]).lower().strip())
        for v in p.get("satellite_keywords") or []:
            covered_kws.add(str(v).lower().strip())

    niche_an = design.get("niche_analysis") or {}
    info_re = re.compile(r"\b(comment|pourquoi|guide|choisir|quand|quoi|est-ce|différence|types|bienfaits|avantages|inconvénients)\b", re.I)
    total_info = 0
    for result in niche_an.get("results") or []:
        for k in result.get("keywords") or []:
            kw = (k.get("keyword") if isinstance(k, dict) else str(k)) or ""
            if info_re.search(kw):
                total_info += 1
    coverage_pct = round(min(100, (len(covered_kws) / total_info) * 100)) if total_info else 0

    from routes.design import _compute_eeat_score
    recent = sorted(posts, key=lambda p: p.get("published_at") or "", reverse=True)[:6]
    recent_scored = [{
        "slug": p.get("slug"), "title": p.get("title"),
        "eeat_score": _compute_eeat_score(p),
    } for p in recent]
    avg_eeat = round(sum(r["eeat_score"] for r in recent_scored) / len(recent_scored)) if recent_scored else 0

    bc = design.get("blog_cluster") or {}
    next_cluster = None
    if bc.get("auto_enabled"):
        if now.month == 12:
            nc = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)
        else:
            nc = now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0)
        next_cluster = nc.isoformat()

    return {
        "articles_this_month": len(posts_month),
        "articles_total": len(posts),
        "keywords_covered": len(covered_kws),
        "keywords_total_informational": total_info,
        "coverage_pct": coverage_pct,
        "recent_articles": recent_scored,
        "avg_eeat_score": avg_eeat,
        "next_cluster_at": next_cluster,
    }


# =====================================================================
# Historique hebdomadaire E-E-A-T + Badges achievements (dopamine-driven)
# =====================================================================
async def _snapshot_all_sites():
    """Pour chaque site, enregistre une photo weekly du pulse dans
    `site.design.seo_coach.weekly_snapshots` (max 52 semaines conservées).
    Attribue les badges débloqués en passant."""
    now = datetime.now(timezone.utc)
    week_key = now.strftime("%G-W%V")  # ISO week, e.g. 2026-W17
    cursor = db.sites.find({}, {"_id": 0})
    async for site in cursor:
        try:
            pulse = await _pulse_from_site_doc(site)
            coach = ((site.get("design") or {}).get("seo_coach")) or {}
            snapshots = list(coach.get("weekly_snapshots") or [])

            # Idempotence — update-in-place if same week_key already exists
            existing_idx = next(
                (i for i, s in enumerate(snapshots) if s.get("week") == week_key), None
            )
            snapshot = {
                "week": week_key,
                "ts": now.isoformat(),
                "avg_eeat_score": pulse["avg_eeat_score"],
                "articles_total": pulse["articles_total"],
                "articles_this_month": pulse["articles_this_month"],
                "coverage_pct": pulse["coverage_pct"],
                "keywords_covered": pulse["keywords_covered"],
            }
            if existing_idx is not None:
                snapshots[existing_idx] = snapshot
            else:
                snapshots.append(snapshot)
            # Cap to last 52 weeks
            snapshots = snapshots[-52:]

            # Achievements
            unlocked = list(coach.get("badges") or [])
            unlocked_ids = {b["id"] for b in unlocked}
            newly_unlocked = _check_badges(snapshots, unlocked_ids)

            update = {
                "design.seo_coach.weekly_snapshots": snapshots,
                "design.seo_coach.last_snapshot_at": now.isoformat(),
            }
            if newly_unlocked:
                update["design.seo_coach.badges"] = unlocked + newly_unlocked

            await db.sites.update_one({"id": site["id"]}, {"$set": update})
        except Exception:
            logger.exception(f"[seo-coach] snapshot failed for site {site.get('id')}")


def _check_badges(snapshots: list, already_unlocked: set) -> list:
    """Rule engine des badges d'achievement. Retourne les nouveaux débloqués.
    Chaque badge est idempotent (unlocked 1 fois, conservé à vie)."""
    if not snapshots:
        return []
    latest = snapshots[-1]
    avg = latest.get("avg_eeat_score", 0)
    arts = latest.get("articles_total", 0)
    coverage = latest.get("coverage_pct", 0)
    now_iso = datetime.now(timezone.utc).isoformat()

    candidates = [
        # Cluster d'ouverture
        ("first-cluster", arts >= 1,
         "Premier pas", "Premier cluster de contenu publié — Google a commencé à indexer.",
         "📝"),
        ("ten-articles", arts >= 10,
         "Prolifique", "10 articles publiés — vous entrez dans la zone E-E-A-T sérieuse.",
         "📚"),
        ("thirty-articles", arts >= 30,
         "Autorité installée", "30 articles — vous êtes une référence dans votre niche.",
         "🏛️"),

        # Score E-E-A-T
        ("eeat-75", avg >= 75,
         "Score pro", "Premier 75/100 E-E-A-T atteint — niveau expert.",
         "⭐"),
        ("eeat-90", avg >= 90,
         "Score élite", "Premier 90/100 E-E-A-T — top 5 % du web éditorial.",
         "🏆"),

        # Couverture keywords
        ("coverage-50", coverage >= 50,
         "Mi-marathon", "Plus de la moitié de vos keywords sont couverts.",
         "🎯"),
        ("coverage-100", coverage >= 100,
         "Cartographie complète", "100 % des keywords informationnels couverts. Chapeau.",
         "🗺️"),
    ]

    # Streak: 4 weeks consecutive >= 75
    last4 = snapshots[-4:] if len(snapshots) >= 4 else []
    if len(last4) == 4 and all((s.get("avg_eeat_score") or 0) >= 75 for s in last4):
        candidates.append((
            "streak-4w-75", True,
            "Marathonien", "4 semaines d'affilée au-dessus de 75/100 — la régularité paie.",
            "🔥",
        ))

    # 12 weeks consecutive above 75
    last12 = snapshots[-12:] if len(snapshots) >= 12 else []
    if len(last12) == 12 and all((s.get("avg_eeat_score") or 0) >= 75 for s in last12):
        candidates.append((
            "streak-12w-75", True,
            "Trimestre d'or", "12 semaines consécutives au-dessus de 75/100.",
            "🏅",
        ))

    new_badges = []
    for bid, ok, title, description, icon in candidates:
        if ok and bid not in already_unlocked:
            new_badges.append({
                "id": bid,
                "title": title,
                "description": description,
                "icon": icon,
                "unlocked_at": now_iso,
            })
    return new_badges


@router.get("/sites/{site_id}/seo/history")
async def seo_history(site_id: str, user=Depends(get_current_user)):
    """Renvoie l'historique des snapshots hebdomadaires + badges débloqués.
    Utilisé par le sparkline + la grille d'achievements dans Pulse SEO."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    coach = ((site.get("design") or {}).get("seo_coach")) or {}
    snapshots = list(coach.get("weekly_snapshots") or [])
    badges = list(coach.get("badges") or [])

    # If no snapshot yet, create one on the fly so the sparkline is not empty
    if not snapshots:
        pulse = await _pulse_from_site_doc(site)
        now = datetime.now(timezone.utc)
        live = {
            "week": now.strftime("%G-W%V"),
            "ts": now.isoformat(),
            "avg_eeat_score": pulse["avg_eeat_score"],
            "articles_total": pulse["articles_total"],
            "coverage_pct": pulse["coverage_pct"],
        }
        snapshots = [live]

    # Delta between the latest and previous snapshot for UI "momentum" indicator
    delta = 0
    if len(snapshots) >= 2:
        delta = (snapshots[-1].get("avg_eeat_score") or 0) - (snapshots[-2].get("avg_eeat_score") or 0)

    return {
        "snapshots": snapshots,
        "badges": sorted(badges, key=lambda b: b.get("unlocked_at") or "", reverse=True),
        "current_score": (snapshots[-1] if snapshots else {}).get("avg_eeat_score", 0),
        "delta_vs_last_week": delta,
        "weeks_tracked": len(snapshots),
    }


@router.post("/sites/{site_id}/seo/snapshot")
async def force_snapshot(site_id: str, user=Depends(get_current_user)):
    """Déclenche manuellement un snapshot pour ce site (test/debug)."""
    site = await db.sites.find_one({"id": site_id}, {"_id": 0})
    if not site:
        raise HTTPException(404, "Site introuvable")

    pulse = await _pulse_from_site_doc(site)
    coach = ((site.get("design") or {}).get("seo_coach")) or {}
    snapshots = list(coach.get("weekly_snapshots") or [])
    now = datetime.now(timezone.utc)
    week_key = now.strftime("%G-W%V")
    snapshot = {
        "week": week_key,
        "ts": now.isoformat(),
        "avg_eeat_score": pulse["avg_eeat_score"],
        "articles_total": pulse["articles_total"],
        "articles_this_month": pulse["articles_this_month"],
        "coverage_pct": pulse["coverage_pct"],
        "keywords_covered": pulse["keywords_covered"],
    }
    existing_idx = next(
        (i for i, s in enumerate(snapshots) if s.get("week") == week_key), None
    )
    if existing_idx is not None:
        snapshots[existing_idx] = snapshot
    else:
        snapshots.append(snapshot)
    snapshots = snapshots[-52:]

    already = {b["id"] for b in (coach.get("badges") or [])}
    new_badges = _check_badges(snapshots, already)

    update = {
        "design.seo_coach.weekly_snapshots": snapshots,
        "design.seo_coach.last_snapshot_at": now.isoformat(),
    }
    if new_badges:
        update["design.seo_coach.badges"] = (coach.get("badges") or []) + new_badges
    await db.sites.update_one({"id": site_id}, {"$set": update})

    return {"ok": True, "snapshot": snapshot, "new_badges": new_badges}

