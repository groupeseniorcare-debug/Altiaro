# Architecture custom domain — Altiaro

> **Solution actuelle : [Approximated.app](https://approximated.app)** (depuis 2026-05-01).
> Reverse-proxy + SSL Let's Encrypt automatique, cluster IP dédié, sans VPS à
> provisionner. Les solutions précédentes (Cloudflare for SaaS, Caddy auto-hébergé)
> ont été abandonnées et leur code retiré.

---

## 🎯 Vue d'ensemble (30 secondes)

```
Concepteur saisit mon-shop.fr (étape 6 du Cockpit)
    ↓
POST /api/sites/{id}/domain/verify   (hook étape 6)
    ↓ A) Approximated   : POST /api/vhosts (incoming=mon-shop.fr, target=POD)
    ↓ B) OVH DNS         : delete A/AAAA/CNAME @ + www  →  add A @ + www → 213.188.213.253
    ↓ C) OVH refresh zone
    ↓ D) Background poller (60s × 15 min)
    ↓                     ↳ marque le site verified dès apx_hit && resolving && ssl
    ↓ E) Approximated cluster émet le cert Let's Encrypt en 30-90 s
    ↓
Visiteur tape mon-shop.fr
    → Approximated reçoit, termine TLS, forward au pod Emergent (Host préservé)
    → custom_domain_middleware route /shop/{site_id}/
    → Storefront servi
```

**Aucune action manuelle pour le concepteur.** Le DNS OVH est poussé via API,
le vhost Approximated créé via API, le SSL géré par Approximated.

---

## 1. Setup unique côté admin Altiaro (10 min)

### 1.1 Compte Approximated
1. https://approximated.app → S'inscrire (~6 €/mois pour le plan de base)
2. **Create a Proxy Cluster** (1er cluster gratuit dans le plan).
   Le cluster reçoit une **IPv4 dédiée** (ex : `213.188.213.253`).
3. **Settings → Cluster** :
   - `Keep Host Headers` : laisser à False (par défaut). Approximated injecte
     `Apx-Incoming-Host` à chaque requête, déjà géré par
     `backend/custom_domain_middleware.py`.
   - `Send X-Forwarded-Host` : True (recommandé).

### 1.2 API Key
1. **Dashboard → API Keys → Create Key**
2. Copier la valeur dans `APPROXIMATED_API_KEY` ci-dessous.

### 1.3 Renseigner `backend/.env`
```bash
APPROXIMATED_API_KEY=<ta_clé>
APPROXIMATED_TARGET_HOST=commerce-builder-21.preview.emergentagent.com
APPROXIMATED_TARGET_PORT=443
APPROXIMATED_CLUSTER_IPS=213.188.213.253     # IP du cluster (visible dashboard)
```

`APPROXIMATED_CLUSTER_IPS` est utilisé pour pousser les A records OVH même
quand on ne veut pas re-créer un vhost juste pour récupérer l'IP.

### 1.4 Restart backend
```bash
sudo supervisorctl restart backend
```

C'est tout côté plateforme. Le concepteur n'a plus rien à toucher.

---

## 2. Flow concepteur (100 % automatique)

À l'étape 6 du Cockpit, quand le concepteur clique « Vérifier » :

| Couche | Code | Action |
|---|---|---|
| Frontend | `cockpit/DomainModal.jsx` | POST `/api/sites/{id}/domain/verify` |
| Backend  | `routes/site_domain.py:_provision_approximated` | Orchestrateur |
| Backend  | `services/approximated_provisioning.py:create_vhost` | POST cloud.approximated.app |
| Backend  | `services/ovh_dns.py:replace_with_a_records` | DELETE+POST records OVH |
| Backend  | `services/ovh_dns.py:refresh_zone` | POST /domain/zone/.../refresh |
| Backend  | `routes/site_domain.py:_poll_until_ready` | Poller 60s × 15 min |
| Approximated | — | Émet le cert Let's Encrypt (30-90 s) |
| Frontend | poll `/api/admin/sites/{id}/domain/approximated-status` | UI passe en vert |

---

## 3. API Altiaro exposée

```
POST   /api/sites/{id}/domain/verify                              [user]
       Hook étape 6 — provisioning Approximated + OVH DNS, lance le poller.

POST   /api/admin/sites/{id}/domain/approximated-provision        [admin]
       Force re-provisioning (utile pour Altea / migrations).

GET    /api/admin/sites/{id}/domain/approximated-status?force=1   [admin]
       Statut détaillé (apx_hit, is_resolving, has_ssl, dns_pointed_at, status).

GET    /api/public/domains/resolve?host=X                         [public]
       Anti-abus / résolution custom domain → site_id (storefront).
```

Le service `approximated_provisioning.py` expose aussi :
- `create_vhost(domain, target=...)` (idempotent, gère 422 « already exists »)
- `get_vhost_status(domain, force_check=False)`
- `delete_vhost(domain)`
- `get_dns_targets(probe_domain=None)` → cluster IPs cachées

---

## 4. Migration `altea-home.com` (rappel — fait le 2026-05-01)

```bash
# Login admin
curl -s -c /tmp/c.txt -X POST https://altiaro.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@conceptfactory.fr","password":"<…>"}'

# Trigger provisioning
curl -s -b /tmp/c.txt -X POST \
  https://altiaro.com/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/domain/approximated-provision \
  | jq

# Poll status
curl -s -b /tmp/c.txt \
  https://altiaro.com/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/domain/approximated-status?force=1 \
  | jq
```

Vérifications externes :
```bash
curl -I https://altea-home.com/api/health        # 200 attendu
curl -IL https://altea-home.com/legal/mentions   # 200 attendu
echo | openssl s_client -servername altea-home.com -connect altea-home.com:443 2>/dev/null \
  | grep -E "subject=|issuer="
# subject=CN = altea-home.com
# issuer=C = US, O = Let's Encrypt, CN = E8
```

---

## 5. Limitations honnêtes

| Limite | Workaround |
|---|---|
| Plan Approximated payant ~6 €/mois pour le cluster initial | OK pour la plateforme (1 cluster partagé entre tous les concepteurs) |
| 1 cluster IP unique pour tous les domaines | Si bloqué, créer un 2e cluster (extra-coût) ou activer LB multi-IP côté Approximated |
| Concepteur DOIT pointer DNS sur Altiaro | Géré automatiquement via OVH API quand le domaine est acheté via Altiaro |
| Domaine non OVH | `_provision_approximated` skip OVH push, l'utilisateur doit pointer manuellement (UI affiche les instructions) |

---

## 6. Subdomain `www`

Pour chaque domaine apex, on crée automatiquement les A records `www`
côté OVH. Si l'on veut aussi un vhost dédié (cert SSL séparé pour `www`),
on peut soit :
- Activer `redirect_www: true` au moment de `create_vhost` (déjà le cas),
  Approximated crée alors un 2e vhost avec un 301 vers l'apex (sans
  facturation supplémentaire).
- Ou créer un vhost manuel avec `redirect: true` et `target_address: https://apex.com`.

---

## 7. Troubleshooting

| Symptôme | Cause probable | Fix |
|---|---|---|
| `https://domain/` retourne 526 / SSL error | Cert pas encore émis (délai ~30-90 s) | Attendre. `force_check=true` peut accélérer la détection. |
| `apx_hit=false, dns_pointed_at=ancienne_IP` | DNS pas encore propagé | TTL 300 s + résolveur. Patience max 15 min. |
| `dns_pointed_at` montre l'IP cluster mais `apx_hit=false` | Le monitor d'Approximated est en cache | Hit `force-check` endpoint OU attendre prochain cycle. |
| OVH `Code 401` lors du push DNS | `OVH_CONSUMER_KEY` expirée | Re-générer via `python -c "import ovh; ovh.Client(...).request_consumerkey(...)"` |
| Vhost `422 already been created` | Idempotence — gérée par `create_vhost`, qui retombe sur `get_vhost_status` | Aucune action |

---

## 8. Anciennes architectures (archive)

- **Cloudflare for SaaS** (testée mars-avril 2026) : Free tier limité, SSL
  for SaaS payant, complexité de setup. Code retiré le 2026-05-01.
- **Caddy auto-hébergé** (esquissé) : nécessitait un VPS dédié, pas scalable
  rapidement. Code retiré.

Voir `memory/CHANGELOG.md` pour la chronologie complète.
