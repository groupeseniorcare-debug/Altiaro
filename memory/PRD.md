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
- **Niche Engine** : 20 niches Silver Eco × 6 pays seedées idempotemment à chaque startup dans `niches` collection.

## User personas
- **Admin (fondateur)** : voit tout, crée sites (wizard lié au Niche Engine), gère users et finances, audite l'activité des Concepteurs.
- **Concepteur (opérateur)** : voit uniquement ses sites, exécute les étapes du workflow en auto-progression (plus de gating admin depuis V3), consulte le Niche Engine en lecture.

## Core requirements
1. Auth JWT 2 rôles (admin/operator) ✅
2. Dashboard KPIs (CA, marge, pub, ROAS, sites actifs, % avancement) ✅
3. Liste sites en cards avec barre progression ✅
4. Wizard création site + seed auto 50 étapes ✅
5. SiteDetail avec timeline 15 phases A→O ✅
6. StepPanel (prompt substitué, exécution IA, livrables, auto-validation) ✅
7. Monitoring Admin des étapes validées (lecture seule) ✅
8. Finances manuelles mensuelles par site ✅
9. Users CRUD admin ✅
10. **Niche Engine** catalogue 20 niches × 6 pays ✅ (NEW — 2026-04-20)

## What's been implemented

### 2026-04-20 (session fork actuelle)
- Rebranding complet "Launch OS" → "Concept Factory" (UI, titres, logs)
- Admin email changé en `admin@conceptfactory.fr` / `Factory2026!`
- **Workflow auto-progression** : le Concepteur auto-valide ses étapes, l'étape N+1 se débloque automatiquement (plus de validation admin)
- **Niche Engine** backend : collection `niches` seedée avec 20 niches enrichies (volume total, CPC moyen, KD moyen) + collection `countries` avec les 6 pays
- Endpoints `/api/niches`, `/api/niches/{slug}`, `/api/countries`
- `POST /api/sites` accepte `niche_slug` optionnel pour lier le site à une niche du catalogue
- **Niche Engine** frontend : pages `/niches` (catalogue filtrable Toutes/Top 10/HERO) et `/niches/:slug` (table 6 pays + bouton "Lancer un site")
- Pré-remplissage auto du wizard `/sites/new` via query params depuis la fiche niche + bannière "Pré-rempli depuis Niche Engine"
- Gestion gracieuse erreurs LLM : 402 budget, 504 timeout (wait_for 50s), message FR
- Testé E2E via testing_agent_v3_fork : Backend 92% / Frontend 100%, 0 bug critique

### Précédemment
- FastAPI + 30+ endpoints (auth, users, sites, steps, validations, financials, dashboard, LLM execute, upload)
- Seed 50 prompts du playbook dropshipping (15 phases A→O)
- Substitution auto placeholders [NICHE]/[NOM_MARQUE]/[DOMAINE]
- React + routing + Layout sidebar + StepPanel slide-in

## Prioritized backlog

### P0 — blockers (terminé)
- [x] Auth + admin seed
- [x] Sites CRUD + workflow 50 étapes
- [x] Niche Engine (catalogue + détail + liaison)
- [x] Auto-progression des étapes
- [x] Gestion gracieuse budget LLM

### P1 — phase 3 (prochain sprint)
- [ ] **Site Factory Template** : template React e-commerce multilingue (FR/EN/DE/NL) avec cart, checkout, account, déployé automatiquement à la création du site
- [ ] **Refactor workflow** : passer de 50 étapes rigides à 4 blocs (Template → Produits → SEO → Marketing)
- [ ] Multi-tenant routing : chaque site a son sous-domaine / domaine custom

### P2 — phase 4-5
- [ ] **Admin Ops Center** : queues Orders ("Envoyer au fournisseur"), SAV, Refunds
- [ ] **Catalogue fournisseurs DSers-like** : import depuis CJ / BigBuy / AliExpress, mapping produits → fournisseurs
- [ ] **Moteur financier** : calcul 50/50 Marge Brute Partageable, TVA multi-pays (5 taux), intégration Mollie payouts/billing
- [ ] Password reset flow

### P3 — phase 6+
- [ ] **Google Ads Center** : interface admin pour créer/gérer campagnes via API, sync dépenses
- [ ] DataForSEO integration pour recalibrer les métriques du Niche Engine avec chiffres réels
- [ ] Notifications (email/slack) SAV + alerte low stock
- [ ] Export CSV livrables d'un site
- [ ] Recherche globale ⌘K

## Refactoring futur
- `server.py` (860 lignes) → splitter en routers : `/app/backend/routes/{auth,sites,steps,niches,financials,dashboard}.py` + `/app/backend/models/` + `/app/backend/tests/`
- `seed_prompts.py` → passer de 50 prompts lourds à 4 blocs Template/Produits/SEO/Marketing

## Next tasks
1. Validation utilisateur du Niche Engine (catalogue + détail + liaison site)
2. Phase 3 : Site Factory Template (multilingue + cart + checkout)
3. Recharger l'Emergent LLM Key si l'utilisateur veut tester l'IA sur les étapes

## Credentials
Voir `/app/memory/test_credentials.md`
