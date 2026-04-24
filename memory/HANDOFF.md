# Altiaro — Mémo technique de reprise (HANDOFF)

> **Dernière mise à jour : 2026-04-24**
>
> Ce document est la source de vérité pour un nouvel intervenant (client, tech lead, agent IA)
> qui se demande **ce qui marche, ce qui reste à faire, comment onboarder un concepteur**.
> Il référence le code actuel ; il remplace les mémos antérieurs.

---

## 1 — Statut général

| Phase | Scope | Statut |
|---|---|---|
| Phase 1 (Chantier 6) | Simplification UI du Cockpit (`SiteDetail.jsx` : 834 → 166 lignes, gating visuel, SEO caché avant step 8) | ✅ Livré + testé |
| Phase 2 (Chantier 7) | Dashboard Analytics interne (`/sites/:id/analytics`, ingestion `/api/public/sites/{id}/track`, `recharts`) | ✅ Livré + testé |
| Phase 3 | Storefront public multilingue 6 langues (FR, EN, DE, NL, IT, ES) + `LanguageSwitcher` + hreflang dynamiques | ✅ Livré + testé (3 sweeps i18n successifs) |
| Fix bonus | Bug bloquant import AliExpress — migration `aliexpress.affiliate.productdetail.get` → `aliexpress.ds.product.get` (API Dropshipping) | ✅ Livré + testé |

⚠️ **Working tree non-pushé sur `origin/main`** : 19+ commits locaux s'accumulent. Utiliser le bouton **"Save to Github"** d'Emergent dans la barre d'action du chat pour pusher proprement (l'agent n'a pas le droit d'exécuter `git push`).

---

## 2 — Ce qui marche aujourd'hui

- **Cockpit 9 étapes avec gating strict** — source unique `backend/routes/journey_gating.py` + endpoint `GET /api/sites/{id}/journey`. L'opérateur ne peut pas sauter une étape, le frontend s'adapte.
- **QuickScan niche validation** en <30 s (prix, volume, concurrence, rentabilité Ads). Fallback Claude si Google Ads KeywordPlanIdeaService indisponible.
- **Sourcing** : AliExpress (API Dropshipping, OAuth multi-tenant) + CJ Dropshipping (tracking sync H+2). Import 1-clic produit.
- **Multi-marché** : 11 pays (FR, BE, LU, DE, AT, NL, IT, ES, PT, IE, FI) × 6 langues. Backend i18n complet (sitemap multi-lang, `llms.txt?lang=XX`, hreflang, translation layer), storefront 100 % i18n (242+54+9×6 ≈ 300 clés de dict).
- **Dashboard Analytics interne** (`/sites/:id/analytics`) — page_view, add_to_cart, purchase, session_id, `ip_hash` (RGPD-safe), agrégations recharts sur 7/30/90 jours.
- **Paiement Mollie** test + live (clé live présente), **Resend** (domaine `altiaro.com` vérifié, emails transactionnels), **OVH Domaines** (achat + cron auto-config DNS toutes les 5 min), **IndexNow** (submit automatique à la publication).
- **Storefront public** : homepage éditoriale monochrome, fiche produit narrative, cart localStorage, checkout Mollie, reviews + bundles, blog cluster mensuel (pilier + 4 satellites auto-traduits Claude), SEO complet (sitemap images, Organization schema, Speakable FAQ, Article v2), **LanguageSwitcher** en header.

---

## 3 — Intégrations : état détaillé

| Intégration | Statut code | Credentials `.env` | Action requise du client |
|---|---|---|---|
| **Google Ads** | ⚠️ Dev token en **mode test** | OK (tous les clients OAuth présents) | Attendre réponse **Basic Access** Google (2-5 jours après soumission). Puis mettre à jour `GOOGLE_ADS_DEVELOPER_TOKEN` (voir §5). |
| **Google Search Console** | OAuth prêt multi-tenant | N/A (flow user-driven) | Connecter site par site quand un storefront est validé (voir §6 étape 7). |
| **Google Merchant Center** | OAuth complet | OK | Rien (compte connecté, cron `merchant_daily_sync` actif). |
| **Mollie** | Live key + test key | OK | Rien. |
| **Resend (`altiaro.com`)** | Domaine vérifié | OK | Rien. |
| **OVH Domains** | API + cron auto-DNS | OK | Créer le sous-domaine **`sites.altiaro.com`** dans OVH (A-record → `104.18.11.243`). Voir §7. |
| **AliExpress Dropshipping API** | OAuth finalisé, `aliexpress.ds.product.get` | Partiel : `ALIEXPRESS_TRACKING_ID` vide (décision user) | Rien. L'app marche **sans** affiliation (pas de PID partenaire). |
| **CJ Dropshipping** | API key valide | OK | Rien. |
| **IndexNow** | Clé stable | OK | Rien. |
| **Emergent LLM (Claude Sonnet 4.5)** | Via `emergentintegrations` | OK | Rien. |

---

## 4 — Variables d'environnement : état final

**Backend `.env`** : 53 variables renseignées — toutes remplies **sauf** :
- `ALIEXPRESS_TRACKING_ID` — **skippé par décision user** (pas d'affiliation AE souhaitée). L'app fonctionne sans.

Variables d'infra réseau :
- `PLATFORM_SITE_IP=104.18.11.243` — IP de l'ingress preview Emergent. **À remplacer par l'IP prod OVH** quand le client déploie sur son infra définitive.
- `PUBLIC_CNAME_TARGET=sites.altiaro.com` — cible CNAME pour les domaines custom des concepteurs. **Nécessite création du sous-domaine côté OVH** (voir §7).

**Frontend `.env`** : 2 variables (`REACT_APP_BACKEND_URL`, `WDS_SOCKET_PORT=443`). Ne pas modifier.

---

## 5 — Checklist post-approbation Google Ads Basic Access

Quand Google répond "Basic Access approved" :

- [ ] Aller sur [https://ads.google.com/aw/apicenter](https://ads.google.com/aw/apicenter) → copier le **nouveau Developer Token "Basic"**.
- [ ] Remplacer `GOOGLE_ADS_DEVELOPER_TOKEN=` dans `/app/backend/.env`.
- [ ] Redémarrer le backend : `sudo supervisorctl restart backend`.
- [ ] Re-lancer un QuickScan sur une niche (ex. "fauteuil releveur") → vérifier dans `/var/log/supervisor/backend.err.log` que l'appel `KeywordPlanIdeaService.GenerateKeywordIdeas` **ne retombe plus sur le fallback Claude**.
- [ ] QuickScan affiche désormais des **volumes Google réels** (pas des estimations Claude).
- [ ] Sur `/admin/sites/:id/ads-campaign`, vérifier que la création de campagne aboutit sans erreur `PERMISSION_DENIED`.

**Si Google demande des modifs / précisions au lieu d'approuver** :
- [ ] Répondre **dans les 48 h** (sinon ticket fermé automatiquement).
- [ ] Si besoin, préciser les scopes et cas d'usage dans le design document (ils veulent concret : "import campagnes existantes", "création Search RSA", "Keyword Planner").

---

## 6 — Checklist onboarding premier concepteur pilote

- [ ] Créer un compte concepteur via l'admin : `POST /api/users` avec `role: "concepteur"`, ou via l'UI `/users` (bouton "Ajouter").
- [ ] Envoyer les credentials par email manuel (Resend template transactionnel disponible dans `routes/emails.py`).
- [ ] Préparer un guide d'onboarding papier/vidéo des 9 étapes du cockpit — **TODO marketing** (pas de guide PDF finalisé à date).
- [ ] Session Zoom 1 h pour l'accompagner sur **steps 1 à 3** (QuickScan niche → Pricing → Sourcing AE/CJ).
- [ ] **Reviewer son QuickScan** avant de lui donner le GO (seuil concurrence 75, marges min, volume min — voir `QS_*` env vars).
- [ ] Surveiller son premier import AE pour détecter d'éventuelles régressions de l'API AE côté Alibaba (la plateforme évolue souvent).
- [ ] Quand il atteint **step 9** (validation) : connecter GSC sur son domaine (voir §7, le bouton "Connecter GSC" est dans le cockpit, section SEO).
- [ ] Créer la **première campagne Google Ads** pour lui (via `/admin/sites/:id/ads-campaign`) — **disponible uniquement après approbation Basic Access** (voir §5).

---

## 7 — Config DNS OVH `sites.altiaro.com`

Étapes dans OVH Manager :

1. Se connecter à [https://www.ovh.com/manager/](https://www.ovh.com/manager/).
2. Sélectionner le domaine **`altiaro.com`** dans la liste.
3. Onglet **"Zone DNS"** → cliquer **"Ajouter une entrée"**.
4. Paramètres :
   - **Type** : `A`
   - **Sous-domaine** : `sites`
   - **Cible** : `104.18.11.243` (valeur actuelle de `PLATFORM_SITE_IP`)
   - **TTL** : `300` (5 min, pratique pour itérer tant qu'on n'est pas en prod)
5. Valider → attendre ~5 min pour la propagation.
6. Tester : `dig sites.altiaro.com +short` doit retourner `104.18.11.243`.
7. Ensuite, quand un concepteur achète un domaine custom via OVH depuis le cockpit, le cron `dns_auto_config` (toutes les 5 min) créera automatiquement un CNAME `www.{domain_custom} → sites.altiaro.com` et enverra un email "🌍 domain is live".

⚠️ **En production**, remplacer `104.18.11.243` par **l'IP réelle du serveur prod** (le preview Emergent actuel n'est pas stable pour le trafic client).

---

## 8 — Bugs connus / TODOs backlog

| Sév. | Fichier | Problème | Fix prévu |
|---|---|---|---|
| **P1** | `frontend/src/components/storefront/Hero.jsx:27` | Eyebrow affiche parfois `[object Object]` quand `brand.tagline` est un dict multi-lang `{fr:…, en:…}` | Passer la ligne par `designText()` ou `pickLang()` au lieu de lire `brand.tagline` brut. |
| **P2** | `backend/routes/analytics.py:45` | Rate-limit `POST /api/public/sites/{id}/track` en mémoire Python (`_rl_bucket` dict), non partagé entre workers, reset à chaque restart | OK pour MVP. À l'échelle : migrer sur **Redis** + `slowapi`. |
| **P3** | `frontend/src/pages/StorefrontOrderDetail.jsx:143-154` + `StorefrontReview.jsx:49-135` | 8 strings FR hardcodées (CTA "Laisser mon avis", header SEO, labels form) | Mini-sweep i18n dédié. Critique seulement si concepteur avec gros trafic multilingue sur son compte client. |
| **P3** | `backend/routes/design.py` | 95 Ko, 37 endpoints monolithique | Split par domaine : `design_hero.py`, `design_logo.py`, `design_sections.py`, `design_footer.py`. |
| **P3** | OpenAPI | 293 / 307 opérations **sans tag** (visibles dans `/api/docs` sans regroupement) | Ajouter `tags=["…"]` sur chaque décorateur FastAPI pour navigation Swagger propre. |
| **P3** | DB `copilot_messages`, `designs`, `block_outputs`, `ads_copy` | Collections déclarées/indexées mais **0 doc** en préprod | Soit code mort, soit features pas encore exercées. Auditer et supprimer ce qui est obsolète. |
| **P3** | Google Ads | Dev token en mode test → volumes via fallback Claude uniquement | Débloqué automatiquement dès que Basic Access approuvé (voir §5). |

---

## 9 — Crons APScheduler actifs (12 jobs)

| Job | Fréquence |
|---|---|
| `weekly_debits` | Lundi 03h UTC |
| `bimonthly_payouts` | 1er + 15 du mois, 03h UTC |
| `reviews_check_due` | Tous les jours, 04h UTC |
| `ae_tracking_sync` | Tous les jours, 05h30 UTC |
| `cj_tracking_sync` | Toutes les 2 h (HH:15) |
| `opportunity_scan` | Lundi 05h UTC |
| `dns_auto_config` | **Toutes les 5 min** |
| `monthly_blog_cluster` | 1er du mois, 06h UTC |
| `weekly_seo_coach` | Lundi 08h UTC |
| `citation_tracker_weekly` | Jeudi 08h UTC |
| `ae_deals_watch` | Mardi 06h UTC |
| `merchant_daily_sync` | Tous les jours, 04h UTC |

---

## 10 — Credentials de test + URLs utiles

- **Preview URL** : [https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com](https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com)
- **Admin** : `admin@conceptfactory.fr` / `Factory2026!`
- **Concepteur** : `concepteur@conceptfactory.fr` / `Concepteur2026!`
- **Site démo avec data analytics seedée** : `d33a5795-7a19-4a03-86a2-ef83ea19db9b` (Projet Fauteuil releveur)
- **Site démo vierge** : `cc58f41b-285b-4007-8cb2-06b50d3baff6` (Démo Altiaro)
- **Storefront public** : [/shop/d33a5795-7a19-4a03-86a2-ef83ea19db9b](https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com/shop/d33a5795-7a19-4a03-86a2-ef83ea19db9b)
- **Dashboard Analytics** : [/sites/d33a5795-7a19-4a03-86a2-ef83ea19db9b/analytics](https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com/sites/d33a5795-7a19-4a03-86a2-ef83ea19db9b/analytics) (après login concepteur)
- **OpenAPI Swagger** : [/api/docs](https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com/api/docs)
- **OpenAPI Redoc** : [/api/redoc](https://24f2727d-5084-4b95-a658-4f3bc93cf26e.preview.emergentagent.com/api/redoc)

### Scripts utiles (tous dans `/app/backend/scripts/`)

```bash
cd /app/backend

# Forcer un site à l'état "validé" pour tester le parcours post-step-9
python -m scripts.force_site_validated <site_id>

# Peupler des events analytics factices (pour visualiser les graphes recharts)
python -m scripts.seed_analytics <site_id> --events 60 --days 7

# Seed des traductions produit pour les 6 langues (via Claude)
python -m scripts.seed_product_translations <site_id>

# Debug direct de l'API AE (contourne le backend, montre la réponse brute)
python scripts/debug_ae_ds.py
```

### Tests rapides

```bash
# Backend alive ?
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/api/docs   # → 200

# Collections MongoDB peuplées ?
python3 -c "
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
async def main():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = c[os.environ.get('DB_NAME','conceptfactory')]
    for n in ['sites','products','storefront_events','users']:
        print(n, '=', await db[n].count_documents({}))
asyncio.run(main())
"
```
