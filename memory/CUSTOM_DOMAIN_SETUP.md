# Architecture custom domain — Altiaro (Phase 4 / Tâche 1)

> Scalable, automatique, sans intervention manuelle dans le dashboard Emergent.
> Inspirée de Vercel for SaaS / Cloudflare for SaaS, mais 100 % self-hosted.

---

## Architecture cible

```
                   Concepteur tape https://mon-shop.fr
                                  │
                                  ▼
                 ┌────────────────────────────────────┐
                 │  DNS du concepteur (OVH, automatique) │
                 │   mon-shop.fr      A     <PROXY_IP>   │
                 │   www.mon-shop.fr  CNAME proxy.altiaro.com │
                 └────────────────────────────────────┘
                                  │
                                  ▼
            ┌─────────────────────────────────────────────────┐
            │  proxy.altiaro.com   (VPS Hetzner / Scaleway, Caddy 2.7+) │
            │   - Termine TLS via Let's Encrypt (TLS-ALPN-01) │
            │   - Forward HTTPS → pod Emergent                │
            │   - Préserve le Host original via              │
            │     X-Forwarded-Host: mon-shop.fr              │
            └─────────────────────────────────────────────────┘
                                  │
                                  ▼
            ┌─────────────────────────────────────────────────┐
            │  Pod Emergent Altiaro (FastAPI)                 │
            │   - custom_domain_middleware                    │
            │   - Lit X-Forwarded-Host en priorité (puis Host)│
            │   - Réécrit /  → /shop/{site_id}/               │
            │   - Sert le storefront                          │
            └─────────────────────────────────────────────────┘
```

**Pourquoi ce design ?**

| Contrainte | Conséquence |
|---|---|
| Le pod Emergent termine TLS sur `altiaro.com` uniquement | Impossible de pointer `mon-shop.fr` directement dessus → 526 SAN mismatch |
| Emergent n'expose pas d'API publique pour ajouter un Custom Domain | Architecture précédente non scalable (action humaine par domaine) |
| Let's Encrypt rate limit = 50 certs / week / **registrable domain** | Non bloquant car chaque concepteur a son propre registrable |
| Caddy admin API permet PUT/DELETE de routes à chaud sans reload | Provisioning automatique côté Altiaro via `services/proxy_provisioning.py` |

**Coût** : VPS dédié €4-6/mois (Hetzner CX11, Scaleway DEV1-S), gratuit côté
Let's Encrypt et Caddy.

---

## 1. Provisioning du VPS Caddy (à faire 1 seule fois côté admin Altiaro)

### 1.1 Spec minimale

| Item | Valeur |
|---|---|
| vCPU | 1 (Hetzner CX11 ou Scaleway DEV1-S suffisent) |
| RAM | 1 Go |
| Disque | 20 Go SSD |
| OS | Debian 12 ou Ubuntu 22.04 |
| Caddy | 2.7+ |
| Ports ouverts | 80, 443 (Internet), 2019 (admin API — **TUNNEL SSH UNIQUEMENT**) |
| DNS | Provisionner `proxy.altiaro.com → IP_VPS` |

### 1.2 Installation Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

### 1.3 Caddyfile de base

`/etc/caddy/Caddyfile` :

```caddy
{
    # Admin API — accessible UNIQUEMENT en local (lié à 127.0.0.1).
    # Altiaro accède via SSH tunnel ou WireGuard. Jamais Internet direct.
    admin 127.0.0.1:2019
    
    # Email pour Let's Encrypt
    email admin@altiaro.com
    
    # On-demand TLS — Caddy demandera un certificat à la volée pour
    # n'importe quel hostname. PROTÉGÉ par un endpoint d'autorisation
    # qui interroge Altiaro pour vérifier que ce hostname est attendu
    # (anti-abus : sans ça, n'importe qui pourrait pointer son DNS chez
    # nous et nous faire émettre un cert pour lui).
    on_demand_tls {
        ask https://altiaro.com/api/public/domains/resolve
    }
}

# Health check du proxy lui-même
proxy.altiaro.com {
    respond "OK proxy" 200
}

# Wildcard catch-all : sert tous les domaines custom des concepteurs.
# Caddy demande automatiquement un certificat Let's Encrypt à la volée
# (mode `tls on_demand`). Le `ask` ci-dessus prévient les abus.
*.* {
    tls {
        on_demand
    }
    
    reverse_proxy https://altiaro-pod.emergentagent.com {
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto https
        header_up X-Real-IP {remote_host}
        header_up Host altiaro-pod.emergentagent.com
        transport http {
            tls
            tls_server_name altiaro-pod.emergentagent.com
        }
    }
}
```

> ⚠️ Le `on_demand_tls.ask` pointe sur **`/api/public/domains/resolve?host=...`**
> qui est déjà exposé par `backend/routes/site_domain.py:public_resolve_domain`.
> Il retourne 200 si le host est un domaine vérifié pour un site Altiaro,
> sinon 404. Caddy ne demande un cert Let's Encrypt **que si l'autorisation
> est OK**. Anti-abus parfait.

### 1.4 Démarrer

```bash
sudo systemctl enable --now caddy
sudo systemctl status caddy

# Test admin API en local
curl http://127.0.0.1:2019/config/
```

### 1.5 Tunnel SSH pour exposer l'admin API à Altiaro

Sur le pod Emergent (ou via un agent dédié), ouvrir un tunnel SSH persistant :

```bash
# Sur le pod Altiaro, ajouter dans systemd ou supervisor :
ssh -N -f -L 2019:127.0.0.1:2019 caddyadmin@proxy.altiaro.com
```

Puis dans `backend/.env` :

```bash
PROXY_ADMIN_URL=http://127.0.0.1:2019
PROXY_ADMIN_TOKEN=<si protection bearer activée>
PROXY_TARGET_POD=https://altiaro-pod.emergentagent.com
PROXY_FALLBACK_MODE=cloudflare-saas
PROXY_CADDY_SERVER_ID=srv0
```

---

## 2. Flow concepteur (étape 6 du Cockpit) — 100 % automatique

```
┌── 1. Concepteur saisit "mon-shop.fr" dans /sites/{id}/domain
│
├── 2. POST /api/sites/{id}/domain
│      → Persist `custom_domain` dans Mongo
│
├── 3. POST /api/sites/{id}/domain/verify
│      → DNS check (CNAME / A) côté Altiaro
│      → Si OK : `custom_domain_verified = true`
│      → AUTOMATIQUEMENT : services.proxy_provisioning.add_domain(domain)
│         qui appelle Caddy admin API :
│            PUT http://127.0.0.1:2019/id/altiaro_route_mon_shop_fr
│            { match: [{host: ["mon-shop.fr", "www.mon-shop.fr"]}],
│              handle: [{handler: "reverse_proxy", upstreams: ...}] }
│      → Caddy ajoute la route à chaud (latence <500ms, pas de reload)
│
├── 4. Concepteur clique "Visiter ma boutique"
│      → DNS résout vers IP du proxy
│      → Caddy reçoit la requête HTTPS
│      → Si premier visiteur : on_demand_tls → ask → Altiaro 200 → cert émis
│      → Caddy forward au pod Emergent avec X-Forwarded-Host: mon-shop.fr
│      → custom_domain_middleware résout site_id → réécrit path → storefront
│
└── 5. Site live, sans aucune intervention humaine plateforme.
```

Implémentation côté code :

| Couche | Fichier | Rôle |
|---|---|---|
| Middleware FastAPI | `backend/custom_domain_middleware.py` | Lit `X-Forwarded-Host` (priorité) puis `Host`, route vers `/shop/{site_id}` |
| Service provisioning | `backend/services/proxy_provisioning.py` | Client Caddy admin API : `add_domain`, `remove_domain`, `domain_status` |
| Hook étape 6 | `backend/routes/site_domain.py:verify_custom_domain` | Provisionne automatiquement après vérif DNS OK |
| Endpoints admin | `POST /api/admin/sites/{id}/domain/proxy-add` | Force re-provisioning manuel (utilisé pour Altea aujourd'hui) |
| Endpoints admin | `DELETE /api/admin/sites/{id}/domain/proxy-remove` | Retire un domaine du proxy |
| Endpoint anti-abus | `GET /api/public/domains/resolve?host=X` | Caddy interroge cet endpoint avant d'émettre un cert |

---

## 3. Plan de migration — Altea (`altea-home.com`)

Une fois le VPS Caddy provisionné :

```bash
# 1. Migrer le DNS OVH d'altea-home.com
#    A / @ → IP_DU_PROXY  (au lieu de IP du pod Emergent)
#    CNAME / www → proxy.altiaro.com

# 2. Forcer le provisioning sur Caddy via l'endpoint admin
curl -X POST -H "Cookie: access_token=$ADMIN_JWT" \
  https://altiaro.com/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/domain/proxy-add

# 3. Vérifier que le cert est émis (peut prendre 5-30 s la première fois)
curl -I https://altea-home.com/

# 4. Retirer altea-home.com des Custom Domains Emergent (si déclaré)
```

---

## 4. Multi-concepteurs : capacités

| Volumétrie | Capacité Caddy | Action |
|---|---|---|
| 1-100 sites/mois | OK natif | Aucune |
| 100-1 000 sites/mois | OK natif | Surveiller logs Let's Encrypt |
| 1 000-5 000 sites/mois | OK natif | Augmenter VPS à 2 vCPU / 2 Go |
| > 5 000 sites/mois | Cluster Caddy ou Cloudflare for SaaS | Voir §5 |

> Le throughput d'un VPS €4/mois est largement suffisant pour 10 sites/jour
> = 300/mois. La marge avant le prochain palier est colossale.

---

## 5. Plan de repli si Caddy ne tient pas

### 5.1 Cloudflare for SaaS (Custom Hostnames)

- API publique : `https://api.cloudflare.com/client/v4/zones/{zone}/custom_hostnames`
- Coût : ~$2/mois/host au-delà de 100 hosts (Plan Pro requis ~$25/mois).
- Avantage : SLA 99.9 %, scaling automatique, anti-DDoS gratuit.
- Inconvénient : payant et lock-in.
- Switch : `PROXY_FALLBACK_MODE=cloudflare-saas` dans `.env`, alors
  `proxy_provisioning.add_domain()` retournera l'erreur fallback que la
  couche admin pourra dispatcher vers un autre service `cf_saas_provisioning.py`.

### 5.2 nginx + acme.sh (script bash)

- Plus low-tech : un script `add-host.sh mon-shop.fr` qui ajoute un
  `server { listen 443; server_name mon-shop.fr; ... }` puis
  `acme.sh --issue -d mon-shop.fr --webroot ...` puis `nginx -s reload`.
- Inconvénient : reload nginx à chaque ajout (latence ~500 ms, pas de hot config).
- Avantage : tooling très mature.

### 5.3 Caddy en mode "on-demand TLS pure" (sans admin API)

- Garder le `*.*` catch-all + `on_demand_tls`, ne JAMAIS appeler l'admin API.
- Caddy détecte les nouveaux Host et émet les certs à la volée.
- Inconvénient : aucun contrôle préalable sur les domaines acceptés
  (mais le `ask` côté Altiaro prévient déjà les abus).
- **C'est en fait ce qui est implémenté avec le Caddyfile §1.3 ci-dessus.**
  L'admin API est un bonus pour le tracking et l'invalidation, mais le
  système marche sans.

→ Conclusion : **on peut démarrer en mode pure on-demand sans admin API**,
et activer l'admin API plus tard pour le tracking fin sans changement
côté concepteur.

---

## 6. Checklist de mise en service

### Côté admin Altiaro (1 fois) :

- [ ] Provisionner VPS €4/mois avec IP statique
- [ ] Pointer `proxy.altiaro.com → IP_VPS` (DNS Altiaro)
- [ ] Installer Caddy 2.7+ + ce Caddyfile
- [ ] Démarrer Caddy, vérifier `https://proxy.altiaro.com → "OK proxy"`
- [ ] (Optionnel mais recommandé) Tunnel SSH pour exposer admin API au pod
- [ ] Renseigner `PROXY_ADMIN_URL`, `PROXY_TARGET_POD`, `PROXY_ADMIN_TOKEN` dans `backend/.env`
- [ ] Restart backend

### Côté concepteur (à chaque site) — 100 % automatique :

- [ ] Saisir le domaine étape 6
- [ ] Cliquer "Vérifier propriétaire"
- [ ] (Le système configure tout : DNS OVH + Caddy provisioning + cert)
- [ ] Visiter le site → 🟢

---

## 7. Endpoints API ajoutés

```
POST   /api/admin/sites/{site_id}/domain/proxy-add      [admin]
       → force le provisioning Caddy d'un domaine déjà persisté
       
DELETE /api/admin/sites/{site_id}/domain/proxy-remove   [admin]
       → retire un domaine du proxy

(déjà existant, utilisé par Caddy on_demand_tls.ask)
GET    /api/public/domains/resolve?host=mon-shop.fr
       → 200 + {site_id, site_name, host} si vérifié, 404 sinon
```

---

*Mise à jour : 2026-05-01 — Phase 4 / Tâche 1 livrée*
