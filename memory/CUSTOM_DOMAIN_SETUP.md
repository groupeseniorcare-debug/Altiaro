# Architecture custom domain — Altiaro

> **Solution adoptée : Cloudflare for SaaS**. 100 hostnames gratuits, SSL
> automatique, scalable. Aucun VPS à provisionner.

---

## 🎯 Vue d'ensemble (30 secondes)

```
Concepteur achète mon-shop.fr (OVH)
    ↓
Étape 6 du Cockpit (auto)
    ↓ A) DNS OVH      : CNAME mon-shop.fr → altiaro.com
    ↓ B) Cloudflare API : POST /zones/{ZONE}/custom_hostnames
    ↓ C) Cloudflare émet le cert SSL en 30-60 s
    ↓
Visiteur tape mon-shop.fr
    → CF reçoit, termine TLS, forward au pod Emergent (Host préservé)
    → custom_domain_middleware route vers /shop/{site_id}/
    → Storefront servi
```

**Aucun VPS, aucune action manuelle Emergent par concepteur.**

---

## 1. Setup unique côté admin Altiaro (10 min)

### 1.1 Compte Cloudflare gratuit
1. https://cloudflare.com/sign-up
2. Add a Site → choisir le domaine racine (recommandé : `altiaro.shop`
   acheté chez OVH puis NS bascule vers Cloudflare ; ou `altiaro.com` si
   tu acceptes de migrer ses NS).

### 1.2 Activer Cloudflare for SaaS
1. Dans le dashboard de la zone : `SSL/TLS` → `Custom Hostnames`
2. Configurer le **Fallback Origin** : `altiaro.com` (ton pod Emergent)
3. Le fallback origin doit être **proxied** dans Cloudflare. Si Emergent
   sert déjà le pod via Cloudflare, on peut faire pointer le fallback
   vers le hostname public Emergent direct (`*.preview.emergentagent.com`
   ou ton domaine de prod).

### 1.3 API Token
1. https://dash.cloudflare.com/profile/api-tokens → Create Token
2. Permissions :
   - **Zone:Custom Hostnames:Edit** ← obligatoire
   - **Zone:SSL and Certificates:Edit**
   - **Zone:Zone:Read**
3. Zone Resources : restreindre à TA zone uniquement (sécurité)
4. Continue to summary → Create Token → copier la valeur

### 1.4 Renseigner `.env` côté Altiaro
```bash
CLOUDFLARE_API_TOKEN=<token-copié>
CLOUDFLARE_ZONE_ID=<zone-id-visible-dans-overview>
CLOUDFLARE_FALLBACK_ORIGIN=altiaro.com
```
Restart backend → fini.

---

## 2. Flow concepteur (100 % automatique)

À l'étape 6 du Cockpit, quand le concepteur clique "Vérifier propriétaire" :

| Couche | Code | Action |
|---|---|---|
| Frontend | `SiteDomain.jsx` | POST `/api/sites/{id}/domain/verify` |
| Backend  | `routes/site_domain.py:verify_custom_domain` | DNS check OVH |
| Backend  | `services/cloudflare_saas.py:add_custom_hostname` | POST CF API |
| CF       | — | émet le cert SSL (30-60 s) |
| Frontend | poll `/api/admin/sites/{id}/domain/cf-status` | UI passe en vert |

**Aucune intervention humaine nécessaire** côté Altiaro ni côté Emergent.

---

## 3. API Altiaro exposée

```
POST   /api/sites/{id}/domain/verify           [user]   Hook auto Cloudflare
POST   /api/admin/sites/{id}/domain/cf-add     [admin]  Force re-provisioning
GET    /api/admin/sites/{id}/domain/cf-status  [admin]  Lit status CF
DELETE /api/admin/sites/{id}/domain/cf-remove  [admin]  Retire le hostname

GET    /api/public/domains/resolve?host=X      [public] Anti-abus / résolution
```

---

## 4. Migration `altea-home.com` (1 commande)

```bash
# Une fois CLOUDFLARE_API_TOKEN renseigné, depuis le pod :
curl -X POST -H "Cookie: access_token=$ADMIN_JWT" \
  https://altiaro.com/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/domain/cf-add

# Vérifier le statut SSL :
curl -H "Cookie: access_token=$ADMIN_JWT" \
  https://altiaro.com/api/admin/sites/6867223e-7ea5-45a7-815a-300cd89b7656/domain/cf-status
```

---

## 5. Limitations honnêtes

| Limite | Workaround |
|---|---|
| 100 custom hostnames gratuits | Au-delà : CF for SaaS Enterprise (~$0.10/host) ou demander quota gratuit étendu (FAQ CF) |
| Origin Altiaro déjà derrière Cloudflare Emergent | CF for SaaS supporte le "Saas → Saas" via CNAME chained. Si bloque, fallback : domaine racine `altiaro.shop` direct chez Cloudflare (sans Emergent au milieu) |
| Concepteur DOIT pointer son DNS sur Altiaro | Géré automatiquement par notre intégration OVH étape 6 |

---

## 6. Fallback prévu : VPS Caddy

Si pour une raison Cloudflare for SaaS ne convient pas (ex: zone propre
indispo, contraintes RGPD spécifiques), le fallback VPS Caddy est codé
dans `backend/services/proxy_provisioning.py` et activable via
`PROXY_ADMIN_URL` dans `.env`. Le code essaie CF d'abord, puis Caddy.

Procédure VPS Caddy : voir l'historique git (commit Phase 4 / Tâche 1).

---

## 7. Checklist activation

- [ ] Compte Cloudflare créé
- [ ] Zone ajoutée + NS basculé
- [ ] Custom Hostnames activé dans la zone
- [ ] Fallback Origin configuré
- [ ] API Token créé (3 permissions)
- [ ] `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ZONE_ID` dans `backend/.env`
- [ ] Restart backend
- [ ] Test : `POST /api/admin/sites/{altea-id}/domain/cf-add` → `{"ok": true, "ssl_status": "pending_validation"}`
- [ ] Attendre 30-60 s
- [ ] `GET /api/admin/sites/{altea-id}/domain/cf-status` → `{"ssl_active": true}`
- [ ] `curl -I https://altea-home.com/` → 200 OK

---

*Mise à jour 2026-05-01 — Phase 4 finale*
