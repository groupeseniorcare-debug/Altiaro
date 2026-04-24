"""
Resend · DNS bootstrap helper (Phase 6).

Endpoint admin qui prend les enregistrements DNS fournis par Resend Dashboard
(SPF, DKIM, DMARC) et les crée automatiquement dans la zone OVH du domaine,
puis rafraîchit la zone. L'user n'a plus qu'à cliquer "Verify" sur resend.com
après ~5 minutes de propagation.

Flow attendu :
1. User va sur resend.com/domains/add → ajoute `altiaro.com`
2. Resend affiche 3-5 enregistrements DNS à ajouter
3. User copie chaque record et POST /api/admin/resend/verify-domain avec
   la liste (nom, type, valeur, priorité si MX)
4. Cette route pousse les records via OVH API dans la zone DNS du domaine
5. Resend vérifie automatiquement ~5-15 min plus tard

IMPORTANT : le domaine cible doit déjà exister dans la zone OVH du compte
plateforme (acheté via /api/domains/purchase ou déjà présent). Sinon OVH
renvoie 404 ResourceNotFoundError.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

import ovh
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/resend", tags=["admin-resend"])


class ResendDNSRecord(BaseModel):
    """1 enregistrement DNS fourni par Resend (TXT, CNAME, MX)."""
    type: Literal["TXT", "CNAME", "MX"] = Field(..., description="Type DNS")
    name: str = Field(
        ...,
        description=(
            "Nom du sous-domaine relatif à altiaro.com, sans TLD. "
            "Exemples : '', 'send', 'resend._domainkey', '_dmarc'."
        ),
    )
    value: str = Field(..., description="Valeur du record (chaîne brute)")
    priority: Optional[int] = Field(None, description="Priorité MX (10, 20, …)")
    ttl: int = Field(300, description="TTL en secondes (défaut 300 = 5 min)")


class VerifyDomainInput(BaseModel):
    domain: str = Field(..., description="Domaine cible, ex : altiaro.com")
    records: list[ResendDNSRecord] = Field(
        default_factory=list,
        description="Liste des records fournis par Resend Dashboard",
    )


def _ovh_client() -> ovh.Client:
    import os
    key = os.environ.get("OVH_APP_KEY", "").strip()
    secret = os.environ.get("OVH_APP_SECRET", "").strip()
    consumer = os.environ.get("OVH_CONSUMER_KEY", "").strip()
    endpoint = os.environ.get("OVH_ENDPOINT", "ovh-eu").strip() or "ovh-eu"
    if not (key and secret and consumer):
        raise HTTPException(503, "OVH credentials manquants dans .env")
    return ovh.Client(
        endpoint=endpoint,
        application_key=key,
        application_secret=secret,
        consumer_key=consumer,
    )


@router.post("/verify-domain")
async def verify_resend_domain(
    data: VerifyDomainInput = Body(...),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Pousse les records DNS Resend dans la zone OVH + refresh la zone.

    Renvoie un détail record-par-record (ok / already_exists / error).
    Idempotent : si un record identique existe déjà, on skip proprement.
    """
    domain = (data.domain or "").strip().lower()
    if not domain:
        raise HTTPException(400, "domain requis")
    if not data.records:
        raise HTTPException(400, "Au moins 1 record DNS requis")

    client = _ovh_client()

    # Vérifier que la zone OVH existe pour ce domaine.
    try:
        await asyncio.to_thread(client.get, f"/domain/zone/{domain}")
    except ovh.exceptions.ResourceNotFoundError:
        raise HTTPException(
            404,
            f"Zone OVH introuvable pour {domain}. "
            "Le domaine doit être sur le compte OVH plateforme.",
        )
    except ovh.exceptions.APIError as e:
        raise HTTPException(502, f"OVH API : {str(e)[:200]}")

    # Lister les records existants pour détecter les doublons
    try:
        existing_ids = await asyncio.to_thread(
            client.get, f"/domain/zone/{domain}/record"
        ) or []
    except Exception:
        existing_ids = []

    existing_records: list[dict] = []
    for rid in existing_ids[:500]:
        try:
            rec = await asyncio.to_thread(
                client.get, f"/domain/zone/{domain}/record/{rid}"
            )
            if rec:
                existing_records.append(rec)
        except Exception:
            continue

    def _already_exists(new: ResendDNSRecord) -> bool:
        for r in existing_records:
            if (
                r.get("fieldType") == new.type
                and (r.get("subDomain") or "") == new.name
                and (r.get("target") or "").strip().strip('"')
                == new.value.strip().strip('"')
            ):
                return True
        return False

    results: list[dict] = []
    created = 0
    skipped = 0
    errored = 0

    for rec in data.records:
        entry = {"name": rec.name, "type": rec.type}
        try:
            if _already_exists(rec):
                entry["status"] = "already_exists"
                skipped += 1
                results.append(entry)
                continue

            payload = {
                "fieldType": rec.type,
                "subDomain": rec.name,
                "target": rec.value,
                "ttl": rec.ttl,
            }
            # Pour les MX, OVH veut le target au format "<priority> <host>."
            if rec.type == "MX" and rec.priority is not None:
                payload["target"] = f"{rec.priority} {rec.value.rstrip('.')}."

            await asyncio.to_thread(
                client.post, f"/domain/zone/{domain}/record", **payload
            )
            entry["status"] = "created"
            created += 1
        except ovh.exceptions.APIError as e:
            entry["status"] = "error"
            entry["error"] = str(e)[:200]
            errored += 1
            logger.warning(f"[resend-dns] {rec.type} {rec.name} failed: {e}")
        results.append(entry)

    # Refresh zone pour appliquer les changements
    try:
        await asyncio.to_thread(client.post, f"/domain/zone/{domain}/refresh")
        refreshed = True
    except Exception as e:
        refreshed = False
        logger.warning(f"[resend-dns] zone refresh failed: {e}")

    # Persist log
    try:
        await db.resend_dns_operations.insert_one({
            "domain": domain,
            "records_input": [r.model_dump() for r in data.records],
            "results": results,
            "created": created,
            "skipped": skipped,
            "errored": errored,
            "refreshed": refreshed,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "executed_by": _admin.get("id", "admin"),
        })
    except Exception:
        pass

    logger.info(
        f"[resend-dns] domain={domain} created={created} "
        f"skipped={skipped} errored={errored} refreshed={refreshed}"
    )

    return {
        "ok": errored == 0,
        "domain": domain,
        "records": results,
        "summary": {
            "created": created,
            "already_exists": skipped,
            "errored": errored,
            "zone_refreshed": refreshed,
        },
        "next_step": (
            "Les records DNS ont été publiés. Attendez 5-15 min puis cliquez "
            "sur 'Verify DNS records' dans https://resend.com/domains."
        ),
    }


@router.get("/domain-status")
async def get_resend_domain_status(_admin: dict = Depends(require_admin)) -> dict:
    """Statut du dernier bootstrap DNS (pour UI future)."""
    last = await db.resend_dns_operations.find_one(
        {}, {"_id": 0}, sort=[("executed_at", -1)]
    )
    return {"last_operation": last}
