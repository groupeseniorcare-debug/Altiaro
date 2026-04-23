# Concept Factory — PRD (Product Requirements Document)

> Document **statique** : problem statement, personas, exigences core.
> L'historique des livrables est dans **CHANGELOG.md**, le backlog dans **ROADMAP.md**.

## Problem statement original
SaaS multi-tenant d'e-commerce 100% custom (pas de Shopify) dédié à la **Silver Economy** (60+ et aidants) sur 6 marchés EU : 🇫🇷 FR · 🇩🇪 DE · 🇨🇭 CH · 🇧🇪 BE+LU · 🇬🇧 UK · 🇳🇱 NL.

- **Admin** gère Google Ads centralement, finances globales, commandes côté fournisseurs.
- **Concepteurs** montent sites, choisissent produits, traitent SAV et remboursements.
- Modèle **50% marge brute partagée** entre Admin et Concepteur.

## User personas
- **Admin (fondateur)** : voit tout, crée sites + users, gère commandes + finances globales, pilote les Ads, a accès au Dashboard Empire cross-pays.
- **Concepteur (opérateur)** : voit UNIQUEMENT ses sites, gère son catalogue, duplique ses sites, scale cross-pays, génère Ads Copy, traite SAV.
- **Client final** (public, non authentifié) : achète sur `/shop/{id}` ou `https://custom.domain` en FR/EN/DE/NL sans créer de compte.

## Architecture technique
- **Stack** : FastAPI (18+ routers modulaires) + MongoDB motor async + React 18 + Tailwind + Phosphor icons + Framer Motion + recharts
- **Auth** : JWT httpOnly cookies, bcrypt, brute force 15min, admin seeded via .env
- **LLM** : Emergent LLM Key (Claude Sonnet 4.5) via `emergentintegrations` pour Niche Analyzer, Ads Copy, Mega-Block Execute, AI Copilot
- **Site Factory** : catalogue produits i18n FR/EN/DE/NL par site + storefront `/shop/{id}` + cart localStorage + checkout → commande
- **Multi-domain** : chaque site peut brancher un domaine custom (CNAME + vérification DNS)
- **Structure backend** : `server.py` (~140 lignes orchestrateur) + `deps.py` + `seed_prompts.py` + `routes/{auth,users,sites,steps,products,orders,public_shop,niches,dashboard,meta,uploads,search,analyzer,ads_copy,duplicate,domain,scale,empire,blocks_execute,copilot}.py`
- **Data scope strict** : tout est scoped par `site_id` et filtré par `operator_id` côté Concepteur.

## Blocks logiques (depuis avril 2026 — refonte Altiaro)
Les 50 étapes du playbook sont regroupées en **8 blocs thématiques ordonnés** :
1. 📦 **Produits & Sourcing** (#1-4) — Matrice, rentabilité Ads, concurrentiel, feuille de route
2. 🎨 **Marque & Identité** (#5-7) — Nom de marque + domaine (c'est ICI que le Concepteur nomme son site), brand book, voix
3. 🏗️ **Fondations boutique** (#8-16) — Sourcing fournisseurs, juridique, config Shopify, import catalogue 20 produits
4. 🖥️ **Construction du front** (#17-24) — Template Altiaro appliqué : homepage, collection, fiche produit, checkout Mollie, pages statiques
5. 🔍 **SEO & Contenu** (#25-32) — Keyword research, 15 piliers + 30 satellites, schemas, netlinking, AEO
6. 🎯 **Conversion & CRM** (#33-39) — CRO, social proof, Klaviyo, paiement, chatbot, helpdesk, téléphonie
7. 🚚 **Opérations & SAV** (#40-42) — Logistique drop, tracking, portail retours
8. 🚀 **Acquisition & Scale** (#43-50) — Google Ads 30€/j, 100 headlines, 5 LP, GA4+CAPI, monitoring SEO, duplication, SOPs
3. 🔍 **SEO & Marque** — Positionnement/voix, SEO technique, AEO/GEO
4. 🚀 **Marketing & Scale** — Ads, Social proof, Analytics, Duplication

## Core requirements
| # | Exigence | Status |
|---|---|---|
| 1 | Auth JWT 2 rôles | ✅ |
| 2 | Dashboard KPIs | ✅ |
| 3 | Sites CRUD + wizard | ✅ |
| 4 | Workflow 50 étapes auto-progression | ✅ |
| 5 | StepPanel avec IA | ✅ |
| 6 | Monitoring Admin | ✅ |
| 7 | Finances manuelles | ✅ |
| 8 | Users CRUD admin | ✅ |
| 9 | Niche Engine 20×6 | ✅ |
| 10 | Catalogue produits i18n | ✅ |
| 11 | Storefront public multilingue | ✅ |
| 12 | Cart + Checkout + Orders | ✅ |
| 13 | Admin Ops Center | ✅ |
| 14 | Refactor monolithic → 18+ routers | ✅ |
| 15 | Niche Analyzer IA dynamique (Claude 4.5) | ✅ |
| 16 | Ads Copy Generator (RSA 15h+4d+25kw) | ✅ |
| 17 | Blocks refactor (50→4 blocs logiques) | ✅ |
| 18 | Site Duplication | ✅ |
| 19 | Multi-domain management (CNAME + DNS verify) | ✅ |
| 20 | Scale 6 pays (1 clic → N clones localisés) | ✅ |
| 21 | Dashboard Empire (KPIs cross-pays) | ✅ |
| 22 | Mega-Block Execute (4 mega-prompts) | ✅ |
| 23 | AI Copilot conversationnel (function calling) | ✅ |
| 24 | Paiement Mollie (checkout + webhook) | ✅ |
| 25 | Facturation Concepteurs (CB mandate + IBAN + cron) | ✅ |
| 26 | **Virements Admin = 50% × marge brute HT** (par Concepteur, 1er/15) | ✅ |
| 27 | `cost_price_ht` tracké sur produits + snapshot à la commande | ✅ |
| 28 | TVA multi-pays auto (FR 20 / DE 19 / BE·NL 21 / UK 20 / CH 7.7) | ✅ |
| 29 | **Sourcing CJ Dropshipping + AliExpress Affiliate (search + import 1-clic)** | ✅ |
| 30 | **Wizard 10 étapes guidées avec auto-détection d'avancement** | ✅ |
| 31 | **SEO avancé (sitemap hreflang, robots, Merchant Feed RSS, Schema.org, OG, canonical)** | ✅ |
| 32 | **CJ Dropshipping API activée (clé user) — recherche + import 1-clic fonctionnel** | ✅ |
| 33 | **Google Ads Center Admin only (OAuth2 + Keyword Planner + Campaigns list)** | ✅ |
| 34 | AliExpress Affiliate API activée | ⏳ (attente clés user) |
| 35 | Resend (emails transactionnels) | ✅ |
| 36 | **Storefront Apple/Dyson (narrative scroll + typographie premium)** | ✅ |
| 37 | OVH Domaines (recherche + achat) | ✅ (markup Mollie branché, facturation Concepteur via Mollie puis déclenchement OVH auto via webhook) |
| 38 | Prompt Studio (remplace Wizard) | ✅ |
| 39 | **Storefront splitté en composants** (`components/storefront/{Hero,Benefits,ProductGrid,Testimonials,FAQSection,FinalCTA,NarrativeProduct}.jsx` + `storefrontUtils.js`) | ✅ |
| 40 | **Emails Resend domaine acheté / échec OVH** (envoyés au Concepteur post-webhook Mollie) | ✅ |
| 41 | **Scan Express Go/No-Go** (Claude + Google Keyword Planner → verdict en 30s sur prix, volume, concurrence, rentabilité Ads) | ✅ |
| 42 | **Scan multi-marché parallèle** (6 pays UE : FR/DE/BE/NL/CH/IT) + page "Lancer un site" qui fusionne scan + sélection marchés + création via `/sites/new` | ✅ |
| 43 | **Seuil concurrence 66 → 75** + règle soft "GO avec réserve" quand concurrence > 75 mais autres critères OK | ✅ |
| 44 | **Menu Concepteur restructuré** : Dashboard / Sites / Lancer un site / Finance / Compte | ✅ |
| 45 | **Dashboard Concepteur v2** — KPIs globaux (CA, commandes, part Concepteur reçue, retours) + next events (prochain versement Mollie / prochain prélèvement Ads) + setup banner (CB + IBAN manquants) + liste sites + empty state | ✅ |
| 46 | **Finance v2** — ledger unifié (crédits/débits/versements) avec filtres site/type/période + presets rapides (7/30/90j/année) + totaux par flux | ✅ |
| 47 | **Compte v2** — édition infos société (SIRET, TVA, adresse, forme juridique, téléphone) avec validation SIRET 14 chiffres + persistance sur `billing_profiles` | ✅ |
| 48 | **Scan multi-marché asynchrone (job + polling)** — POST démarre en BG retourne <1s, GET poll les cartes qui apparaissent progressivement (fix timeout 60s ingress K8s) | ✅ |
| 49 | **Cron auto-config DNS post-OVH** — APScheduler toutes les 5 min scanne les domaines `purchased`, tente la config DNS, envoie email "🌍 domain is live", abandonne après 30 min si zone OVH pas créée (status `dns_auto_failed`) | ✅ |
| 50 | Admin Virements UI (P3) — page `/admin/payouts` déjà existante, 520 lignes, couvre preview + run-payouts + mark-paid + history | ✅ (n'était pas à recoder) |
| 51 | **Storefront monochrome éditorial** (homepage + page produit, Manifesto + BrandProcess + FounderStory + PressLogos + EditorialMosaic + Reviews) | ✅ |
| 52 | **Blog IA — pilier + satellites automatiques** (`/api/sites/{id}/blog-posts/auto-plan` background task + cross-linking + IndexNow) | ✅ |
| 53 | **Cluster SEO mensuel** (1 pilier + 4 satellites, exclusion keywords utilisés, APScheduler 1er du mois, toggle auto + déclenchement manuel, UI monochrome éditoriale) | ✅ |
| 54 | **Étape 6 — Rédaction IA des pages** (About, Contact, Livraison, Retours, FAQ en 1 run Claude, endpoint background, bouton Studio, storefront lit design.pages.*) | ✅ |
| 55 | **Widget Pulse SEO** (articles/mois, couverture keywords, score E-E-A-T par article, prochain cluster, intégré au cockpit SiteDetail) | ✅ |
| 56 | **Refactor Storefront.jsx** (extract StorefrontProduct → −40 % lignes) | ✅ |
| 57 | **Coach SEO proactif** (rule engine alertes + email Resend hebdo lundi 9h + cloche topbar cockpit) | ✅ |
| 58 | **Google Search Console OAuth** (multi-tenant, refresh_token, metrics position/clicks/CTR, UI dormante + guide setup) | ✅ (backend + UI) · ⏳ (en attente des clés Google Cloud) |

## Règles critiques
- Pas de Shopify — tout custom React/FastAPI.
- FR par défaut, mais tout prêt pour EN/DE/NL.
- Cookies httpOnly uniquement pour le JWT.
- Ne jamais supprimer `<html translate="no">` dans index.html (bug Mac Chrome auto-translate crash React).
- Emergent LLM Key via playbook, jamais en direct.

## Credentials de test
Voir `/app/memory/test_credentials.md`.
