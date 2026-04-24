"""
setup_platform_dns.py
=====================
Crée (ou vérifie) le A-record `sites.altiaro.com` → {PLATFORM_SITE_IP} sur OVH.

Utilise l'API OVH avec les creds en env (OVH_APP_KEY / OVH_APP_SECRET /
OVH_CONSUMER_KEY / OVH_ENDPOINT). Idempotent : ne remplace jamais un record
existant qui pointe vers une autre IP sans confirmation explicite.

Usage (depuis /app/backend) :
    python -m scripts.setup_platform_dns

En cas de changement d'IP prod, mettre à jour PLATFORM_SITE_IP dans .env puis
re-lancer ce script.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Charge .env backend
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    import ovh  # type: ignore
except ImportError:
    print("[ERR] Package `ovh` non installé. pip install ovh")
    sys.exit(1)


# --- Config --------------------------------------------------------------
ZONE = "altiaro.com"
SUBDOMAIN = "sites"          # donne sites.altiaro.com
RECORD_TYPE = "A"
TTL = 300                     # 5 min
TARGET_IP = os.environ.get("PLATFORM_SITE_IP", "").strip()

OVH_ENDPOINT = os.environ.get("OVH_ENDPOINT", "ovh-eu")
OVH_APP_KEY = os.environ.get("OVH_APP_KEY", "").strip()
OVH_APP_SECRET = os.environ.get("OVH_APP_SECRET", "").strip()
OVH_CONSUMER_KEY = os.environ.get("OVH_CONSUMER_KEY", "").strip()


# --- Helpers -------------------------------------------------------------
def _ovh_client() -> "ovh.Client":
    if not all([OVH_APP_KEY, OVH_APP_SECRET, OVH_CONSUMER_KEY]):
        print("[ERR] Creds OVH manquants dans .env")
        sys.exit(1)
    return ovh.Client(
        endpoint=OVH_ENDPOINT,
        application_key=OVH_APP_KEY,
        application_secret=OVH_APP_SECRET,
        consumer_key=OVH_CONSUMER_KEY,
    )


def _redact_ck(ck: str) -> str:
    if not ck:
        return "(empty)"
    return f"{ck[:6]}…{ck[-4:]}"


# --- Main ----------------------------------------------------------------
def main() -> int:
    print("=" * 70)
    print("  Altiaro — Setup DNS platform sub-domain via OVH API")
    print("=" * 70)
    print(f"  Endpoint      : {OVH_ENDPOINT}")
    print(f"  Application   : {OVH_APP_KEY[:8] + '…' if OVH_APP_KEY else '(missing)'}")
    print(f"  Consumer key  : {_redact_ck(OVH_CONSUMER_KEY)}")
    print(f"  Zone          : {ZONE}")
    print(f"  Record        : {SUBDOMAIN}.{ZONE}  →  {TARGET_IP} ({RECORD_TYPE}, TTL={TTL})")
    print()

    if not TARGET_IP:
        print("[ERR] PLATFORM_SITE_IP vide dans .env — abandon.")
        return 1

    client = _ovh_client()

    # 1. Vérifier que la zone existe bien sur le compte
    print("[1/5] Vérification de la zone dans le compte OVH…")
    try:
        zones = client.get("/domain/zone")
    except ovh.exceptions.APIError as e:
        print(f"[ERR] API OVH : {e}")
        print("      → Permission manquante ou Consumer Key expirée ?")
        print("      → Scope requis : GET /domain/zone, GET/POST/DELETE /domain/zone/*/record*")
        return 2

    if ZONE not in zones:
        print(f"[ERR] La zone `{ZONE}` n'est pas visible depuis ce compte OVH.")
        print(f"      Zones accessibles : {zones}")
        return 3
    print(f"      ✓ Zone `{ZONE}` trouvée")

    # 2. Chercher les records existants pour le sous-domaine
    print(f"[2/5] Recherche de records {RECORD_TYPE} existants sur `{SUBDOMAIN}.{ZONE}`…")
    try:
        record_ids = client.get(
            f"/domain/zone/{ZONE}/record",
            fieldType=RECORD_TYPE,
            subDomain=SUBDOMAIN,
        )
    except ovh.exceptions.APIError as e:
        print(f"[ERR] Lecture records : {e}")
        return 4

    existing_by_target: dict[str, int] = {}
    for rid in record_ids:
        try:
            rec = client.get(f"/domain/zone/{ZONE}/record/{rid}")
            existing_by_target[rec.get("target", "")] = rid
        except ovh.exceptions.APIError:
            continue

    print(f"      {len(existing_by_target)} record(s) existant(s) : {list(existing_by_target.keys()) or '(aucun)'}")

    # 3. Décision
    print("[3/5] Décision…")
    if TARGET_IP in existing_by_target:
        print(f"      ✓ Record déjà présent et pointe vers {TARGET_IP}. Rien à faire.")
        return 0

    if existing_by_target and TARGET_IP not in existing_by_target:
        # Des records existent mais vers une autre IP → on ne touche PAS sans confirmation.
        print("      ⚠ Des records A existent déjà mais pointent vers une autre IP :")
        for ip, rid in existing_by_target.items():
            print(f"         - id={rid} target={ip}")
        print(f"      → Ne sera PAS écrasé automatiquement. Target attendu : {TARGET_IP}.")
        print("      → Pour forcer la mise à jour, supprime ces records dans OVH Manager")
        print("        ou ajoute un flag --force à ce script (non implémenté volontairement).")
        return 5

    # 4. Créer le record
    print(f"[4/5] Création du record A `{SUBDOMAIN}.{ZONE}` → {TARGET_IP} (TTL={TTL})…")
    try:
        created = client.post(
            f"/domain/zone/{ZONE}/record",
            fieldType=RECORD_TYPE,
            subDomain=SUBDOMAIN,
            target=TARGET_IP,
            ttl=TTL,
        )
        print(f"      ✓ Record créé : id={created.get('id')}")
    except ovh.exceptions.APIError as e:
        print(f"[ERR] Création record : {e}")
        return 6

    # 5. Refresh de la zone
    print(f"[5/5] Refresh de la zone `{ZONE}`…")
    try:
        client.post(f"/domain/zone/{ZONE}/refresh")
        print("      ✓ Zone refresh demandé (propagation 1-5 min)")
    except ovh.exceptions.APIError as e:
        print(f"[WARN] Refresh : {e}")
        print("       Le record est créé mais la zone peut mettre plus de temps à propager.")

    print()
    print("=" * 70)
    print(f"  ✅ SUCCÈS : {SUBDOMAIN}.{ZONE} → {TARGET_IP}")
    print("=" * 70)
    print("  Vérifier la propagation dans 1-5 min avec :")
    print(f"    dig {SUBDOMAIN}.{ZONE} +short")
    print(f"    getent hosts {SUBDOMAIN}.{ZONE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
