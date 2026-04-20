# Concept Factory — CHANGELOG

Historique des sprints de développement. Le PRD.md reste la source de vérité
sur les exigences produit ; ce fichier trace uniquement ce qui a été livré.

## 2026-04-20 · Sprint 11 : Phase 5 — Paiement Mollie 💳
- **💰 Intégration Mollie complète** (`mollie-api-python==3.9.1`) avec clés test/live + profile configurés via `.env` (MOLLIE_TEST_KEY, MOLLIE_LIVE_KEY, MOLLIE_PROFILE_ID, MOLLIE_MODE).
- **3 endpoints Mollie** :
  - `POST /api/public/payments/create` → crée paiement Mollie pour une commande, retourne `{payment_id, checkout_url, mode}`. Persiste `mollie_payment_id`, `mollie_checkout_url`, `payment_method=mollie` sur l'order.
  - `GET /api/public/payments/{id}/status` → poll public pour savoir si paid/pending/failed.
  - `POST /api/webhooks/mollie` (route nommée `mollie_webhook`) → reçoit l'id, fetch via API Mollie, update l'order (idempotent, toujours 200 OK).
- **🌍 Locales par langue** : fr_FR, en_GB, de_DE, nl_NL auto-sélectionnées selon `order.language`. Support devises EUR/CHF/GBP.
- **🎨 UI storefront** : after checkout form submit → create order → create Mollie payment → `window.location.href = checkout_url`. Nouvelle route `/shop/:siteId/checkout/success` qui réutilise `StorefrontConfirmation` avec polling de statut (20 tentatives × 2s) et UI adaptative selon paid/failed/pending.
- **🛡️ Sécurité** : le webhook Mollie ne fait JAMAIS confiance au body — il fetch toujours le paiement via l'API avec la clé secrète (pattern recommandé Mollie). Forged IDs = no-op.
- Tests : 13/13 pytest iter10 + régression complète (60/60 iter9) = **73/73** + 100% frontend E2E (iteration_10.json).
- Phase 5 P1 avancée à **66%** : reste TVA multi-pays + split 50/50 runtime + SAV workflow (en attente priorisation + Resend pour emails).

## 2026-04-20 · Sprint 10 : PRD split + AI Copilot conversationnel
- **📚 Documentation split** : PRD.md (exigences statiques) + CHANGELOG.md (ce fichier) + ROADMAP.md (backlog priorisé). Plus scalable dans le temps.
- **🤖 AI Copilot conversationnel** : assistant Claude Sonnet 4.5 avec function calling maison (ReAct loop). `POST /api/copilot/chat` exécute jusqu'à 6 itérations tools → finale. 9 outils :
  - `list_my_sites`, `get_site_details`, `get_site_orders`, `get_site_products`, `search_sites`, `list_scale_family` (lecture)
  - `update_product_price`, `batch_update_prices` (écriture, ±50% max)
  - `empire_overview` (admin only)
- **📝 Sessions persistées** dans `copilot_messages` (user-scoped, ts_seq ordonné). Endpoints : `GET/DELETE /api/copilot/sessions(/id)` + `GET /api/copilot/tools`.
- **🎨 UI Copilot FAB** : bouton flottant bottom-20 right-6 gradient noir sur toutes les pages authentifiées, slide-over panel avec header, suggestions de démarrage, input multi-line, historique des sessions avec preview + delete, tool trace expandable sous chaque message assistant.
- **🔒 Auto-correction** : quand Claude hallucine un nom d'outil, le backend renvoie `{error, hint: [tools_list]}` et Claude se corrige au tour suivant (testé live).
- Tests : 16/16 iter9 + 44/44 régression = **60/60** + 100% frontend E2E (iteration_9.json, 1 low-priority warning résolu : nested button fix).

## 2026-04-20 · Sprint 9 : Dashboard Empire + Mega-Block Execute
- **🏛️ GET `/api/admin/empire`** (admin only) : agrège temps réel tous les sites. KPIs : GMV total, AOV, split 50/50 admin/concepteur, nb sites actifs, ads campaigns. Breakdown par pays (via shipping_address.country_code), familles scalées (scale_batch_id), top 5 produits cross-sites, timeseries 30j, alertes auto (no_orders_7d, domain_unverified, no_active_products, empty_catalog), commandes en attente.
- **📊 Page `/empire`** : hero KPIs (GMV, ta part 50% en carte gradient noir highlight, part Concepteurs, Empire sites), line chart recharts 30j, pie chart répartition pays, tables per-country / alerts / families / top products / pending orders.
- **⚡ Mega-Block Execute** : 4 mega-prompts Claude Sonnet 4.5 (template, products, seo, marketing) qui génèrent en 1 seul appel IA le livrable complet d'un bloc (ex: products → top 10 produits avec scoring + fournisseurs + angles marketing + plan import EU). JSON structuré persisté dans `block_outputs`. Endpoints : `POST /api/sites/{id}/blocks/{bid}/execute`, GET list/latest, DELETE.
- **🎨 UI SiteDetail** : bouton "⚡ Générer le bloc en IA" sur chaque header de bloc + badge "Livrable IA prêt" si déjà généré + modale BlockOutputModal qui render le JSON comme sections lisibles (iteratif, pas récursif — évite babel stack overflow).
- Tests : 44/44 backend (8 iter8 + 36 régression) + 100% frontend E2E (iteration_8.json).

## 2026-04-20 · Sprint 8 : Scale 6 pays (multi-country mass duplication)
- **🚀 POST `/api/sites/{id}/scale`** : duplique un site source vers N clones (1 par pays cible). Chaque clone hérite de selected_countries=[cc], primary_language mappée (FR→fr, DE→de, CH→fr, BE→fr, UK→en, NL→nl), daily_budget_eur=30. Input : `{target_countries, custom_domains?, copy_products, generate_ads_copy, tone}`.
- **🌐 Domaines custom par pays** : chaque clone peut recevoir son propre domaine (ex: `shop.de`, `shop.nl`). Validations : hostname RFC 1035, pas de doublon intra-batch, unicité cross-site (409 si déjà pris).
- **🤖 Ads Copy en background** : via `BackgroundTasks` FastAPI, génération async Claude 4.5 par clone (~30s chacun, non bloquant). Fail silently si budget LLM épuisé.
- **👨‍👩‍👧‍👦 Batch tracking** : `scale_batch_id` partagé entre siblings + `scaled_from` sur chaque clone + `GET /api/sites/{id}/scale-siblings` pour afficher la famille.
- **UI** : bouton "Scaler 6 pays" (gradient rocket) sur SiteDetail → ScaleModal 6 cartes pays (checkbox + flag + langue + devise + 30€/j + input domaine), toggles copy_products/generate_ads_copy, sélecteur de ton, récap budget total, résultat avec liens vers chaque clone.
- Tests : 13/13 pytest (9 iter7 + 4 iter7_extra) + 100% E2E frontend (iteration_7.json). Regression : 23/23 passes.

## 2026-04-20 · Sprint 7 : Site Duplication + Multi-domain
- **🔁 POST `/api/sites/{id}/duplicate`** : clone un site en 1 clic (nouveau nom, 50 étapes fresh, produits clonés en draft, orders/ads-copy NON copiés).
- **🌐 Multi-domain custom** : `GET/POST/DELETE /api/sites/{id}/domain` + `POST /api/sites/{id}/domain/verify` avec lookup DNS (dnspython) CNAME avec fallback A-records. Uniqueness garantie par index partiel Mongo. `GET /api/public/domains/resolve?host=...` pour le routage storefront public (404 si non vérifié).
- Tests : 8/8 pytest + 100% E2E frontend (iteration_6.json).

## 2026-04-20 · Sprint 6.5 : Ads Copy Generator + Blocks refactor
- **📣 Google Ads Copy Generator** : `POST /api/sites/{id}/ads-copy/generate` via Claude 4.5 → 15 headlines (≤30 chars), 4 descriptions (≤90 chars), 25 keywords, 12 negative keywords, 4 sitelinks, 6 callouts. Sanitizer server-side enforce les limites. Export CSV compatible Google Ads Editor.
- **🧩 Blocks refactor** : `seed_prompts.py` expose BLOCKS dict (template/products/seo/marketing) + PHASE_TO_BLOCK mapping. Chaque step reçoit block, block_name, block_order, block_emoji. Migration idempotente au startup (200 steps backfilled). Endpoint `GET /api/meta/blocks`.
- Tests : 15/15 pytest backend + E2E frontend (iteration_5.json).

## 2026-04-20 · Sprint 6 : Niche Analyzer IA + Sync + Mobile
- Niche Analyzer IA via Claude 4.5 (analyse 6 marchés FR/DE/CH/BE/UK/NL, verdicts GO/MAYBE/NOGO).
- Multi-market launch avec budget 30€/jour par pays sélectionné.
- Concepteurs peuvent créer leurs sites (auto-assignés).
- Resync fournisseur avec diff prix + alerte marge.
- Mobile responsive complet.

## 2026-04-20 · Sprint 5 : ⌘K + Streaming CSV
- Command Palette `⌘K` global admin (sites/products/orders/niches/users).
- Streaming CSV export O(1) mémoire.

## 2026-04-20 · Sprint 4 : Media & Import
- Scraper Open Graph + JSON-LD + Shopify Analytics.
- Import URL produit + upload images drag&drop.

## 2026-04-20 · Sprint 3 : Admin Ops Center + refactor
- 5 endpoints admin orders, page /orders, transitions status, rate-limit IP.
- Refactor server.py monolithic → modulaire (14 routers).
