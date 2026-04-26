# Altiaro — PRD (Product Requirements Document)

> **Dernière mise à jour : 2026-04-26**
>
> Document **statique** : problem statement, personas, exigences core.
> L'historique des livrables est dans **CHANGELOG.md**, le backlog dans **ROADMAP.md**,
> et l'état opérationnel de reprise dans **HANDOFF.md**.

## Problem statement original
SaaS multi-tenant d'e-commerce 100% custom (pas de Shopify) dédié à la **Silver Economy** (60+ et aidants).
Couverture : **11 pays EU** (🇫🇷 FR · 🇧🇪 BE · 🇱🇺 LU · 🇩🇪 DE · 🇦🇹 AT · 🇳🇱 NL · 🇮🇹 IT · 🇪🇸 ES · 🇵🇹 PT · 🇮🇪 IE · 🇫🇮 FI) × **6 langues** (FR, EN, DE, NL, IT, ES).

- **Admin** gère Google Ads centralement, finances globales, commandes côté fournisseurs.
- **Concepteurs** montent sites, choisissent produits, traitent SAV et remboursements.
- Modèle **50% marge brute partagée** entre Admin et Concepteur.

## User personas
- **Admin (fondateur)** : voit tout, crée sites + users, gère commandes + finances globales, pilote les Ads, a accès au Dashboard Empire cross-pays.
- **Concepteur (opérateur)** : voit UNIQUEMENT ses sites, gère son catalogue, duplique ses sites, scale cross-pays, génère Ads Copy, traite SAV.
- **Client final** (public, non authentifié) : achète sur `/shop/{id}` ou `https://custom.domain` dans l'une des **6 langues** (FR, EN, DE, NL, IT, ES) sans créer de compte.

## Architecture technique
- **Stack** : FastAPI (60 routers modulaires, 307 endpoints) + MongoDB motor async + React 19 + Tailwind + Phosphor icons + Framer Motion + recharts
- **Auth** : JWT httpOnly cookies, bcrypt, brute force 15min, admin seeded via .env
- **LLM** : Emergent LLM Key (Claude Sonnet 4.5) via `emergentintegrations` pour Niche Analyzer, Ads Copy, Mega-Block Execute, AI Copilot, traduction blog multi-langues, AEO FAQ, Citation Tracker
- **Site Factory** : catalogue produits i18n 6 langues par site + storefront `/shop/{id}` + cart localStorage + checkout → commande
- **Storefront i18n** : `LanguageSwitcher` dans le header, détection langue via `localStorage`, balises `<html lang>` dynamiques, `hreflang` multi-pays, sitemap + `llms.txt` multi-langues
- **Multi-domain** : chaque site peut brancher un domaine custom (CNAME → `sites.altiaro.com` + vérification DNS + cron auto-config toutes les 5 min)
- **Structure backend** : `server.py` (~140 lignes orchestrateur) + `deps.py` + `seo_constants.py` (source de vérité 11 pays / 6 langues) + 60 fichiers de routes dans `routes/` (voir OpenAPI sur `/api/docs`)
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
| 11 | Storefront public multilingue (FR/EN/DE/NL/IT/ES) | ✅ |
| 12 | Cart + Checkout + Orders | ✅ |
| 13 | Admin Ops Center | ✅ |
| 14 | Refactor monolithic → 18+ routers | ✅ |
| 15 | Niche Analyzer IA dynamique (Claude 4.5) | ✅ |
| 16 | Ads Copy Generator (RSA 15h+4d+25kw) | ✅ |
| 17 | Blocks refactor (50→4 blocs logiques) | ✅ |
| 18 | Site Duplication | ✅ |
| 19 | Multi-domain management (CNAME + DNS verify) | ✅ |
| 20 | Scale 11 pays EU (1 clic → N clones localisés) | ✅ |
| 21 | Dashboard Empire (KPIs cross-pays) | ✅ |
| 22 | Mega-Block Execute (4 mega-prompts) | ✅ |
| 23 | AI Copilot conversationnel (function calling) | ✅ |
| 24 | Paiement Mollie (checkout + webhook) | ✅ |
| 25 | Facturation Concepteurs (CB mandate + IBAN + cron) | ✅ |
| 26 | **Virements Admin = 50% × marge brute HT** (par Concepteur, 1er/15) | ✅ |
| 27 | `cost_price_ht` tracké sur produits + snapshot à la commande | ✅ |
| 28 | TVA multi-pays auto (11 pays EU — FR 20 / BE 21 / LU 17 / DE 19 / AT 20 / NL 21 / IT 22 / ES 21 / PT 23 / IE 23 / FI 25.5) | ✅ |
| 29 | **Sourcing CJ Dropshipping + AliExpress Affiliate (search + import 1-clic)** | ✅ |
| 30 | **Wizard 10 étapes guidées avec auto-détection d'avancement** | ✅ |
| 31 | **SEO avancé (sitemap hreflang, robots, Merchant Feed RSS, Schema.org, OG, canonical)** | ✅ |
| 32 | **CJ Dropshipping API activée (clé user) — recherche + import 1-clic fonctionnel** | ✅ |
| 33 | **Google Ads Center Admin only (OAuth2 + Keyword Planner + Campaigns list)** | ✅ |
| 34 | AliExpress Affiliate API activée | ✅ (clés OK + OAuth validé le 24/04 après fix bug `refresh_token_valid_time` ms→datetime) |
| 35 | Resend (emails transactionnels) | ✅ |
| 36 | **Storefront Apple/Dyson (narrative scroll + typographie premium)** | ✅ |
| 37 | OVH Domaines (recherche + achat) | ✅ (markup Mollie branché, facturation Concepteur via Mollie puis déclenchement OVH auto via webhook) |
| 38 | Prompt Studio (remplace Wizard) | ✅ |
| 39 | **Storefront splitté en composants** (`components/storefront/{Hero,Benefits,ProductGrid,Testimonials,FAQSection,FinalCTA,NarrativeProduct}.jsx` + `storefrontUtils.js`) | ✅ |
| 40 | **Emails Resend domaine acheté / échec OVH** (envoyés au Concepteur post-webhook Mollie) | ✅ |
| 41 | **Scan Express Go/No-Go** (Claude + Google Keyword Planner → verdict en 30s sur prix, volume, concurrence, rentabilité Ads) | ✅ |
| 42 | **Scan multi-marché parallèle** (11 pays EU : FR/BE/LU/DE/AT/NL/IT/ES/PT/IE/FI) + page "Lancer un site" qui fusionne scan + sélection marchés + création via `/sites/new` | ✅ |
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
| 59 | **Historique E-E-A-T + Badges** (snapshots hebdo, sparkline SVG, 9 badges d'achievement, rule engine) | ✅ |
| 60 | **Boost AEO/SEO** (sitemap images, llms-full.txt, Organization enrichi, Speakable FAQ, Article schema v2, IndexNow auto-submit) | ✅ |
| 61 | **Panneau AEO Readiness** (score 0-100 + checklist 7 items + bulk enrich Claude 18-22 Q/R par produit) | ✅ |
| 62 | **Maillage interne automatique** (scan blog + produits, injection liens markdown déterministe, audit orphelines + most-linked) | ✅ |
| 63 | **AI Citation Tracker** (panel Claude mesure taux de citation par les IA, sparkline historique, détail par question) | ✅ |
| 64 | **Citation Tracker scheduler** (APScheduler jeudi 08:00 UTC, opt-out `citation_auto_enabled`, gestion budget LLM) | ✅ |
| 65 | **AliExpress Weekly Deals Watcher** (APScheduler mardi 06:00 UTC, détection price drop ≥20 % + ≥500 cmd, UI cockpit avec import/dismiss) | ✅ |
| 66 | **Phase 0 — Résilience LLM (Circuit Breaker + Retry expo)** : module `services/llm_resilience.py` (419 lignes), wrappers `safe_claude_text/json` + `safe_nano_banana_bytes` + `safe_llm_text` (multi-provider) + endpoint `/api/admin/llm-health`, breakers per provider (claude, nano_banana), 3 retries (2s/8s/32s + jitter) sur 502/503/504/timeout/429, OPEN après 5 échecs consécutifs, reprise auto via cron `auto_resume_failed_jobs` toutes les 5 min, endpoint `/launch-jobs/{id}/resume` avec mode `only_degraded`, persistance `degraded_steps[]` sur `launch_jobs`, statut `completed_with_degraded`. 6 tests pytest verts. | ✅ |
| 67 | **Phase 0.5 — Migration LLM complète** (drop-in replacement de 19 routes restantes : analyzer, ads_copy, blocks_execute, blog_posts, cockpit_tools, copilot, design × 4 sites internes, google_ads_manual, platform, product_bundles, product_images, product_narrative, quick_scan, seo_automation, seo_studio, sourcing, step_side_effects, steps, testimonials_ai). `grep LlmChat( backend/routes/` = **0**. Tous les appels Claude/Nano Banana sont désormais protégés par retry + circuit breaker. | ✅ |
| 68 | **Phase 0.5 — UI LaunchProgress** : pill santé LLM (vert/orange/rouge selon `claude.state` + `recent_failures_60s`, poll 30s), liste FR-friendly des `degraded_steps[]` avec raisons, bouton "Relancer uniquement les étapes dégradées" (POST `/resume?only_degraded=true`), bouton "Reprendre la génération" (failed-resumable), bouton "Continuer vers la boutique" (completed_with_degraded), data-testids complets. Support debug `?launch_job_id=` en URL. | ✅ |
| 69 | **Phase 1 — Storefront ↔ contenu premium** : `Testimonials.jsx` lit `design.testimonials_premium` en priorité (3 portraits IA), `StorefrontPages.jsx` lit `design.cms_pages.{about,contact}` avec rendu markdown via `MarkdownLite`, fallback intelligent vers `pages.*` puis hardcoded. Bug `availableLangs is not defined` corrigé (préexistant, plantait toutes les pages CMS). Bug Hero `[object Object]` corrigé via garde dict multilingue dans `sanitizeBrandText`. Bug 403 launch.py corrigé (admin lance un site dont il n'est pas operator_id). | ✅ |

## Règles critiques
- Pas de Shopify — tout custom React/FastAPI.
- Multi-langue natif : 6 langues au choix du concepteur (FR, EN, DE, NL, IT, ES), FR par défaut.
- Séparation `seo_countries` (≤ 11 pays EU) vs `ads_countries` (pays où le concepteur achète des Ads Google) — voir `backend/seo_constants.py`.
- Cookies httpOnly uniquement pour le JWT.
- Ne jamais supprimer `<html translate="no">` dans index.html (bug Mac Chrome auto-translate crash React).
- Emergent LLM Key via playbook, jamais en direct.
- **TOUS les appels Claude/Nano Banana DOIVENT passer par `services/llm_resilience.py`** (`safe_claude_text/json`, `safe_llm_text`, `safe_nano_banana_bytes`). Plus jamais de `LlmChat(...)` direct dans `routes/` — la résilience (retry expo + circuit breaker) ne s'applique sinon pas.
- API AliExpress = `aliexpress.ds.product.get` (Dropshipping), **pas** l'API Affiliate (permissions insuffisantes pour cette app).

## Credentials de test
Voir `/app/memory/test_credentials.md`.
