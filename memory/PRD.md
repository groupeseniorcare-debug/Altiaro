# Concept Factory — Product Requirements Document

## Problem statement original
L'utilisateur veut bâtir **Concept Factory**, un SaaS multi-tenant d'e-commerce 100% custom (pas de Shopify) dédié à la **Silver Economy** (60+ et aidants) sur 6 marchés EU : 🇫🇷 FR · 🇩🇪 DE · 🇨🇭 CH · 🇧🇪 BE+LU · 🇬🇧 UK · 🇳🇱 NL.

- **Admin (founder)** gère centralement Google Ads, finances globales, les commandes côté fournisseurs.
- **Concepteurs (opérateurs)** montent leurs sites, sélectionnent les produits (catalogue DSers-like interne), traitent le SAV et les remboursements.
- Modèle économique : 50% marge brute partageable entre Admin et Concepteur.
- Produits non-médicaux ; catalogue fournisseurs CJ / BigBuy / AliExpress EU.

## Architecture
- **Stack** : FastAPI + MongoDB (motor async) + React 18 + Tailwind + shadcn/ui + @phosphor-icons/react + Framer Motion + recharts
- **Auth** : JWT httpOnly cookies (access 8h + refresh 7j), bcrypt, brute force 15min après 5 échecs, admin seeded via .env
- **LLM** : Emergent LLM Key via emergentintegrations.LlmChat (Claude Sonnet 4.5 par défaut). Timeout 50s + 402 budget + 504 timeout gracieux.
- **Niche Engine** : 20 niches × 6 pays seedées idempotemment.
- **Site Factory (Phase 3)** : catalogue produits i18n par site + storefront public `/shop/{siteId}` + cart localStorage + checkout → commande `pending_payment`.

## User personas
- **Admin (fondateur)** : voit tout, crée sites (wizard lié au Niche Engine), gère users et finances.
- **Concepteur (opérateur)** : voit uniquement ses sites, exécute les étapes en auto-progression, gère son catalogue produits.
- **Client final (public)** : achète sur `/shop/{siteId}`, navigue en FR/EN/DE/NL, passe commande sans créer de compte.

## Core requirements (status)
1. Auth JWT 2 rôles ✅
2. Dashboard KPIs ✅
3. Liste sites en cards ✅
4. Wizard création site + seed 50 étapes ✅
5. SiteDetail workflow phases ✅
6. StepPanel auto-progression ✅
7. Monitoring Admin ✅
8. Finances manuelles ✅
9. Users CRUD admin ✅
10. Niche Engine 20×6 ✅
11. **Catalogue produits par site (CRUD admin i18n)** ✅ (NEW 2026-04-20)
12. **Storefront public multilingue FR/EN/DE/NL** ✅ (NEW 2026-04-20)
13. **Cart + Checkout + Orders** ✅ (NEW 2026-04-20)

## What's been implemented

### 2026-04-20 · Sprint 2 : Phase 3 Site Factory MVP
- Backend `models_shop.py` (ProductCreateInput i18n, OrderCreateInput avec validators `quantity>0, le=99`, `price>=0`)
- Collections MongoDB `products`, `orders` + indexes dédiés
- Endpoints CRUD admin : `GET/POST/PATCH/DELETE /api/sites/{id}/products` + `GET /api/sites/{id}/orders`
- Endpoints publics (sans auth) : `GET /api/public/sites/{id}`, `.../products`, `.../products/{id}`, `POST /api/public/sites/{id}/orders`, `GET /api/public/sites/{id}/orders/{order_number}`
- **Sécurité** : recalcul serveur des totaux avec **prix canoniques DB** (pas les prix client) · order_number unique `CF-{ts}-{hex}` · cascade delete site → products + orders
- Frontend admin : page `/sites/{id}/products` avec grille + slide-in ProductEditor (tabs FR/EN/DE/NL, images multiples, featured, statut active/draft/archived)
- Frontend public : 5 pages `/shop/{siteId}` (Home grid · /product/:id · /cart · /checkout · /confirmation) via `StorefrontLayout` senior-friendly + footer trust signals
- i18n dictionnaire 4 langues + localStorage persistant `cf_lang_{siteId}`
- Cart localStorage scopé `cf_cart_{siteId}` avec événement `cf_cart_updated` pour refresh temps réel du badge
- Livraison gratuite dès 50€, sinon 4.90€ (hard-codé MVP, Phase 5 TVA par pays)
- `/auth/me` skip sur routes `/shop/*` pour éviter les 401 bruyants
- Testing : 21/21 backend pytest + E2E frontend passés, 0 bug critique

### 2026-04-20 · Sprint 1 : Niche Engine + rebranding
- Rebranding "Launch OS" → "Concept Factory"
- Workflow auto-progression (suppression du gating admin)
- 20 niches × 6 pays seedées idempotemment
- Pages `/niches` (catalogue filtrable) et `/niches/:slug` (analyse 6 pays + bouton Lancer un site)
- Pré-remplissage wizard `/sites/new` depuis fiche niche

### Précédemment
- FastAPI + 30+ endpoints · Seed 50 prompts du playbook · React routing + Layout sidebar + StepPanel

## Prioritized backlog

### P0 (fait)
- [x] Auth + admin seed
- [x] Sites CRUD + workflow 50 étapes
- [x] Niche Engine
- [x] Auto-progression étapes
- [x] Phase 3 MVP : catalogue produits + storefront + cart + checkout

### P1 — Phase 4 (prochain sprint)
- [ ] **Admin Ops Center** : page `/orders` globale pour l'admin (toutes commandes tous sites) · filtres par statut · action "Envoyer au fournisseur" · export CSV
- [ ] **Refactor `server.py`** (1046 lignes) → `/app/backend/routes/{auth,sites,steps,niches,products,orders,financials,dashboard}.py`
- [ ] **Rate-limiting** sur `/public/orders` (IP-based) pour éviter le spam
- [ ] **Import DSers-like** : page Admin/Concepteur pour coller une URL AliExpress/CJ/BigBuy → parse + création produit auto
- [ ] **Upload images** pour produits (actuellement URL manuelle)

### P2 — Phase 5 (finances)
- [ ] **Intégration Mollie** (paiement réel + payouts) · lien de paiement envoyé par email
- [ ] **TVA multi-pays** (5 taux : FR 20%, DE 19%, BE 21%, NL 21%, UK 20%, CH 0%+TVA import)
- [ ] **Moteur 50/50** : calcul Marge Brute Partageable auto par commande
- [ ] **SAV workflow** : tickets, messages client, refunds

### P3 — Phase 6+
- [ ] **Google Ads Center** : interface admin pour créer/gérer campagnes via API
- [ ] **DataForSEO** pour recalibrer métriques Niche Engine avec chiffres réels
- [ ] **Emails transactionnels** (Resend) : confirmation commande, relance panier, expédition
- [ ] **Multi-domaine** : chaque site sur `marque.com` via DNS CNAME + routing Nginx
- [ ] **Notifications** (email admin) + recherche globale ⌘K

## Refactoring futur (urgence moyenne)
- `server.py` 1046 lignes → split en routers FastAPI
- `seed_prompts.py` 50 prompts → 4 blocs Template/Produits/SEO/Marketing
- Ajouter validation `product_id` existe dans OrderCreateInput (déjà fait côté endpoint, à déplacer en model_validator pour uniformité)

## Next tasks (après validation user)
1. Phase 4 : Admin Ops Center (commandes + export CSV)
2. Refactor server.py en routers
3. Import automatique produit depuis URL fournisseur
4. Intégration Mollie + TVA

## Credentials
Voir `/app/memory/test_credentials.md` — `admin@conceptfactory.fr` / `Factory2026!`
