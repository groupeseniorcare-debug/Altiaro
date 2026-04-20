# Concept Factory — Product Requirements Document

## Problem statement original
SaaS multi-tenant d'e-commerce 100% custom (pas de Shopify) dédié à la **Silver Economy** (60+ et aidants) sur 6 marchés EU : 🇫🇷 FR · 🇩🇪 DE · 🇨🇭 CH · 🇧🇪 BE+LU · 🇬🇧 UK · 🇳🇱 NL.

- **Admin** gère Google Ads, finances globales, commandes côté fournisseurs.
- **Concepteurs** montent sites, choisissent produits, traitent SAV et remboursements.
- Modèle 50% marge brute partagée.

## Architecture
- **Stack** : FastAPI (10 routers modulaires) + MongoDB (motor async) + React 18 + Tailwind + Phosphor icons + Framer Motion + recharts
- **Structure backend** : `server.py` orchestrateur 117 lignes + `deps.py` (shared : db, auth, helpers) + `routes/{auth,users,sites,steps,products,orders,public_shop,niches,dashboard,meta}.py`
- **Auth** : JWT httpOnly cookies, bcrypt, brute force 15min, admin seeded via .env
- **LLM** : Emergent LLM Key via emergentintegrations, timeout 50s, 402 budget, 504 timeout, 402 budget épuisé propre
- **Niche Engine** : 20 niches × 6 pays seedées idempotemment
- **Site Factory** : catalogue produits i18n FR/EN/DE/NL par site + storefront `/shop/{id}` + cart localStorage + checkout → commande
- **Admin Ops Center** : `/orders` globale avec stats, filtres, transitions de statut, export CSV, rate-limit IP 10/10min (via X-Forwarded-For)

## User personas
- **Admin** : voit tout, crée sites + users, gère commandes + finances
- **Concepteur** : voit ses sites, gère son catalogue, auto-progression étapes
- **Client final** (public) : achète sur `/shop/{id}` en FR/EN/DE/NL sans compte

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
13. **Admin Ops Center** ✅ (NEW 2026-04-20 · Sprint 3)
14. **Server.py refactoré en 10 routers** ✅ (NEW 2026-04-20 · Sprint 3)

## What's been implemented

### 2026-04-20 · Sprint 4 : Media & Import
- **Scraper `/app/backend/scraper.py`** : fetch + extraction Open Graph + JSON-LD + Schema.org Product + fallback Shopify Analytics
- **POST `/api/sites/{id}/products/import`** : renvoie un draft produit pré-rempli (name FR/EN, description, price, currency, images, sku, supplier_url) — **non persisté**, le frontend l'injecte dans l'editor
- **POST `/api/uploads/image`** : upload image générique (jpg/png/webp/gif/avif, max 8 Mo), renvoie URL publique
- Frontend : barre d'import URL au-dessus de la grille produits, composant `ImagesField` avec drag&drop, multi-upload, preview gallery, reorder, badge "Principale", fallback input URL
- Testé : Allbirds (Shopify) → import complet (nom + 110$ + image + description). Patagonia/Google : partial fallback gracieux.

---

### 2026-04-20 · Sprint 3 : Admin Ops Center + refactor
- **5 endpoints admin ops** : `GET /admin/orders` (filtrable), `/stats`, `PATCH /admin/orders/{id}` (transitions validées), `GET /export.csv`
- **Page frontend `/orders`** : stats cards (7 statuts), table avec recherche, slide-in détail avec historique + copy address + copy email + liens fournisseurs + transitions contextuelles
- **Status transitions** : pending_payment → paid|cancelled · paid → shipped|refunded|cancelled · shipped → delivered|refunded · delivered → refunded · cancelled/refunded terminaux
- **Rate-limit IP-based** sur POST public orders : 10 cmd / IP / 10 min via X-Forwarded-For + index Mongo dédié
- **Refactor server.py** : 1252 → 117 lignes + 10 routers modulaires (auth 78, users 57, sites 97, steps 264, products 63, orders 179, public_shop 146, niches 29, dashboard 129, meta 17) + `deps.py` shared
- Testing : 27/27 pytest backend + frontend E2E validé (iteration_3.json)

### 2026-04-20 · Sprint 2 : Phase 3 Site Factory MVP
- `models_shop.py` (ProductCreateInput i18n, OrderCreateInput avec validators)
- Collections `products`, `orders` + indexes
- Admin CRUD produits + endpoints publics storefront
- Sécurité : prix canoniques serveur, cascade delete, order_number unique
- Frontend : ProductEditor i18n, 5 pages `/shop/{id}`, i18n 4 langues, cart localStorage scopé

### 2026-04-20 · Sprint 1 : Niche Engine + rebranding
- Rebranding "Launch OS" → "Concept Factory", auto-progression étapes, 20 niches × 6 pays, `/niches` et `/niches/:slug`, pré-remplissage wizard

## Prioritized backlog

### P0 (fait)
- [x] Auth, Sites, Workflow, Niche Engine, Phase 3 MVP shop, Admin Ops Center, Refactor

### P1 — Phase 5 : Paiement réel (⏳ en attente clés user)
- [ ] **Mollie** (paiement + payouts) — **requiert clé API Mollie**
- [ ] **Resend** (emails transactionnels FR/EN/DE/NL) — **requiert clé API + domaine vérifié**
- [ ] **TVA multi-pays** (5 taux : FR 20%, DE 19%, BE 21%, NL 21%, UK 20%, CH TVA import)
- [ ] **Moteur 50/50** : calcul Marge Brute Partageable par commande
- [ ] **SAV workflow** : tickets, messages client, refunds partiels

### P1.5 — Améliorations produit (sans clé externe)
- [x] **Import DSers-like** ✅ (2026-04-20 sprint 4)
- [x] **Upload images** ✅ (2026-04-20 sprint 4)
- [ ] **Streaming CSV export** pour gros volumes (actuellement memory buffer 5000 rows max)

### P2 — Phase 6
- [ ] **Google Ads Center** admin (API)
- [ ] **DataForSEO** : recalibrage métriques Niche Engine
- [ ] **Multi-domaine** : CNAME par site → routing Nginx
- [ ] **Notifications admin** (email nouvelle commande)
- [ ] **Recherche globale** ⌘K
- [ ] **Mobile responsive** storefront (déjà partiellement fait)

## Refactoring encore à faire (urgence basse)
- Rate-limit order : réindexer `_meta_ip + created_at` ✅ fait sprint 3
- `seed_prompts.py` 50 prompts → 4 blocs Template/Produits/SEO/Marketing
- Ajout de tests pytest pour chaque route.py nouvellement créée

## Next tasks
1. **Phase 5** quand l'user fournit clés Mollie + Resend
2. **Import produit** depuis URL fournisseur (pas de clé requise)
3. **Upload images** produits

## Credentials
Voir `/app/memory/test_credentials.md` — `admin@conceptfactory.fr` / `Factory2026!`
