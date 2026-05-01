# Procédure d'association d'un domaine custom de boutique à Altiaro

> Cas concret traité ici : `altea-home.com` (boutique du concepteur, **pas**
> la plateforme `altiaro.com`).
>
> Architecture : **un seul pod Emergent** sert à la fois la plateforme
> (`altiaro.com`) et tous les storefronts concepteurs. Le routage par hôte
> est assuré côté code par `backend/custom_domain_middleware.py`.

---

## 1. Vue d'ensemble — qui fait quoi

| Étape | Acteur | Outil | Action |
|-------|--------|-------|--------|
| 1 | Concepteur (côté Cockpit) | UI étape 6 (Domaine) | Saisit son domaine et clique "Vérifier propriétaire" |
| 2 | Plateforme | API OVH (auto) | Configure les DNS A + CNAME chez OVH (déjà automatisé) |
| 3 | **Admin Altiaro (humain)** | **Dashboard Emergent** | **Déclare le domaine comme Custom Domain dans Emergent** |
| 4 | Cloudflare (Emergent) | Auto | Provisionne le certificat SSL |
| 5 | Plateforme | `custom_domain_middleware.py` | Réécrit les requêtes `altea-home.com/*` → `/shop/{site_id}/*` |
| 6 | Concepteur | Interface storefront | Vérifie que la boutique est en ligne |

**Bilan honnête** : l'étape 3 reste **manuelle** côté admin Altiaro. Voir §4
pour les conséquences en multi-concepteurs.

---

## 2. Procédure exacte pour `altea-home.com`

### 2.1 — Pré-requis (déjà fait)

- ✅ DNS OVH configurés (A `altea-home.com` → IP du pod Emergent + CNAME
  `www.altea-home.com` → `altea-home.com`).
- ✅ Champ `sites.domain = "altea-home.com"` persisté dans MongoDB.
- ✅ Middleware `custom_domain_middleware.py` actif (lit `Host:` header,
  résout vers `site_id`, réécrit le path `/` → `/shop/{site_id}/`).

### 2.2 — Étape manuelle dans Emergent (à faire UNE fois par domaine)

1. Aller sur le **Dashboard Emergent** du projet Altiaro.
2. Section **Custom Domains** (à côté de "Domains" pour `altiaro.com` qui
   est déjà déclaré).
3. Cliquer sur **Add Custom Domain**.
4. Saisir : `altea-home.com`
5. Cocher **également** : `www.altea-home.com` (alias).
6. Emergent (via Entri) lance la vérification DNS automatiquement.
   - Si les DNS OVH sont OK (cf. §2.1), la vérification passe en quelques
     minutes.
   - Sinon, Emergent affiche les enregistrements DNS attendus → rectifier
     côté OVH.
7. Une fois vérifié, Emergent provisionne le certificat SSL Cloudflare
   automatiquement (~5 min).
8. À partir de là, `https://altea-home.com/` arrive sur le pod et le
   middleware Altiaro le route automatiquement vers le storefront Altea.

### 2.3 — Vérification (curl côté admin)

```bash
# Doit renvoyer 200 et le HTML de la home storefront Altea
curl -I https://altea-home.com/

# Une PDP au hasard (slug du produit)
curl -I https://altea-home.com/products/<slug>

# Les redirects 301 légaux (transverses à la plateforme)
curl -I https://altea-home.com/legal/mentions-legales
# → HTTP/2 301
# → location: /legal/mentions
```

---

## 3. Ce que le middleware fait automatiquement

Code source : `backend/custom_domain_middleware.py`.

```
Visiteur → altea-home.com/
                    ↓
       Cloudflare SSL (Emergent)
                    ↓
       Pod Altiaro (FastAPI)
                    ↓
   custom_domain_middleware (avant tout router)
                    ↓
   1. Skip si /api/, /legal/, /static/, /uploads/, /docs, /shop/  → passthrough
   2. Si Host est plateforme (altiaro.com, *.preview.emergentagent.com)  → passthrough
   3. Sinon : DB lookup `sites.{domain | custom_domain}`
        ├─ Non trouvé : passthrough (404 SPA)
        └─ Trouvé site_id → réécrit scope.path :
             - "/"        → "/shop/{site_id}/"
             - "/about"   → "/shop/{site_id}/about"
             - "/legal/X" → reste "/legal/X"  (page plateforme légale)
   4. Garde-fou : sous un domaine boutique, /admin /sites /login etc.
      sont 302 → "/" (le visiteur ne peut pas voir le Cockpit).
```

**Implication concrète pour Altea** : le concepteur ne voit jamais
`altiaro.com/shop/6867223e.../` dans son URL. Tout est masqué derrière
`altea-home.com`.

**Cache** : le middleware cache `host → site_id` 5 min en mémoire pour
éviter une requête Mongo par requête HTTP (acceptable, cache lazy).

---

## 4. Multi-concepteurs : est-ce 100 % automatisé ?

### Ce qui EST automatisé aujourd'hui

✅ DNS chez OVH (via API OVH côté backend, étape 6 du Cockpit)
✅ Persistance `sites.domain` côté Mongo
✅ Routing côté pod (middleware)
✅ Pages légales serveur-side servies sous tous les hosts
✅ Aliases 301 légaux (`/legal/mentions-legales` → `/legal/mentions`)

### Ce qui n'EST PAS automatisé aujourd'hui

❌ **Déclaration du Custom Domain côté Emergent** (Dashboard → Custom Domains
→ Add Domain) reste une action **manuelle par admin Altiaro** par concepteur.

Cause : Emergent n'expose pas (à ce jour) d'API publique pour ajouter un
Custom Domain depuis le code. La déclaration et la vérification DNS passent
par leur dashboard + Entri.

### Conséquences pratiques

| Scénario | Délai | Action |
|----------|-------|--------|
| 1ᵉʳ concepteur lance Altea | T+0 | Admin déclare `altea-home.com` dans Emergent (5 min de manip + ~10 min SSL) |
| 2ᵉ concepteur ajoute `mon-shop.fr` | T+0 | Admin **doit** refaire la même manip dans Emergent |
| 10 concepteurs / jour avec leurs domaines | — | 10 × manip Emergent à faire (pas scalable en l'état) |

### Recommandation produit (à valider)

Pour atteindre l'objectif "**10 sites par jour par concepteur**" sans goulet
admin, deux options :

1. **Court terme (semaines)** : créer un canal dédié + checklist admin,
   batch les déclarations Emergent en début/fin de journée (1 admin × ~3 min
   par domaine = 30 min / jour pour 10 sites).

2. **Moyen terme (mois)** : demander à Emergent une **API Custom Domains**
   ou un **wildcard subdomain** sur `*.altiaro.shop` (ou similaire) pour
   que les nouveaux sites soient accessibles immédiatement sur
   `<concepteur-slug>.altiaro.shop` sans intervention humaine. Le concepteur
   peut ensuite, à son rythme, basculer vers son propre `.com`.

3. **Alternative technique** : déployer un **reverse-proxy Cloudflare Worker**
   qui forwarde tous les domaines vers le pod Altiaro. L'admin n'a alors
   qu'à pointer un CNAME chez Cloudflare une fois pour tous les sous-domaines
   gérés. Étude requise.

---

## 5. Désactiver / migrer un domaine

Pour retirer un domaine d'un site :
1. Côté Mongo : `db.sites.updateOne({id: SITE}, {$unset: {domain: 1}})`.
2. Le cache du middleware se vide automatiquement (TTL 5 min).
3. Côté Emergent : retirer le Custom Domain dans le dashboard si on
   l'avait ajouté.

Pour migrer `altea-home.com` d'un site à un autre : modifier `sites.domain`
côté Mongo, le routing suit (TTL 5 min).

---

## 6. Checklist de mise en ligne d'un nouveau concepteur

- [ ] Cockpit étape 6 → DNS OVH OK (vert)
- [ ] Mongo `sites.domain` rempli
- [ ] **Admin** : déclarer le domaine dans Emergent Custom Domains
- [ ] Attendre la vérification DNS Emergent (~5-10 min)
- [ ] Attendre le SSL Cloudflare (~5 min)
- [ ] `curl -I https://<domaine>/` → 200
- [ ] `curl -I https://<domaine>/legal/mentions-legales` → 301 → 200
- [ ] Tester 1 PDP au hasard
- [ ] Cockpit étape 10 (QA) → ready=true

---

*Dernière mise à jour : 2026-05-01*
