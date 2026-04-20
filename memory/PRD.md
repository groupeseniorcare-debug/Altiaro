# Concept Factory — Product Requirements Document

## Problem statement original
SaaS multi-tenant d'e-commerce 100% custom (pas de Shopify) dédié à la **Silver Economy** (60+ et aidants) sur 6 marchés EU : 🇫🇷 FR · 🇩🇪 DE · 🇨🇭 CH · 🇧🇪 BE+LU · 🇬🇧 UK · 🇳🇱 NL.

- **Admin** gère Google Ads, finances globales, commandes côté fournisseurs.
- **Concepteurs** montent sites, choisissent produits, traitent SAV et remboursements.
- Modèle 50% marge brute partagée.

## Architecture
- **Stack** : FastAPI (14 routers modulaires) + MongoDB (motor async) + React 18 + Tailwind + Phosphor icons + Framer Motion
- **Auth** : JWT httpOnly cookies, bcrypt, brute force 15min, admin seeded via .env
- **LLM** : Emergent LLM Key (Claude Sonnet 4.5) via emergentintegrations pour Niche Analyzer et Ads Copy Generator
- **Site Factory** : catalogue produits i18n FR/EN/DE/NL par site + storefront `/shop/{id}` + cart localStorage + checkout → commande
- **Admin Ops Center** : `/orders` globale avec stats, filtres, transitions, export CSV streaming, rate-limit IP 10/10min
- **Structure backend** : `server.py` (~130 lignes) + `deps.py` + `seed_prompts.py` + `routes/{auth,users,sites,steps,products,orders,public_shop,niches,dashboard,meta,uploads,search,analyzer,ads_copy,duplicate,domain}.py`

## User personas
- **Admin** : voit tout, crée sites + users, gère commandes + finances
- **Concepteur** : voit SES sites, gère son catalogue, duplique ses sites, génère Ads Copy
- **Client final** (public) : achète sur `/shop/{id}` ou `https://custom.domain` en FR/EN/DE/NL sans compte

## Blocks logiques (depuis sprint 7)
Les 50 étapes du playbook sont regroupées en 4 blocs :
1. 🏗️ **Template & Boutique** — Shopify backend, Front React, Juridique, Paiement, SAV, Logistique
2. 📦 **Produits & Sourcing** — Étude marché, Sourcing fournisseurs
3. 🔍 **SEO & Marque** — Positionnement/voix, SEO technique, AEO/GEO
4. 🚀 **Marketing & Scale** — Ads, Social proof, Analytics, Duplication

## Core requirements (status)
1. Auth JWT 2 rôles ✅
2. Dashboard KPIs ✅
3. Sites CRUD + wizard ✅
4. Workflow 50 étapes auto-progression ✅
5. StepPanel avec IA ✅
6. Monitoring Admin ✅
7. Finances manuelles ✅
8. Users CRUD admin ✅
9. Niche Engine 20×6 ✅
10. Catalogue produits i18n ✅
11. Storefront public multilingue ✅
12. Cart + Checkout + Orders ✅
13. Admin Ops Center ✅
14. Server.py refactoré en 14 routers ✅
15. **Niche Analyzer IA dynamique** (Claude 4.5, 6 marchés) ✅
16. **Google Ads Copy Generator** (Claude 4.5, RSA 15h+4d+25kw) ✅
17. **Blocks refactor** (50 étapes → 4 blocs logiques) ✅
18. **Site Duplication** ✅
19. **Multi-domain management** (CNAME + verification DNS) ✅
20. **Scale 6 pays** (1 clic → N clones localisés + Ads Copy auto) ✅

## What's been implemented

### 2026-04-20 · Sprint 8 : Scale 6 pays (multi-country mass duplication)
- **🚀 POST `/api/sites/{id}/scale`** : duplique un site source vers N clones (1 par pays cible). Chaque clone hérite de selected_countries=[cc], primary_language mappée (FR→fr, DE→de, CH→fr, BE→fr, UK→en, NL→nl), daily_budget_eur=30. Input : `{target_countries, custom_domains?, copy_products, generate_ads_copy, tone}`.
- **🌐 Domaines custom par pays** : chaque clone peut recevoir son propre domaine (ex: `shop.de`, `shop.nl`). Validations : hostname RFC 1035, pas de doublon intra-batch, unicité cross-site (409 si déjà pris).
- **🤖 Ads Copy en background** : via `BackgroundTasks` FastAPI, génération async Claude 4.5 par clone (~30s chacun, non bloquant). Fail silently si budget LLM épuisé.
- **👨‍👩‍👧‍👦 Batch tracking** : `scale_batch_id` partagé entre siblings + `scaled_from` sur chaque clone + `GET /api/sites/{id}/scale-siblings` pour afficher la famille.
- **UI** : bouton "Scaler 6 pays" (gradient rocket) sur SiteDetail → ScaleModal 6 cartes pays (checkbox + flag + langue + devise + 30€/j + input domaine), toggles copy_products/generate_ads_copy, sélecteur de ton, récap budget total, résultat avec liens vers chaque clone.
- Tests : 13/13 pytest (9 iter7 + 4 iter7_extra) + 100% E2E frontend (iteration_7.json). Regression : 23/23 passes.

### 2026-04-20 · Sprint 7 : Site Duplication + Multi-domain
- **🔁 POST `/api/sites/{id}/duplicate`** : clone un site en 1 clic (nouveau nom, 50 étapes fresh, produits clonés en draft, orders/ads-copy NON copiés). Idéal pour scaler cross-pays.
- **🌐 Multi-domain custom** : `GET/POST/DELETE /api/sites/{id}/domain` + `POST /api/sites/{id}/domain/verify` avec lookup DNS (dnspython) CNAME avec fallback A-records. Uniqueness garantie par index partiel Mongo. `GET /api/public/domains/resolve?host=...` pour le routage storefront public (404 si non vérifié).
- **UI** : sur SiteDetail, 2 boutons `Dupliquer` et `Domaine` + 2 modales propres (instructions CNAME complètes : type/name/value/TTL + état vérifié).
- Tests : 8/8 pytest nouveaux + 100% E2E frontend (iteration_6.json)

### 2026-04-20 · Sprint 6.5 : Ads Copy Generator + Blocks refactor
- **📣 Google Ads Copy Generator** : `POST /api/sites/{id}/ads-copy/generate` via Claude 4.5 → 15 headlines (≤30 chars), 4 descriptions (≤90 chars), 25 keywords, 12 negative keywords, 4 sitelinks, 6 callouts. Sanitizer server-side enforce les limites. Export CSV compatible Google Ads Editor. Historique par site + restauration. Support FR/DE/CH/BE/UK/NL + tons (rassurant/premium/direct).
- **🧩 Blocks refactor** : `seed_prompts.py` expose BLOCKS dict (template/products/seo/marketing) + PHASE_TO_BLOCK mapping. Chaque step reçoit block, block_name, block_order, block_emoji. Migration idempotente au startup (200 steps backfilled). Endpoint `GET /api/meta/blocks`. UI SiteDetail groupe désormais par blocs avec progress bar dédiée.
- Tests : 15/15 pytest backend + E2E frontend (iteration_5.json)

### 2026-04-20 · Sprint 6 : Niche Analyzer IA + Sync + Mobile
- Niche Analyzer IA via Claude 4.5 (analyse 6 marchés FR/DE/CH/BE/UK/NL, verdicts GO/MAYBE/NOGO)
- Multi-market launch avec budget 30€/jour par pays sélectionné
- Concepteurs peuvent créer leurs sites (auto-assignés)
- Resync fournisseur avec diff prix + alerte marge
- Mobile responsive complet

### 2026-04-20 · Sprint 5 : ⌘K + Streaming CSV
- Command Palette `⌘K` global admin (sites/products/orders/niches/users)
- Streaming CSV export O(1) mémoire

### 2026-04-20 · Sprint 4 : Media & Import
- Scraper Open Graph + JSON-LD + Shopify Analytics
- Import URL produit + upload images drag&drop

### 2026-04-20 · Sprint 3 : Admin Ops Center + refactor
- 5 endpoints admin orders, page /orders, transitions status, rate-limit IP
- Refactor server.py monolithic → modulaire

## Prioritized backlog

### P0 (fait) ✅
- Auth, Sites CRUD, Workflow 50 étapes, Niche Engine, Phase 3 MVP shop, Admin Ops Center, Niche Analyzer IA, Ads Copy Generator, Blocks refactor, Site duplication, Multi-domain

### P1 — Phase 5 : Paiement réel (⏳ en attente clés user)
- [ ] **Mollie** (paiement + payouts) — **requiert clé API Mollie** (test_xxx + live_xxx)
- [ ] **Resend** (emails transactionnels FR/EN/DE/NL) — **requiert clé API + domaine vérifié**
- [ ] **TVA multi-pays** (FR 20%, DE 19%, BE 21%, NL 21%, UK 20%, CH import)
- [ ] **Moteur 50/50** : calcul Marge Brute Partageable par commande
- [ ] **SAV workflow** : tickets, messages client, refunds partiels

### P2 — Phase 6
- [ ] **Google Ads Center** admin (API, requiert clé Google Ads API)
- [ ] **DataForSEO** : recalibrage métriques Niche Engine (clé DataForSEO)
- [ ] **Notifications admin** (email nouvelle commande — lié à Resend)
- [ ] **Refactor seed_prompts.py en profondeur** — réécrire les 50 prompts en 4 mega-prompts (risque élevé, bénéfice UX marginal vs blocs actuels)

## Next tasks
1. **Phase 5** quand l'user fournit clés Mollie + Resend
2. **Google Ads Center** quand clé Google Ads API fournie

## Credentials
Voir `/app/memory/test_credentials.md` — `admin@conceptfactory.fr` / `Factory2026!` · `concepteur@conceptfactory.fr` / `Concepteur2026!`
