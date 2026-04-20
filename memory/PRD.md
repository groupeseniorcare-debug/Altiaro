# Launch OS — Brand Factory SaaS

## Problem statement original
L'utilisateur (e-commerçant) veut créer un back-office central de type "usine à marques e-commerce" où il peut :
- Lister tous les sites e-commerce qu'il gère
- Créer un nouveau site via un bouton "Lancer un site internet"
- Suivre pour chaque site un workflow de 50 étapes (issues du playbook senior dropshipping) étape par étape
- Valider chaque étape avant que l'opérateur puisse passer à la suivante (workflow gated)
- Voir un dashboard global avec CA, budget pub, marge, ROAS de tous les sites
- Embaucher des opérateurs qui suivent le process clé-en-main pour ouvrir un Shopify, lancer le SEO, les pubs, etc.
- Modèle scalable et duplicable : chaque site = un clone du template

## Architecture
- **Stack** : FastAPI + MongoDB + React 18 + Tailwind + shadcn/ui + @phosphor-icons/react + Framer Motion + recharts
- **Auth** : JWT httpOnly cookies (access 8h + refresh 7j), bcrypt, brute force protection 15min après 5 échecs, admin seeded via .env
- **LLM** : Emergent LLM Key via emergentintegrations.LlmChat, supporte Claude Sonnet 4.5 / Claude Haiku 4.5 / GPT-5.1 / GPT-4o / Gemini 2.5 Pro, substitution automatique [NICHE]/[NOM_MARQUE]/[DOMAINE] dans le prompt
- **File upload** : multipart/form-data, stockage local /app/backend/uploads/, servi via /api/uploads/{filename}, max 15 Mo

## User personas
- **Admin (fondateur)** : voit tout, crée sites, crée users, valide/refuse étapes, saisit finances
- **Opérateur (employé/freelance)** : voit uniquement les sites qui lui sont assignés, exécute les prompts, upload livrables, soumet à validation

## Core requirements (static)
1. Auth JWT 2 rôles (admin/opérateur) ✅
2. Dashboard KPIs agrégés (CA, marge, pub, ROAS, sites actifs, % avancement, validations en attente) + chart évolution mensuelle ✅
3. Liste sites en cards avec barre progression + étape en cours ✅
4. Wizard création site (nom, niche, domaine, Shopify URL, opérateur assigné, notes) + seed auto 50 étapes ✅
5. Page SiteDetail avec timeline par phase (15 phases A→O) et 50 étapes gated ✅
6. StepPanel slide-in (prompt substitué, exécution IA, livrables URL/notes/fichiers, soumission, validation/refus admin) ✅
7. Validation queue admin (toutes les étapes awaiting_validation) ✅
8. Finances manuelles mensuelles par site (CA, ad_spend, COGS, autres coûts, commandes → calcul marge + ROAS auto) ✅
9. Users CRUD admin ✅
10. Design premium Linear/Stripe-like : beige chaud #FDFBF7, charbon #1C1917, terracotta #B84B31, Fraunces + Satoshi ✅

## What's been implemented (2026-04-20)
- Backend FastAPI complet avec 30+ endpoints (auth, users, sites, steps, validations, financials, dashboard, LLM execute, file upload)
- Seed automatique des 50 prompts du playbook lors de la création d'un site (fichier seed_prompts.py, 15 phases A→O)
- Substitution automatique des placeholders [NICHE]/[NOM_MARQUE]/[DOMAINE]/[URL_ADMIN] dans les prompts à partir des infos du site
- Frontend React avec routing, AuthProvider, ProtectedRoute, 7 pages, Layout sidebar, StepPanel slide-in
- Markdown rendering pour la réponse IA (marked)
- Gestion gracieuse de l'erreur budget Emergent LLM épuisé
- MongoDB indexes sur users.email, financials (site_id, month), steps (site_id, number)

## What's NOT implemented (phase 2)
- **Shopify API sync** (option 3B) : le user a choisi "Intégration Shopify API + Google Ads + saisie manuelle". Pour phase 2, nécessite OAuth par site + access tokens par boutique. Pour MVP, saisie manuelle uniquement opérationnelle.
- **Google Ads API sync** : idem, phase 2.
- **Password reset flow** : pas critique pour un outil interne, admin peut supprimer/recréer un user.
- **Notifications temps réel** (WebSocket/SSE) : pas dans le scope MVP.
- **Multi-niche templates** : le prompt 49-50 du playbook prévoit cette refacto template ; pas appliqué au Launch OS lui-même mais reste documenté dans le playbook pour dupliquer les sites e-commerce.

## Prioritized backlog

### P0 — Blockers
- [x] Auth + admin seed
- [x] Sites CRUD + workflow 50 étapes
- [x] StepPanel avec IA + validation
- [x] Dashboard KPIs
- [x] Finances manuelles
- [x] Users admin

### P1 — Nice to have prochaine itération
- [ ] Sync Shopify API (OAuth app Shopify + récupération auto CA mensuel)
- [ ] Sync Google Ads API (OAuth + récupération dépense campagnes)
- [ ] Notifications (email admin quand une étape est soumise)
- [ ] Export CSV des livrables d'un site (dossier complet)
- [ ] Password reset flow complet
- [ ] Recherche globale (⌘K) sur sites/étapes

### P2 — Futur
- [ ] Intégration Notion / Google Drive pour livrables externes
- [ ] Refactor en template multi-niches (CLI create-brand)
- [ ] Rapport hebdo auto généré par IA à partir des étapes validées de la semaine
- [ ] Multi-tenant (plusieurs groupes/agences sur la même instance)
- [ ] Mobile app operator (React Native)

## Next tasks
1. L'utilisateur doit recharger sa Emergent LLM Key (Profile → Universal Key → Add Balance) pour utiliser le bouton "Exécuter avec l'IA"
2. Test complet end-to-end : login admin → créer site → ouvrir étape → exécuter IA → soumettre → valider → vérifier étape suivante déverrouillée
3. Créer un utilisateur "opérateur" pour tester la restriction d'accès par rôle
4. Saisir quelques données financières pour valider le dashboard KPIs avec données réelles

## Credentials
Voir `/app/memory/test_credentials.md`
