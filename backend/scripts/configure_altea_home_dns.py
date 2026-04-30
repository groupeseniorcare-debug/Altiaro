"""
Configure DNS OVH pour altea-home.com → pod Emergent.

Usage : `python backend/scripts/configure_altea_home_dns.py`

Stratégie : remplacer le record A apex (104.18.11.243 = IP figée Cloudflare
posée on ne sait quand par qui) par un CNAME apex vers le hostname stable
du pod preview Emergent `commerce-builder-21.preview.emergentagent.com`.

OVH support : OVH accepte **CNAME apex** quand il n'y a pas de conflit
(pas d'A ni de MX sur la racine). Comme `altea-home.com` a des MX (OVH
webmail), le CNAME apex sera refusé par OVH. Fallback : garder A apex
mais le pointer vers une IP ; le vrai bloqueur est côté Cloudflare SNI,
pas côté DNS OVH.

Ce script diagnostique et applique la meilleure config possible côté OVH.
Le bug "https://altea-home.com timeout" sera résolu côté Cloudflare/Emergent
(déclaration du hostname dans le compte qui termine le TLS).
"""
from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / "backend" / ".env")

import ovh  # noqa: E402

DOMAIN = "altea-home.com"
POD_HOSTNAME = "commerce-builder-21.preview.emergentagent.com"

# Records qu'on veut garder intacts (MX, SPF, NS, CNAME ftp).
KEEP_TYPES_ON_APEX = {"NS", "MX", "SPF", "TXT", "DKIM", "CAA"}
# Records à reconfigurer : A apex + CNAME www.
TARGETS_TO_RESET = [("A", ""), ("CNAME", ""), ("AAAA", ""), ("A", "www"), ("CNAME", "www"), ("AAAA", "www")]


def main():
    endpoint = os.getenv("OVH_ENDPOINT") or "ovh-eu"
    app_key = os.getenv("OVH_APP_KEY")
    app_secret = os.getenv("OVH_APP_SECRET")
    consumer_key = os.getenv("OVH_CONSUMER_KEY")
    if not all([app_key, app_secret, consumer_key]):
        print("❌ Clés OVH manquantes dans backend/.env")
        sys.exit(1)

    client = ovh.Client(
        endpoint=endpoint,
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )

    # 0) Zone présente ?
    zones = client.get("/domain/zone")
    if DOMAIN not in zones:
        print(f"❌ {DOMAIN} absent du compte OVH (zones disponibles : {zones})")
        sys.exit(2)
    print(f"✓ Zone {DOMAIN} trouvée sur le compte OVH")

    # 1) Snapshot des records actuels
    record_ids = client.get(f"/domain/zone/{DOMAIN}/record")
    records = []
    for rid in record_ids:
        d = client.get(f"/domain/zone/{DOMAIN}/record/{rid}")
        records.append({
            "id": rid,
            "type": d.get("fieldType"),
            "sub": d.get("subDomain", ""),
            "target": d.get("target"),
            "ttl": d.get("ttl"),
        })
    print(f"\n📋 {len(records)} records actuels :")
    for r in records:
        print(f"  [{r['id']}] {r['type']:6s} sub={r['sub']!r:10s} → {r['target']}  ttl={r['ttl']}")

    # 2) Résolution de l'IP cible (pour A record si CNAME apex refusé)
    try:
        target_ip = socket.gethostbyname(POD_HOSTNAME)
        print(f"\n🌐 {POD_HOSTNAME} résout vers {target_ip}")
    except Exception as e:
        print(f"❌ Impossible de résoudre {POD_HOSTNAME} : {e}")
        sys.exit(3)

    # 3) Nettoyage ciblé : A / AAAA / CNAME sur apex et www
    removed = []
    for r in records:
        key = (r["type"], r["sub"])
        if key in TARGETS_TO_RESET:
            try:
                client.delete(f"/domain/zone/{DOMAIN}/record/{r['id']}")
                removed.append(f"{r['type']} {r['sub'] or '@'} → {r['target']}")
            except ovh.exceptions.APIError as e:
                print(f"  ⚠️  delete {r['id']} ({r['type']} {r['sub']}) failed: {e}")
    print(f"\n🗑️  {len(removed)} record(s) supprimé(s) :")
    for rm in removed:
        print(f"  - {rm}")

    # 4) Création des nouveaux records
    created = []

    # 4a) Apex : tenter CNAME (fallback A si refusé)
    try:
        client.post(
            f"/domain/zone/{DOMAIN}/record",
            fieldType="CNAME",
            subDomain="",
            target=f"{POD_HOSTNAME}.",
            ttl=300,
        )
        created.append(f"CNAME @ → {POD_HOSTNAME}.")
        print(f"✓ CNAME apex → {POD_HOSTNAME}. créé")
    except ovh.exceptions.APIError as e:
        print(f"⚠️  CNAME apex refusé par OVH ({e}) — fallback A record IP")
        try:
            client.post(
                f"/domain/zone/{DOMAIN}/record",
                fieldType="A",
                subDomain="",
                target=target_ip,
                ttl=300,
            )
            created.append(f"A @ → {target_ip} (ex {POD_HOSTNAME})")
            print(f"✓ A apex → {target_ip} (IP résolue de {POD_HOSTNAME}) créé")
        except Exception as e2:
            print(f"❌ Impossible de créer A apex : {e2}")

    # 4b) www : CNAME vers apex (standard)
    try:
        client.post(
            f"/domain/zone/{DOMAIN}/record",
            fieldType="CNAME",
            subDomain="www",
            target=f"{POD_HOSTNAME}.",
            ttl=300,
        )
        created.append(f"CNAME www → {POD_HOSTNAME}.")
        print(f"✓ CNAME www → {POD_HOSTNAME}. créé")
    except Exception as e:
        print(f"⚠️  CNAME www : {e}")

    # 5) Refresh zone (push du plan OVH vers les NS publics)
    client.post(f"/domain/zone/{DOMAIN}/refresh")
    print(f"\n🔄 Zone {DOMAIN} refreshed sur dns109.ovh.net / ns109.ovh.net")
    print(f"   Propagation : 5-30 min (TTL=300s)")

    print(f"\n✅ Reconfiguration OVH terminée. {len(created)} nouveau(x) record(s) :")
    for c in created:
        print(f"   + {c}")
    print("\n⏳ Attente 10 s avant test DNS...")
    time.sleep(10)

    # 6) Validation
    print("\n─── VALIDATION ───")
    try:
        import dns.resolver
        for rtype in ["A", "CNAME", "NS"]:
            try:
                ans = dns.resolver.resolve(DOMAIN, rtype)
                print(f"  {rtype:6s} : {[r.to_text() for r in ans]}")
            except Exception as e:
                print(f"  {rtype:6s} : (aucun — {type(e).__name__})")
    except ImportError:
        pass

    print(f"\n👉 Teste maintenant : curl -I http://{DOMAIN}/   (SSL vient après)")


if __name__ == "__main__":
    main()
