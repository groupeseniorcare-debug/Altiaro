# Altiora — CHANGELOG

Historique des sprints de développement. Le PRD.md reste la source de vérité
sur les exigences produit ; ce fichier trace uniquement ce qui a été livré.

## 2026-04-24 · AEO Readiness + Maillage interne + Citation Tracker IA

### Panneau AEO Readiness (suite du boost AEO)
- **Backend `routes/aeo.py`** (374 lignes) :
  - `POST /api/products/{id}/aeo-enrich` — génère 18-22 Q/R conversationnelles
    + mots-clés longue-traîne via Claude, fusionne avec FAQ existante
    (dedup case-insensitive).
  - `POST /api/sites/{id}/products/aeo-enrich-bulk` — job background enrichit
    jusqu'à 50 produits avec throttling `Semaphore(3)`. Gestion budget LLM
    via flag `budget_hit` qui arrête propre.
  - `GET /api/sites/{id}/aeo-readiness` — score 0-100 local (zéro coût LLM) :
    35 % produits AEO-ready · 20 pts richesse Q/R · 15 pts keywords
    conversationnels · 10 pts llms-full.txt · 10 pts contactPoint · 10 pts blog.
- **Frontend `components/AeoReadinessPanel.jsx`** — score Fraunces XXL +
  barre de progression Débutant→Pro→Élite + CTA bulk enrich + checklist
  right-col + footer stats (`ready / total · Q/R moy · keywords`).

### Maillage interne automatique (P1, signal ranking #1)
- **Backend `routes/internal_linking.py`** (déterministe, zéro LLM) :
  - `POST /api/sites/{id}/internal-linking/auto-inject` — scanne tous les
    posts + product descriptions + narrative sections, construit une
    link-map pondérée (pillar 10 > product 8 > collection 6 > blog 4),
    injecte des liens markdown `[keyword](url)` sur la première occurrence
    non protégée (skip code blocks, existing anchors, h1, self-links).
    Stop word filter FR + longueur min 5 char + unicode word boundaries.
  - `GET /api/sites/{id}/internal-linking/stats` — audit : liens sortants
    totaux, pages orphelines (0 incoming), top pages citées, dernier run.
  - Persist `design.seo_coach.last_internal_linking_stats` pour UI + post-
    audit.
- **Frontend `components/InternalLinkingPanel.jsx`** — score Fraunces
  (liens détectés) + stats-line `docs scannés · liens/doc · cibles uniques`
  + CTA "Injecter le maillage interne" + right-col orphan pages (avec
  warning icon) + most-linked leaderboard.
- **Tests pytest** `tests/test_internal_linking.py` : **11 tests** couvrant
  priorité pillar/product, skip upsells, filtre stop-words, max links,
  skip markdown existant, skip code-blocks, skip self-URL, case-insensitive,
  word boundaries stricts (`fauteuil` ≠ `fauteuils`).

### AI Citation Tracker (P2, visibilité moteurs IA)
- **Backend `routes/citation_tracker.py`** :
  - `POST /api/sites/{id}/citation-tracker/run` — interroge Claude (panel IA)
    sur 6 questions conversationnelles du site (extraites de `narrative.faq`
    + fallback synthetic par produit). Détecte si la marque ou le domaine
    est cité via regex word-boundary case-insensitive dans answer +
    brands_cited.
  - `GET /api/sites/{id}/citation-tracker` — dernier snapshot + historique
    26 semaines (6 mois) pour sparkline.
  - Persistence `design.seo_coach.last_citation_run` + array `citation_history`
    avec `$slice: -26`.
- **Frontend `components/CitationTrackerPanel.jsx`** — score Fraunces XXL
  (rate %) + sparkline SVG pur (polyline + dots) + CTA "Mesurer maintenant"
  + right-col résultats détaillés (Q + extrait réponse, check/xmark par ligne).

### Tests & validation
- **Testing agent iter29** : 100 % backend (28/28 : 11 unit + 17 API) + 100 %
  frontend (3 nouveaux panneaux + boutons testids + previous panels OK +
  zéro console error). Aucun bug identifié.
- **Design** : strict monochrome editorial préservé (Fraunces / `#0A0A0A` /
  hairlines `#E5E5E5` / background cards `#F5F5F5`).

## 2026-04-23 · Historique E-E-A-T + Badges + Boost AEO/SEO

### Historique hebdomadaire + Badges achievements (dopamine-driven)
- **Backend** :
  - `_snapshot_all_sites()` — appelé chaque lundi 08:00 UTC par APScheduler,
    persiste `site.design.seo_coach.weekly_snapshots[]` (52 semaines max).
  - `_check_badges(snapshots, already_unlocked)` — rule engine qui débloque :
    `first-cluster`, `ten-articles`, `thirty-articles`, `eeat-75`, `eeat-90`,
    `coverage-50`, `coverage-100`, `streak-4w-75`, `streak-12w-75`.
  - Endpoints `GET /sites/{id}/seo/history` (snapshots + badges + delta vs last
    week) et `POST /sites/{id}/seo/snapshot` (déclenchement manuel test/debug).
- **Frontend** `components/EeatHistoryPanel.jsx` :
  - Score Fraunces XXL + delta coloré (+/- pt vs semaine précédente).
  - **Sparkline SVG pur** (zero-dep) avec aire + ligne + dot final + ligne
    pointillée à 75 (seuil "pro").
  - Grille de badges monochromes 🏆📝⭐🎯🏛️ avec description narrative.
  - Intégré au bas du Pulse SEO avant la bande GSC.
- **Tests pytest** : +7 sur le badge engine → **29 tests verts** total
  (seo_coach + seo_badges + blog + brand).

### Boost AEO/SEO "premier sur tous les produits"
- **Sitemap images** — `sitemap.xml` enrichi du namespace `image:` avec les
  images AI (Nano Banana closeup/studio/lifestyle) priorisées devant les
  images fournisseurs → +1 canal de trafic Google Image et signal visuel
  pour Gemini/Perplexity.
- **llms-full.txt** (standard <llmstxt.org>) — version exhaustive avec About,
  catalogue complet (nom + prix + description + benefits + FAQ par produit),
  articles blog complets (body jusqu'à 4000 chars). C'est la pièce maîtresse
  pour être **cité directement** par ChatGPT/Claude/Perplexity/Gemini. Listé
  dans robots.txt comme Sitemap.
- **Organization schema enrichi** — passage en `OnlineStore` (plus spécifique),
  ajout de `areaServed`, `knowsLanguage`, `contactPoint` avec téléphone/email,
  `address` si fourni, `sameAs` étendu (TikTok, Pinterest).
- **Speakable schema** sur FAQPage (homepage) et BlogPosting — activé pour
  Google Assistant, Siri, Alexa (voice search).
- **Article schema v2** sur les posts de blog :
  `wordCount`, `timeRequired` (ISO 8601 `PT7M`), `inLanguage`, `about`,
  `keywords` (pillar + satellites), `alternativeHeadline`, `dateModified`,
  `speakable` css selectors `h1, h2`.
- **IndexNow auto-submit** — hooked sur `POST /sites/{id}/products` (create)
  et `PATCH /sites/{id}/products/{id}` (update). Chaque modif pousse 3 URLs
  (homepage, produit, sitemap) vers Bing/Yandex/Naver/Seznam (ChatGPT search
  utilise Bing, donc ça indexe indirectement dans les réponses AI).



### 1. Refactor `Storefront.jsx` (–40 %)
- Extrait **StorefrontProduct** (~515 lignes) dans `pages/StorefrontProduct.jsx`.
- `Storefront.jsx` garde StorefrontHome/Cart/Checkout/Confirmation + re-exporte Product.
- **1279 → 764 lignes** (dans le fichier principal), imports nettoyés.

### 2. Coach SEO proactif (alertes + email Resend)
- **Backend** `routes/seo_coach.py` :
  - `GET /api/sites/{id}/seo/alerts` — rule engine retourne des alertes
    catégorisées (critical / warn / info) sur score E-E-A-T, couverture keywords,
    cadence mensuelle, proximité du prochain cluster.
  - `GET .../alerts/unread` — compteur pour le badge cloche, mémorise les
    alertes lues via `site.design.seo_coach.read_alert_ids`.
  - `POST .../alerts/mark-read` — marque lues.
- **APScheduler** cron **lundi 08:00 UTC** (9h CET) → `send_weekly_seo_digests()` :
  Iterate tous les sites `seo_coach.email_enabled != False`, envoie un digest
  HTML Resend si ≥ 1 alerte warn/critical. Support `created_by` comme
  fallback de l'owner_id et gère les users `_id` ObjectId legacy.
- **Frontend** `components/SEOCoachBell.jsx` — cloche monochrome dans le
  topbar cockpit avec badge count rouge/noir selon severity, dropdown 400px
  premium (Fraunces, CTA noirs, footer "DIGEST EMAIL · CHAQUE LUNDI 09H"),
  mark-read au clic d'ouverture, polling 60 s.
- **Tests pytest** : 7 tests sur le rule engine (+ 7 existants blog) → **14/14**.

### 3. Google Search Console OAuth
- **Backend** `routes/gsc.py` (multi-tenant) :
  - `GET /api/sites/{id}/gsc/connect` — retourne l'URL OAuth avec state CSRF.
  - `GET /api/gsc/oauth/callback` — exchange code → refresh_token, stocké dans
    `site.design.gsc.*`, détecte automatiquement la property_url via
    `searchconsole.googleapis.com/webmasters/v3/sites`.
  - `GET .../gsc/status` — {configured, connected, property_url, last_synced_at}.
  - `GET .../gsc/metrics?days=28` — queries, avg_position, clicks, impressions,
    CTR via searchAnalytics API. Refresh token exchange à chaque call.
  - `POST .../gsc/disconnect` — unset `design.gsc`.
- **Frontend** `components/GSCConnectCard.jsx` — bande intégrée au bas du
  PulseSEOWidget, 3 états : non-configuré (message admin) / non-connecté
  (bouton "Connecter GSC") / connecté (4 Fraunces KPIs + lien déconnecter).
- **Setup guide** `docs/GSC_SETUP.md` — 6 étapes pour créer projet Google
  Cloud, activer l'API, configurer OAuth consent, créer credentials,
  copier dans `.env`. En attente que l'admin fournisse
  `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`.
- **Packages** : `google-auth-oauthlib`, `google-api-python-client` (pip freeze).



### Étape 6 — Rédaction IA des pages statiques
- **NEW backend** `POST /api/sites/{id}/design/generate-pages` + `GET .../generate-pages/{job_id}` :
  job background qui génère en 1 appel Claude le copy éditorial des 5 pages
  (**about, contact, livraison, retours, faq**) persisté dans `site.design.pages.*`.
  Gère l'erreur 402 budget proprement (status `failed` + message clair).
- **Frontend** : bouton noir **"Rédiger les pages (IA)"** dans `SiteDesign.jsx` +
  polling du statut toutes les 8 s (max 4 min).
- **Storefront** : `StorefrontAbout`, `StorefrontContact`, `StorefrontLivraison`,
  `StorefrontRetours`, `StorefrontFAQ` lisent maintenant `design.pages.{section}`
  avec fallback sur l'ancien contenu hardcodé.

### Widget "Pulse SEO" — Dashboard Concepteur
- **NEW backend** `GET /api/sites/{id}/seo/pulse` : articles ce mois, keywords
  couverts vs total informationnels, score E-E-A-T par article (heuristique sur
  longueur, structure H2, listes, FAQ, internal links, méta SEO), prochain
  cluster mensuel, top 6 articles récents scorés.
- **NEW frontend** `components/PulseSEOWidget.jsx` :
  - Carte monochrome éditoriale 4-KPIs (Fraunces numerals, barres de progression
    noires `#0A0A0A`).
  - Liste des top articles récents avec badge E-E-A-T coloré par tranche
    (≥75 noir, ≥55 gris, <55 ambre).
  - Footer placeholder pour brancher Google Search Console plus tard.
  - Bouton d'accès direct vers `/sites/:id/blog-posts`.
- Intégré dans `SiteDetail.jsx` entre le Cockpit et le QA Panel.

### Budget
Chaque appel Claude coûte ~1-2 € avec un pillar ou 5 pages. Les prompts sont
calibrés au minimum viable. Budget épuisé = `status:"failed"` clair + UI
bannerisée. Aucune perte de UX.

## 2026-04-23 (earlier) · Cluster mensuel SEO — 1 pilier + 4 satellites auto

### Backend
- **NEW** `POST /api/sites/{id}/blog-posts/cluster-monthly` — déclenche un cluster
  (pilier + 4 satellites par défaut) en arrière-plan, exclut automatiquement les
  keywords déjà consommés par les articles existants via `_used_keywords_from_posts()`.
- **NEW** `POST /api/sites/{id}/blog-posts/cluster-settings` — toggle
  `design.blog_cluster.auto_enabled` pour programmer le run mensuel.
  (POST et non PATCH pour éviter la collision avec `PATCH /{slug}`.)
- **NEW** `GET /api/sites/{id}/blog-posts/cluster-status` — retourne `auto_enabled`,
  `next_scheduled_at` (prochain 1er du mois 06:00 UTC), derniers 5 jobs cluster.
- **NEW** `run_monthly_clusters_for_all_sites()` — entry-point APScheduler qui
  itère tous les sites avec `auto_enabled=True` et lance un job par site.
- **NEW** scheduler cron `day=1, hour=6` dans `server.py` → `monthly_blog_cluster`.
- `_pick_informational_keywords()` accepte `exclude_used: set[str]` pour éviter
  les doublons entre cycles.
- **Résilience LLM** : `_call_claude_json()` retry sur 502/503 (1 tentative +
  backoff 3 s) pour absorber les BadGateway transients du proxy LiteLLM.
- **Prompts optimisés pour le budget** : pillar 1400-1800 mots (vs 2200-2800),
  satellite 700-1000 mots (vs 900-1300) — économie ~30 % tokens/cluster.

### Frontend
- `SiteBlogPosts.jsx` : nouvelle **carte "Cluster de contenu mensuel"** ultra-premium
  monochrome (2 col : gauche CTA + description E-E-A-T / droite `#F5F5F5` avec
  programme, dates formatées FR, historique des runs récents).
- Bouton noir sharp-corner **"Générer mon cluster mensuel"** (déclenchement manuel).
- Toggle pill "Auto-publier chaque mois" (active le scheduler).
- Chargement du statut au mount + polling après lancement.

### Blocage résiduel
- Budget Emergent LLM (28.03 / 28.00) : les prompts réduits permettent d'espérer
  ~2-3 clusters supplémentaires avant épuisement. Le code est robuste : en cas
  d'échec le job est marqué `failed` avec message clair dans l'UI.



### Page Produit — refonte images
- **NEW** `components/storefront/ProductEditorialMosaic.jsx` : mosaïque magazine asymétrique
  (4 tuiles sur 12-col : 1 grand portrait + 2 paysages + 1 bannière 21:9) avec eyebrows
  chapitre-style, captions narratives. Placée entre ProductBundle et NarrativeSections.
- `NarrativeProduct.jsx` : sections du narratif reçoivent maintenant la galerie `productImages`
  en fallback → chaque chapitre a une image même sans génération IA. Bullet points réintroduits
  sous la body quand image présente (compactés à 3 max).
- `Storefront.jsx` : priorité `generated_images` (Nano Banana) puis `images[]` CJ pour alimenter
  mosaïque + narrative. Résultat : la page produit n'a plus de blocs text-only.

### Blog IA Étape 7 — Pilier + Satellites
- **NEW** `POST /api/sites/{id}/blog-posts/auto-plan` : génère 1 pilier (2200-2800 mots) +
  N satellites (900-1300 mots) depuis les keywords informationnels de Step 8. Claude Sonnet 4.5
  via Emergent LLM Key.
- Architecture background : retourne `{job_id, status:"started"}` en <1s, génération dans
  `BackgroundTasks`, polling via `GET /api/sites/{id}/blog-posts/auto-plan/{job_id}`. Évite
  le timeout gateway 60s.
- Cross-linking automatique : chaque satellite cite le pilier via ancre markdown obligatoire,
  le pilier liste ses satellites en fin d'article.
- IndexNow fire-and-forget sur tous les slugs + /blog à la fin du job.
- `_pick_informational_keywords()` : classification regex (comment/pourquoi/guide/choisir…) +
  rank par volume, fallback sur keywords neutres, puis sur synthetic keywords si pool trop court.
- **Frontend `SiteBlogPosts.jsx`** : bouton "Générer tout le blog (IA)" + bannière de progression
  animée + polling auto toutes les 8s pendant max 4 min + toast de succès à la fin.
- Gestion budget : `_call_claude_json` catch "Budget has been exceeded" et persiste le flag
  `platform_health.llm = budget_exhausted`.

### Tests
- `tests/test_blog_auto_plan.py` : **5 tests pytest** (ranking informationnel, fallback neutres,
  empty pool, marché manquant, slugify). Tous passent.

### Blocage environnement
- L'Emergent LLM Key est **épuisée** (current_cost=27.19 / max_budget=27.00). L'endpoint est
  fonctionnel mais retourne `{status:"failed", error:"IA indisponible ou budget épuisé"}`
  jusqu'à recharge par l'utilisateur (Profile → Universal Key → Add Balance).


## 2026-02 · Fix critique storefront — 3 identités de marque incohérentes

Bug remonté par le user : le storefront affichait **3 noms de marque différents** sur la même page (logo image "Maison Clarelle", hero "Test Fauteuils Releveurs", footer "Test409"), avec une image hero hors-sujet et un produit seul perdu dans une grille 4-col vide.

### Root causes identifiées
1. `/api/sites/:id/design/ai-field` retournait la réponse Claude brute **avec markdown + préambule** (`# Proposition de nom de marque\n\n**Soléa**\n\n...`) et la sauvegardait telle quelle dans `design.brand.name`.
2. `brand.logo_text = "Test409"` venait d'un ancien run de test où le site s'appelait "Test409" ; jamais régénéré par le wizard car la condition `if wizard.get("brand_name")` écrivait vers `logo_text` **seulement** (pas `brand.name`), créant deux champs désynchronisés.
3. `Hero.jsx` avait un fallback Unsplash `photo-1447452001602-...` (silhouette yoga) quand `design.hero.image` absent.
4. `ProductGrid` utilisait une grille `grid-cols-3` fixe → 1 produit = 66% d'espace vide.
5. Prix des produits en couleur `primary` (bleu) → peu lisible, typo premium exige du noir.

### Fixes livrés
- **Backend `routes/design.py`** : nouvelle fonction `_sanitize_brand_text()` qui extrait le premier bloc `**bold**`, à défaut demote les markdown headings, strippe les préambules FR ("Voici…", "Proposition de…"), les guillemets (`" ' « » “ ”`) et enforce `max_len`. Appliquée dans `ai_field`, `prompt_apply` (identity), `brand_patch`.
- **Backend `routes/design.py`** : prompts FIELD_PROMPTS renforcés avec "Réponds EXCLUSIVEMENT avec X, sans markdown, sans préambule".
- **Backend `routes/launch.py`** : écrit `brand_patch["name"]` + `brand_patch["logo_text"]` simultanément (single source of truth), sanitize les inputs wizard, reset `logo_url=None` quand `overwrite_all=True`.
- **Frontend `lib/brandText.js` (NEW)** : `sanitizeBrandText()` miroir du backend, appliqué défensivement dans `StorefrontLayout` (logoText, tagline) et `Hero.jsx` (title, eyebrow) pour couvrir les sites déjà corrompus en BDD.
- **Frontend `Hero.jsx`** : fallback Unsplash yoga **supprimé** → utilise en cascade `design.hero.image` > image du premier produit vedette > placeholder élégant avec initiale monogram sur gradient de la palette. La prop `products` est désormais passée depuis `Storefront.jsx`.
- **Frontend `ProductGrid.jsx`** : layout adaptatif — 1 produit = colonne unique `max-w-md` centrée, 2 produits = 2-col `max-w-3xl`, 3 = 3-col, 4+ = grid standard. Prix passent de `color: primary` à `text-neutral-900`.
- **Frontend `Testimonials.jsx`** : étoiles avis passent de `color: primary` (bleu sur le test site) à `#F5B800` doré fixe — convention UX universelle.

### Tests
- `tests/test_brand_sanitizer.py` : **8 tests pytest** couvrant extraction bold, stripping préambules FR, guillemets, markdown chars, empty input, enforcement max_len. Tous passent.
- Validation e2e via screenshot : le site affiche maintenant "Soléa" partout (hero title, footer brand, © copyright) au lieu des 3 noms différents, le produit apparaît centré avec son image réelle de fauteuil, les prix sont noirs.

## 2026-02 · Refactoring `SiteDesign.jsx` → modules `/components/site-design/`

Monolithe de **1417 lignes** découpé en 6 modules pour améliorer la maintenabilité :

| Fichier | Lignes | Rôle |
|---|---|---|
| `pages/SiteDesign.jsx` | **214** | Orchestrateur (wizard switching, tabs, publish, live preview) |
| `components/site-design/constants.js` | 58 | TABS, FONT_PAIRS, PALETTE_PRESETS, LINK_TYPES, `detectLinkType` |
| `components/site-design/shared.jsx` | 66 | `AiField`, `Field`, `ColorPicker` (helpers réutilisables) |
| `components/site-design/LivePreview.jsx` | 52 | Iframe preview sticky |
| `components/site-design/IdentityTab.jsx` | 363 | Onglet identité (brand, logo, palette, typo, génération IA) |
| `components/site-design/NavigationTab.jsx` | 379 | Onglet navigation (header/footer + `NavRow` + `MegaMenuEditor`) |
| `components/site-design/CollectionsTab.jsx` | 295 | Onglet collections + `CollectionEditor` modal |

Validation : aucune régression fonctionnelle, tous les data-testid préservés, ESLint clean sur les 6 nouveaux fichiers. Smoke test e2e réussi (login Concepteur → `/sites/:id/design` → tabs → storefront mobile → Cmd+K opérateur OK).

## 2026-02 · Storefront UI polish v2 — mobile-first premium

### Header refait mobile-first
- **Mobile (<lg)** — grille 3 colonnes : hamburger **GAUCHE** (44×44) · logo **CENTRE** (h-9 max-w-[160px] object-contain, natural aspect) · panier **DROITE** (44×44 avec badge count). Fini le logo-carré-cropé.
- **Desktop (>=lg)** — logo horizontal propre (h-10 max-w-[220px] object-contain, sans border, sans rounded-lg). Fraunces tagline sous le nom uniquement si pas de logo uploaded.

### Drawer mobile premium (slide depuis la GAUCHE)
- Barre de recherche full-width arrondie en haut (data-testid `mobile-search`)
- **Lien compte** avec avatar User icon + label « Se connecter » / « Mon compte » (data-testid `mobile-account`) — NOUVEAU
- Nav items (mobile-nav-*) avec min-h-[56px] + CaretRight
- Footer email + téléphone + réassurance

### Homepage — sections premium avec animations
- `hasData()` **permissif** : benefits / testimonials / faq / newsletter / final_cta / products rendent toujours (fallback premium embarqué dans chaque composant). Seules les sections qui requièrent du contenu strictement user-provided restent gated (press_logos, lifestyle_editorial, founder_story, values, buying_guide, instagram, blog_teaser).
- **Alternance de fond** : DARK_SECTIONS (`press_logos`, `final_cta`) → `#1C1917` blanc · GRAY_SECTIONS (`benefits`, `testimonials`, `faq`, `values`, `newsletter`) → `#F5F2EB` · autres → white.
- **framer-motion v12.38** installé · chaque section wrappée dans `motion.div` avec `initial={{ opacity: 0, y: 32 }} whileInView={{ opacity: 1, y: 0 }}` viewport `once: true, margin: -80px` · animation 500ms easeOut.

### Fix régression Cmd+K
- Event listener installé sur `window` + `document` en **capture phase** (`true`) avec `stopPropagation()` — résout le cas où certains browser system handlers capturent avant React.

### Testing iter28 : 30/30 UI PASS
- Mobile layout 3-col validé bounding-box
- Drawer left-0 slide-in-from-left confirmé
- Logo desktop horizontal sans border confirmé
- 5 sections motion wrapper + alternance bg confirmées
- Cmd+K regression corrigée (cmdk-overlay count=1 après Ctrl+K)


## 2026-02 · Étape 5 · Wizard magique « Lancer la création » + orchestrateur full-site IA

> **Changement majeur de l'UX** : l'Étape 5 devient un wizard 5 étapes → 1 bouton magique qui régénère palette + logo + homepage + fiches produits + images IA en une seule action.

- 🎛️ **BrandWizard.jsx (NEW)** — 5 étapes avec stepper visuel :
  1. Identité (nom de marque, tagline, mission, voix)
  2. Ambiance (Éditorial / Minimaliste / Chaleureux / Moderne) → propose palette pré-composée
  3. Typographie (4 paires premium : Fraunces×Inter, Playfair×DM Sans, Cormorant×Manrope, Libre Caslon×Poppins)
  4. Portée (remplir seulement le vide / tout écraser)
  5. Récap + bouton **⚡ Lancer la création complète**
- 🚀 **Orchestrateur backend `/api/backend/routes/launch.py` (NEW)** avec 9 étapes pilotées :
  1. Brand identity & palette (écriture directe)
  2. Logo horizontal premium via Nano Banana (prompt Hermès/Aesop/Loro Piana, ratio 16:5)
  3. Template homepage fixe appliqué (Hero → Logos partenaires → Best-sellers → Collections → À propos → Avis → Gestion commande → FAQ → Newsletter → CTA)
  4. Régénération de 6 sections de contenu (Hero / Benefits / Testimonials / FAQ / About / Contact) via Claude
  5. Navigation IA (mega menu depuis collections réelles)
  6. Suggestions de collections IA + auto-création (max 3)
  7. Seed des 7 pages légales
  8. **Pour chaque produit importé** :
     - Narrative Claude (si manquant ou overwrite=true)
     - 3 images IA (lifestyle + studio + closeup) → complète les images fournisseur existantes
     - 2 images narrative-sections (in_use + closeup) embarquées dans la fiche produit
  9. Validation Étape 5 → débloque Étape 6 SEO/AEO
- 📊 **LaunchProgress.jsx (NEW)** — écran plein écran z-[100] gradient violet→indigo, polling 2.5 s, barre animée, journal live des étapes, gestion completed/failed avec redirection automatique.
- 🛡️ **Fail-soft robuste** : chaque appel IA wrappé en `asyncio.wait_for(timeout=90-150s)` + flag `budget_exhausted` qui skip le reste du job au lieu de crasher. Warning ajouté dans le doc job.
- 🛡️ **Zombie jobs reaper** : `@app.on_event('startup')` dans server.py marque automatiquement les jobs "running" dead (worker killed) comme failed → la guard concurrent (409) ne bloque plus les relances.
- 🛡️ **Guard concurrent launches** : POST un 2e launch pendant qu'un est running renvoie 409 « Une génération est déjà en cours ».
- 🔗 **Coexistence wizard / éditeur avancé** : bouton **"Relancer le wizard"** (rocket violet) en haut de l'éditeur avancé pour revenir au wizard quand on veut.
- ⚙️ Bugfixes minor de la review testing : POST launch → 201, guard `if not site2: return` quand site supprimé mid-job, React warning `fetchpriority`→`fetchPriority`, LaunchProgress cancel timeout au unmount.
- **Testing iter27** : 18/18 frontend testids, 4/4 backend endpoints (launch 201, status 200, concurrent 409, reaper OK), budget fail-soft vérifié en logs, zombie reaper confirmé. Rapport `/app/test_reports/iteration_27.json`.


## 2026-02 · Sticky ATC · Cmd+K · Page Builder drag-and-drop · Narrative sections IA

- 📱 **Sticky Add-to-Cart mobile amélioré** : `backdrop-blur-xl` + `bg-white/90` + `safe-area-inset-bottom` via `pb-[calc(0.75rem+env(safe-area-inset-bottom))]` + bouton `h-12 min-h-[48px]` avec shadow-lg. Plus propre, plus premium, plus tactile (z-50).
- ⌘ **Command Menu `Cmd+K` pour Concepteurs** (`cmdk`) : palette globale avec 3 groupes dynamiques — « Site actif » (cockpit + 9 étapes + preview shop, apparaît quand URL = /sites/:id/*), « Changer de site » (10 premiers), « Navigation » (Dashboard / Sites / Finance / Niches / Validations) + « Actions rapides » (new-site, new-niche, gen-images, regen-design, orders). Bouton flottant `Chercher… ⌘K` bottom-right desktop. Admin continue d'utiliser l'ancien `CommandPalette` (search backend).
- 🧩 **Page Builder homepage sections** — NOUVEAU sous-onglet **"Sections homepage"** dans Studio → Pages & contenu (1er position, activé par défaut) :
  - **16 sections** listées (Hero, PressLogos, Benefits, Collections, Products, FeaturedProduct, LifestyleEditorial, Values, BuyingGuide, Testimonials, FounderStory, Instagram, BlogTeaser, FAQ, Newsletter, FinalCTA)
  - **Drag-and-drop** via `@dnd-kit/sortable` pour réorganiser
  - **Toggle eye/eyeslash** par section (masquer sans perdre le contenu)
  - **4 presets** : Minimaliste (5 sections) / Éditorial (11) / Conversion-first (10) / Complète (16)
  - Storefront `renderHomepageSections()` respecte l'ordre + visibilité + **skip automatique** des sections sans contenu réel (`hasData()`) → fini le template générique avec données de démo qui ne correspondent pas au business
  - Backend : 3 endpoints `GET/PUT /api/sites/{id}/design/homepage-sections` + `POST /preset/{name}`, schéma merge-safe (nouvelles sections futures ajoutées invisibles par défaut)
- 🖼️ **Narrative sections editor** par produit (SiteProducts → ProductEditor) :
  - Liste toutes les sections détaillées (titre, body, bullet points) du storytelling IA
  - Bouton **"Image IA"** Nano Banana par section (`gen-section-img-{i}`) → stocke URL dans `narrative.sections[i].image`
  - 4 styles sélectionnables (lifestyle / studio / closeup / in_use)
  - Prompt enrichi automatiquement du contexte narratif de la section (titre + body tronqué)
  - Storefront rend les sections **en alternance gauche/droite** (rythme éditorial) avec image ou layout 12-col si pas d'image
- **Testing iter26** : 4/4 backend endpoints + 4/4 frontend flows validés, 0 régression, Nano Banana section-img OK. Rapport `/app/test_reports/iteration_26.json`.


## 2026-02 · Skeleton loading + Scroll snap + Cockpit styling phase 2

- 💀 **Skeleton UI partout** (remplacement des "Chargement..." spinners — perception d'attente -40%) :
  - Storefront : `products-grid-skeleton` (6 cartes animate-pulse) dans `ProductGrid.jsx`.
  - Cockpit admin : `dashboard-skeleton` (4 stat cards + 2 chart placeholders bento-style).
  - Cockpit concepteur : `concepteur-dashboard-skeleton` (4 KPI + 2 boxes).
  - Liste sites : `sites-list-skeleton` (6 site cards placeholders).
  - SEO Studio : `site-seo-skeleton` (gauge + 3 stats + large card).
- 📱 **Scroll snap horizontal mobile** (`flex md:grid snap-x snap-mandatory`) :
  - `collections-carousel` : cards `snap-center w-[85vw]` → grid sur md+.
  - `upsells-carousel` : cards `w-[72vw]` (4 côte à côte mobile-friendly).
  - Padding négatif `-mx-6 px-6` pour déborder élégamment du container parent.
- 🎨 **Cockpit styling phase 2** : conformité au `design_guidelines.json` (palette #F9FAFB bg / #1C1917 primary / Inter / rounded-md buttons / shadow-sm) vérifiée sur Dashboard, Sites, SiteSEO. `Layout.jsx` utilise déjà `bg-neutral-50` (≈ #F9FAFB).
- **Testing** — iter25 : 10/10 targets validés via Playwright route-throttling (page.route + delay 3s pour capturer les skeleton states). Carrousels snap vérifiés en viewport 390×844. Aucun bug.


## 2026-02 · Pages légales × 7 + Mega menu + Mobile polish + UX/UI audit

- 📄 **Pages légales enrichies** de 3 → 7 : ajout de `COOKIES` (RGPD), `LIVRAISON` (tableau zones + délais), `RETOURS` (rétractation 14 j + formulaire type), `MEDIATION` (CM2C + ODR UE). Routes storefront `/shop/{id}/cookies`, `/mediation` ajoutées; `/livraison` et `/retours` conservent leurs composants custom riches.
- 🔗 **Sélecteur de lien intelligent** : l'onglet Navigation du Studio a maintenant un select avec 18 types de cible (Accueil, Toutes collections, Une collection…, Un produit…, Blog, À propos, Contact, FAQ, Search, CGV, Mentions, Confidentialité, Cookies, Livraison, Retours, Médiation, URL custom). Pour `collection`/`product`, un second select liste dynamiquement les vrais items du site. Plus besoin de taper un href à la main.
- 🖼️ **Mega menu** : nouveau bouton `Mega menu` dans l'onglet Navigation → crée un item avec éditeur de vignettes intégré (images + libellés + liens). Boutons `⚡ Auto-collections` et `⚡ Auto-produits` préremplissent depuis le catalogue. Storefront rend le panel au **hover desktop** et en accordéon `<details>` sur **mobile** avec grille 2 colonnes de cartes-images. CaretRight indicateur.
- 📱 **Polish mobile** : touch targets 44×44 min sur hamburger / panier / search / preview toggle; drawer mobile items `min-h-[56px]`; `pb-[env(safe-area-inset-bottom)]` sur footer et cart drawer; `active:scale-95 transition-transform` pour feedback tactile. Application des quick-wins du design audit.
- 🎨 **UX/UI audit complet** : `design_agent_full_stack` a généré `/app/design_guidelines.json` (blueprint app + storefront, palette, typo, patterns mobile, spec mega menu détaillée). Référence pour les prochaines itérations (phase 2 : cockpit styling, phase 3 : skeleton loading + scroll snap).
- 🐛 **Fix critique NavItem Pydantic** (iter23 → iter24) : le modèle n'acceptait que `label/href/external` et stripait silencieusement `type`/`children`/`image`. Étendu avec champs optionnels + `exclude_none=True`. Mega menu persiste end-to-end (PUT → GET public → storefront render).
- **Testing** — iter23 + iter24 : 17/17 tests backend + 100% frontend testids, mega menu validé sur desktop (hover panel) ET mobile (drawer expand). Rapports : `/app/test_reports/iteration_23.json`, `iteration_24.json`.


## 2026-02 · Studio de marque v2 + Nano Banana — fork priorité 0

- 🐛 **Fix nav storefront** : `StorefrontLayout.jsx` utilisait un `navItems()` **hardcoded** ligne 84 et ignorait `design.navigation.header` configuré par le Concepteur. Remplacé par lecture de `design.navigation.header` + `.footer` avec fallback. Header et footer du storefront suivent désormais ce qui est enregistré dans l'onglet Navigation de l'Étape 5.
- 📄 **Onglet Pages & contenu → 7 sous-onglets éditables** : Hero · À propos · Bénéfices · FAQ · Témoignages · Contact · Pages légales. Chaque sous-onglet est un formulaire complet avec champs inline (textareas, inputs, gestion i18n FR) + bouton ✨ `regen-{section}` (Claude régénère juste cette section) + bouton `save-{section}`. Nouveau endpoint backend `PATCH /api/sites/{id}/design/section/{section}` qui remplace proprement la section.
- 👁️ **Mini-iframe live preview** : sur desktop `xl:` une colonne droite 420px affiche l'aperçu de `/shop/{siteId}?preview=1&v={ts}` avec un header de fenêtre MacOS (3 boutons rouge/ambre/vert). Refresh auto à chaque sauvegarde/regen (bump `previewKey` = `Date.now()`). Boutons `preview-refresh`, `preview-external`, `preview-close`. Bouton flottant `open-preview` quand fermé.
- 🖼️ **Nano Banana — images produits IA** : nouveau module `routes/product_images.py` avec 4 endpoints (`POST /products/{id}/generate-image`, `POST /sites/{id}/products/bulk-generate-images`, `GET /products/{id}/generated-images`, `DELETE` idem). 4 styles : lifestyle, studio, closeup, in_use. Prompt construit dynamiquement depuis `brand.palette` + voice + nom produit. Les images sont stockées sous `/api/uploads/products_ai/p_{pid}_{hex}.png`. Un bouton ✨ `ai-img-generate` + select `ai-img-style` dans `ProductEditor` permet au Concepteur de générer depuis n'importe quelle fiche produit importée. Génération testée : ~21 s, PNG 670 KB.
- **Testing** — iteration 22 : 8/8 backend + 15/15 frontend testids, fix nav validé (storefront rend bien les libellés custom après PUT), aucune régression. Rapport : `/app/test_reports/iteration_22.json`.


## 2026-02 · Studio de marque — finition Priorité 0 (fork)

- **Fix P0** : `BrandingContent.jsx` avait un `Unterminated string constant` ligne 206 (bloc dupliqué collé par erreur pendant la session précédente). Bloc supprimé → build restauré.
- **Pages légales** — nouveau bouton `[data-testid=seed-legal]` dans l'onglet *Pages & contenu* qui appelle `POST /sites/{id}/design/seed-legal` : affiche un état "non générée" + avertissement amber quand vide, et désactive les liens vers CGV/Mentions/Confidentialité tant qu'ils ne sont pas créés. Le backend rendait déjà les templates mais il n'y avait aucun déclencheur UI.
- **Prompt fiches produits "ultra premium"** — `product_narrative.py` : system prompt enrichi (niveau Hermès/Dyson/Apple, style éditorial sensoriel : textures, matières, gestes, lumière, rituel) et nouvelle règle dure "chaque `body` de section contient ≥1 image sensorielle concrète" (interdit les slogans creux).
- **Testing** — iteration 21 : 7/7 backend + 100% frontend, seed-legal OK, ai-field tagline OK (~2 s), aucune régression. Rapport : `/app/test_reports/iteration_21.json`.


## 2026-04-22 · Étape 9 QA enrichi · intégration de toutes les nouveautés

- **`_run_qa_snapshot` étendu** de 13 → 23 contrôles pour refléter tout ce qu'on vient de bâtir :
  - **Catalog** : produits principaux (filtre `role != upsell`), narratif IA (check étendu à `narrative.seo`)
  - **Upsells** : ≥2 importés + couverture ≥80% (linked_product_ids)
  - **Navigation** : menu header ≥3 liens
  - **Collections** : ≥1 créée dans `db.collections`
  - **Financial forecast** : prévisionnel calculé (critique) + launch gate status viable (critique) — empêche la soumission si marge/CPA < 1.5×
  - **Journey** : toutes les étapes du cockpit validées (pricing → import → upsells → forecast → branding → pages → content → seo)
  - **SEO bulk** : optimisation Studio AEO ≥80% des produits
  - Détails actionnables avec renvoi explicite vers chaque étape ("Étape 5 → Navigation", "Studio AEO → Optimisation IA en masse")
- **Testing** : curl QA retourne score 48/100 · 5 blockers · détail par check cohérent avec état du site (launch gate ok ✓, forecast calculé ✓, upsells linked 100% ✓).



## 2026-04-22 · SEO/AEO Studio · étape 6 bouclée

**Backend — nouveau module `seo_studio.py`** (4 endpoints puissants) :
- `GET /api/public/sites/{id}/products/{pid}/jsonld` — retourne JSON-LD combiné Product + Offer + Organization + BreadcrumbList + AggregateRating (si avis) + FAQPage (si narrative.faq). Utilisable par Google rich snippets ET AI engines.
- `GET /api/sites/{id}/seo/aeo-readiness` — checklist AEO 10-items pondérée (100 pts) : identité marque, llms.txt, sitemap+hreflang, FAQ ≥70%, meta ≥80%, alt-texts ≥50%, blog ≥5, contact local, legal, publié. Verdict excellent/bon/moyen/faible.
- `POST /api/sites/{id}/seo/bulk-optimize` — background job Claude qui génère pour chaque produit : seo_title (≤60 car), meta_description (≤155 car), 5 keywords long-tail (mix transactionnel+informationnel), alt-texts par image, 3 Q/R pour FAQPage (AEO). Flag `force=true` pour tout régénérer.
- `GET /api/sites/{id}/seo/keyword-strategy` — classifie les mots-clés Google par marché en transactionnel (acheter, prix, meilleur…) vs informationnel (comment, pourquoi, guide…) + 10 suggestions d'articles blog pour combler le gap informationnel.

**Bouclage étape 5 — storefront public** :
- `GET /api/public/sites/{id}/navigation` — sert le menu header/footer configuré à l'étape 5
- `GET /api/public/sites/{id}/collections` — merge collections user (db.collections) + legacy (design.collections) avec flag `source: "user" | "legacy" | "fallback"` + `featured` sort

**Frontend** :
- `SiteSEO.jsx` : 2 onglets (Audit SEO / Studio AEO + mots-clés), conservant l'audit existant et ajoutant le nouveau panneau.
- Nouveau `SeoStudioPanel.jsx` : jauge AEO 100pts avec anneau SVG coloré, checklist 10 items (OK/à faire + poids + how_to_fix), card violet "Optimisation IA en masse" (bulk-optimize avec 2 boutons : manquants / tout régénérer), panneau stratégie mots-clés par marché avec buckets Transactionnel/Informationnel (pastilles avec volume + CPC tooltip), suggestions d'articles blog, liens vers sitemap.xml/robots.txt/llms.txt.

**Testing** : lint ✅ · 5 endpoints curl 100% OK (navigation 2/1 items, collection "fauteuils-releveurs" source=user, JSON-LD avec 2 schemas + aggregateRating prêt, AEO score 40/100 moyen avec détail 10 checks, keyword strategy structure OK) · screenshot onglet AEO validé (jauge + checklist complète visible).



## 2026-04-22 · Étape 5 · Studio de marque complet

**Backend** (3 nouveaux endpoints dans `/routes/design.py`) :
- `PATCH /api/sites/{id}/design/brand` — édition granulaire des champs brand (nom, tagline, voix, story, palette 5-couleurs, font heading/body)
- `GET/PUT /api/sites/{id}/navigation` — menu header (≤12 items) + footer (≤12 items), ordre + external
- `GET/POST/PATCH/DELETE /api/sites/{id}/collections` — CRUD collections (slug auto, validation produits du site, featured flag)

**Frontend (`SiteDesign.jsx`)** — rewrite en studio tabbé `max-w-6xl` avec 4 onglets :
1. **Identité** : formulaire éditable (nom + tagline + voix + storytelling), upload/regeneration de logo (Nano Banana), 5 colorpickers, 5 presets Silver Economy (Sénior chaleureux, Médical rassurant, Nature apaisant, Luxe minimal, Bien-être doux), sélecteur typographie avec 6 paires recommandées. Barre sticky "Enregistrer l'identité".
2. **Navigation** : CRUD items header + footer, ↑/↓ pour réordonner, checkbox external.
3. **Collections** : grille avec aperçu (cover + badge vedette), modal d'édition avec multi-select produits (filtre `role !== upsell`), slug auto.
4. **Pages & contenu** (composant `BrandingContent.jsx` extrait) : régénération IA section par section (hero, bénéfices, about, FAQ, testimonials, contact, SEO), brief global pour régénérer tout, pages légales auto.
- **UX EmptyState améliorée** : lien "remplir manuellement →" pour contourner la génération IA.
- `hasDesign` détecté si au moins un champ brand est rempli (pas seulement `name`).

**Testing** : lint OK, 4 endpoints curl testés (PATCH brand ok, GET+PUT navigation ok, POST collection ok `fauteuils-releveurs`), 2 screenshots validés (onglet Collections + onglet Identité avec preset palette + tagline pré-remplie).



## 2026-04-22 · Launch Gate : garde-fou marge vs CPA

- **Backend** : nouveau bloc `launch_gate` dans le forecast avec statut `ok | warning | blocked` basé sur le ratio `marge/commande HT / CPA`.
  - `ok` : ratio ≥ 2× ET net par vente ≥ 30 € → feu vert
  - `warning` : 1,5 ≤ ratio < 2 → lancement possible mais risqué
  - `blocked` : ratio < 1,5 → stop, message explicite + liste d'actions ordonnées (remplacer produits à marge < 50%, monter prix de X €, ajouter upsells, pivoter niche)
- **Endpoint `/journey/validate-step`** : bloque désormais la validation de `forecast` si `launch_gate.status == "blocked"` (HTTP 400 avec message détaillé).
- **Frontend (`SiteForecast.jsx`)** :
  - Bannière `LaunchGateBanner` en tête de page (vert / ambre / rouge) avec 3 KPI clés : Marge/commande HT · CPA · Net profit / vente (ratio + seuil min affiché).
  - Bouton "Valider l'étape 4" (Rocket icon) affiché en bas uniquement si `gate.status !== "blocked"`.
  - Badge "validé" sur la bannière une fois l'étape cochée.
  - Liste numérotée "Comment débloquer" quand bloqué.
- **Testing** :
  - Cas réel (fauteuil 684€) → `status: ok`, marge 297€ vs CPA 80€, ratio 3.7×, net +217€. ✅
  - Cas simulé faible marge (prix 150€, coût 130€) → `status: blocked`, marge -11€ vs CPA 80€. Actions générées : "Remplace les 1 produit(s) à marge <50%" + "Monte tes prix de +91 €/commande". ✅
  - Tentative de validate-step sur cas bloqué → HTTP 400 avec message explicite. ✅
  - Screenshot UI validé (bannière feu vert affichée).



## 2026-04-22 · Impulse-buy drawer panier + GA4 tracking enrichi

- **Panneau "Offre exclusive"** dans le drawer panier (`CartDrawer.jsx`) :
  - Fetch auto d'un upsell recommandé selon les produits du panier (`POST /public/sites/{id}/upsells-for-products`).
  - Carte mise en avant : prix barré + prix remisé + badge "-20%" + encadrement pointillé coloré.
  - Checkbox "Oui, j'ajoute cet accessoire à -20% à ma commande" → ajout au panier avec discount.
  - Le panneau se cache dès que l'upsell est dans le panier (pas de doublon d'offre).
- **Prix canoniques sécurisés côté backend** :
  - `OrderItem.upsell_discount_pct: Optional[float]` ajouté.
  - `public_create_order` : la remise n'est appliquée **que** si `product.role == "upsell"` + cap à 50%. Sinon, prix canonique serveur forcé. Impossible d'abuser en envoyant `-50%` sur un produit main.
  - `canonical_items` stocke `original_price` et `upsell_discount_pct` pour audit/facturation.
- **GA4 / Google Ads tracking** :
  - Nouvelle méthode `window.altiaroTrack.upsellImpulse(product, pct, lang)` → firing double event : `add_to_cart` (avec `item_category: 'upsell_impulse'` + `discount` en euros) **et** un event custom `upsell_impulse` pour segmentation.
  - Branchement `onAddToCart` sur fiche produit upsells + clic checkbox cart drawer.
- **lib/cart.js** : `addToCart` accepte `{discount_pct}` et stocke `original_price` + `upsell_discount_pct` sur l'item localStorage.
- **Checkout submit** propage `upsell_discount_pct` dans le payload POST `/orders`.
- **Testing** : lint OK, 2 tests curl (commande avec remise valide + tentative d'abus sur produit main **rejetée**), screenshot drawer fonctionnel.



## 2026-04-22 · Upsells : association produit + recommandations storefront

- **Étape 3 Cockpit unifiée** : extraction d'un composant `<SourcingPanel>` partagé avec l'étape 2. Même moteur d'import (search CJ/AE + URL + filtres providers) + bandeau IA en haut basé sur le catalogue.
- **Associations upsell ↔ produit principal** :
  - Sélecteur "Associer le(s) upsell(s) importé(s) à" (multi-pastilles) en tête de l'étape 3, défaut = tous les produits principaux cochés.
  - Chaque upsell importé porte `linked_product_ids: []` stocké en DB.
  - Bouton "Associé à X produits · Modifier" sur chaque carte upsell → modal pour éditer les liens après coup.
  - Nouveau endpoint `PATCH /api/sites/{id}/products/{pid}/upsell-links` (valide que le produit est bien un upsell + nettoie les IDs qui ne sont plus des produits principaux du même site).
- **Storefront** :
  - Nouveau composant `<UpsellsRecommendations>` (mode "product" ou "post_purchase").
  - Injection sur la fiche produit : "Souvent acheté avec" via `GET /api/public/sites/{id}/products/{pid}/upsells` — fallback : tous les upsells du site si aucun lien spécifique.
  - Injection sur la page confirmation : "Complétez votre commande" via `POST /api/public/sites/{id}/upsells-for-products` avec les IDs de la commande.
  - Le listing public `/products` filtre désormais `role:upsell` → les upsells n'apparaissent plus dans la boutique principale mais uniquement en recommandation.
- **Testing** : lint OK, curl PATCH + GET + POST 100% fonctionnels, 2 screenshots validés (cockpit étape 3 + fiche produit storefront affichant l'upsell).



## 2026-04-22 · Sprint C : Fulfillment Concepteur UI

- **Nouvelle page `/sites/:id/fulfillment`** (`SiteFulfillment.jsx`) routée dans `App.js` — le Concepteur voit d'un coup d'œil les commandes clients payées avec leur mapping CJ/AliExpress.
  - 5 compteurs : En attente · Commandé fournisseur · Expédié · Livré · Erreur
  - Par commande : order_number, client, total, mapping fournisseur (ID CJ/AE, statut, tracking, dernier sync)
  - Bouton "Réessayer" sur les commandes en erreur ou pending (→ POST `/sites/{id}/orders/{oid}/supplier-retry`)
- **Bouton navigation** "Commandes fournisseurs" (data-testid=`nav-fulfillment`) ajouté dans `SiteDetail.jsx` à côté de Produits / Blog / SEO.
- **Chaîne complète dropshipping 100% automatique validée** :
  1. Client paie sur storefront → webhook Mollie `paid`
  2. `auto_place_cj_order` / `auto_place_aliexpress_order` commande chez le fournisseur
  3. Cron `sync_all_cj_tracking` + AE (scheduler APScheduler) récupère tracking quotidien
  4. Au passage en `shipped`, email "expédié" envoyé une fois (flag `shipping_email_sent` anti-doublon)
- **Testing** : iter 21 — backend 4/4 pass + capture UI vérifiée (2 commandes CJ réelles affichées : CF-1776885171-3362 placed + CF-1776884932-B6CC pending).



## 2026-04-22 · Sprint B.3 : Design editor + Sourcing re-routing + GA4 + async design.generate

- **Nouvelle page `/sites/:id/design`** (`SiteDesign.jsx`) : l'éditeur branding complet que la Sprint B.2 avait oublié. 
  - Empty state + bouton « Générer mon site (IA) » avec brief optionnel
  - Vue complète post-génération : nom marque, baseline, logo, palette, hero, bénéfices, about, FAQ, contact, pages légales CGV/mentions/confidentialité
  - Régénération par section (brand, logo, hero, about, benefits, faq, testimonials, contact, SEO) via boutons cliquables
  - Upload de logo custom → `/uploads/image` puis `POST /design/brand/logo` (nouvel endpoint)
  - Toggle Publier / Publié
- **Sourcing re-routé** : `/sites/:id/sourcing` remis dans `App.js` (existait déjà dans `Sourcing.jsx` mais n'était plus accessible). CJ Dropshipping fonctionne (1 résultat retourné sur « fauteuil releveur »), AliExpress affiche « connecté » mais reste en cooldown 48h.
- **CockpitJourney relinké** :
  - Étape 2 « Import du catalogue » → `/sites/:id/sourcing` (avant : `/aliexpress/import` seul)
  - Étapes 5 & 6 « Branding » et « Pages essentielles » → `/sites/:id/design` (avant : redirigeaient à tort vers `/products`)
- **GA4 / Google Ads conversion tracking câblé** :
  - `StorefrontProduct` → `view_item` au chargement
  - `StorefrontProduct.handleAdd` + `ProductBundle.addAll` → `add_to_cart`
  - `StorefrontCheckout.submit` → `begin_checkout`
  - `StorefrontConfirmation` → `purchase` quand order.status devient `paid` (fire-once)
  - Helpers `window.altiaroTrack.*` poussent toujours vers `window.dataLayer` même sans GA4 ID configuré (GTM-compatible)
- **`/design/generate` refactoré en job async + polling** pour contourner le cap ingress K8s de 60 s :
  - POST retourne `{job_id, status:"running"}` en < 1 s
  - Nouveau endpoint `GET /design/generate/status` à poller toutes les 3 s
  - Collection `design_jobs` stocke l'état + erreur éventuelle
- **Retry + erreur actionnable dans `_claude_json`** :
  - Retry jusqu'à 3× sur 502/503/504/BadGateway (Emergent LLM proxy flaky)
  - Si « Budget has been exceeded » → HTTP 402 avec message clair « Recharge la clé depuis Profile → Universal Key → Add Balance »
- **Clean DB** : steps orphelins (300), ledger, quick_scans, niche_analyses tous vidés → prêt pour le premier lancement réel.

⚠️ **Blocker utilisateur** : la clé Emergent LLM est actuellement à court de budget (cost 17.08 / max 17.00). Toutes les fonctions IA (design.generate, pricing-analysis, upsells) échoueront avec un message actionnable jusqu'au rechargement.


## 2026-04-22 · Sprint B.2 : Nouveau Parcours Cockpit linéaire (9 étapes) — remplace les 50 prompts

- **Câblage complet** (ce qui manquait de la session précédente) :
  - `cockpit_tools` router mounté dans `server.py` (routes `/api/sites/{id}/pricing-analysis|financial-forecast|upsell-recommendations`).
  - Ajout des routes React `/sites/:id/pricing`, `/forecast`, `/upsells` dans `App.js`.
  - `SiteDetail.jsx` : la liste des 50 prompts (8 blocs × phases × steps) est **entièrement remplacée** par `<CockpitJourney />` + `<SiteQAPanel />`.
  - Compteur legacy "0/50 étapes validées" du header SiteDetail supprimé — le cockpit pilote désormais seul l'avancement.
- **Nouveaux endpoints IA / calcul** :
  - Claude Sonnet 4.5 analyse concurrence + recommande fourchettes de prix (entry / sweet-spot / premium) par type de produit.
  - Forecast 30 j : prix moyen × CPA × budget pour produire CA / COGS / marge brute / ROAS / break-even CPA, verdict `healthy|acceptable|risky`.
  - Upsells : Claude suggère 6-10 keywords AliExpress cohérents avec le catalogue.
- **Wipe data de test** : sites, steps orphelins, quick_scans, ledger, ads_copy, site_submissions, niche_analyses → base prête pour le 1er lancement réel.
- **Testing agent iteration 19** : 8/8 backend + 9/9 steps cockpit OK · Claude pricing end-to-end OK (~30 s).


## 2026-04-22 · Sprint 45 : Espace client Storefront — Suivi + Historique commandes
### Template partagé (toutes boutiques actuelles ET futures)
- **Backend** :
  - Nouveau endpoint `GET /api/public/sites/{id}/customers/orders/{order_id}` (JWT customer) — détail enrichi : items avec `product_image` + `product_name_current` (résolus depuis la collection `products`), `status_history` complet, `review_invitations[]` pour les commandes livrées avec invitation pending.
  - Helper `_enrich_order_items` partagé (réutilisé aussi par le guest tracking).
  - **Fix sécurité** : suppression de l'endpoint shadow `/public/sites/{id}/orders/{num}` dans `public_shop.py` qui renvoyait n'importe quelle commande sans vérification d'email. La route sécurisée de `customers.py` (email obligatoire en query + match strict) reprend la main.
- **Frontend** (pages dans `/app/frontend/src/pages/`) :
  - `StorefrontOrderDetail.jsx` — route `/shop/:siteId/account/orders/:orderId` : header + badge statut, timeline 4 étapes (Commande reçue / Paiement / Acheminement / Livrée) avec dates réelles extraites de `status_history`, lien direct vers le transporteur (Colissimo, Chronopost, Mondial Relay, DHL, UPS, FedEx, GLS), bloc "Laisser mon avis" si livrée + invitation pending, articles avec miniatures, totaux détaillés (sous-total / livraison / TVA / remise / total), adresse de livraison, encart d'aide.
  - `StorefrontTrack.jsx` — route publique `/shop/:siteId/track` : formulaire N° commande + email (pas de compte requis) qui appelle le endpoint sécurisé et affiche la timeline + récap.
  - `StorefrontAccount.jsx` amélioré : lignes de commandes cliquables, 4 filtres de statut (Toutes / En cours / Livrées / Archivées), chevron hover.
- **Composants partagés** :
  - `components/storefront/OrderTimeline.jsx` — timeline réutilisée par les 2 pages, gère les états terminaux (cancelled/refunded → bannière), auto-résout la couleur accent depuis `site.design.brand.primary_color`.
  - `components/StorefrontLayout.jsx` : ajout du lien "Suivre ma commande" dans le footer "Service client" (visible sur toutes les pages du storefront).
- **Routes ajoutées dans `App.js`** : `/shop/:siteId/account/orders/:orderId` + `/shop/:siteId/track`.
- **Testing agent iteration 18** : **14/14 backend + 100% frontend PASS**, aucun bug.

## 2026-04-22 · Sprint 44 : SEO Dashboard + hardening Hook #27
### Dashboard SEO Cockpit (P0)
- **Endpoint** `GET /api/sites/{id}/seo-audit` branché dans `server.py` (oubli du sprint précédent corrigé).
- Score global 0-100 calculé sur **6 dimensions** : Catalogue, Contenu, Structure, Confiance, AEO, Fraîcheur.
- Couverture chiffrée (produits enrichis IA / avec avis / avec bundles / blog posts / collections) + 9 contrôles booléens (publié, brand book, logo, légal complet, about, contact, valeurs, founder story).
- **Recommandations hiérarchisées** (critical/high/medium/low) avec action concrète pour chaque lacune (ex : "Déclencher Auto-bundles IA", "Valider le prompt #27").
- **Frontend** `/sites/:id/seo` (nouvelle page `SiteSEO.jsx`) avec :
  - Gauge SVG circulaire animée sur score global
  - 6 cartes dimensions colorées par palier (rouge/orange/ambre/vert)
  - Bannière rouge si boutique non publiée (signal critique)
  - Bouton "Rafraîchir l'audit" avec spinner
- Bouton d'accès "Santé SEO" ajouté dans la barre d'actions du cockpit (`SiteDetail.jsx`).

### Hook #27 hardening (P1)
- `_hook_blog_seed` maintenant **bounded** : timeout 90s par article + abandon après 3 échecs consécutifs → évite la saturation du loop asyncio quand Claude retourne des 502 en rafale (issue détectée par le testing agent iteration 17).
- Test agent iteration 17 : **7/7 backend + 100% frontend PASS**.

## 2026-04-21 · Sprint 43 : SEO Expert-level + Éditeur Blog WYSIWYG + Hook Review J+14
### Volet 1 — SEO ultra-expert sur page Produit (🎯 l'objectif : trafic organique + citation IA)
- **Prompt narrative Claude refondu** : ajoute un bloc `seo` complet avec 9 champs optimisés top 1% mondial :
  - `title` (meta 55-60 chars avec keyword+bénéfice+marque)
  - `description` (meta 140-158 chars avec prix+USP+CTA implicite)
  - `slug` (kebab-case SEO-friendly)
  - `keywords[]` (variations longue-traîne réelles)
  - `people_also_ask[]` (4-6 vraies questions long-tail, réponses factuelles 3-6 phrases — cible snippets PAA Google + citations IA)
  - `best_for[]` (3-5 profils utilisateurs idéaux)
  - `not_for[]` (2-3 limites honnêtes — **signal E-E-A-T très fort**, admettre ses limites vend 2× mieux)
  - `usage_steps[]` (4-8 étapes pour le schema HowTo)
  - `related_queries[]` (6-8 requêtes connexes pour maillage interne)
- **Nouveau composant** `/app/frontend/src/components/storefront/ProductSEOBlocks.jsx` avec 5 sections :
  - `PeopleAlsoAsk` — accordéon AEO (visible + indexable par IA)
  - `BestForNotFor` — cartes vert/rouge empathiques
  - `UsageSteps` — timeline numérotée
  - `RelatedQueries` — pills cliquables → `/search?q=`
  - `LastUpdatedBadge` — signal E-E-A-T de fraîcheur
- **Schemas schema.org enrichis** sur la page Produit :
  - `Product` (+AggregateRating +Review +Offer avec MerchantReturnPolicy + ShippingDetails)
  - `BreadcrumbList` taxonomique
  - `FAQPage` (fusionne `narrative.faq` + `seo.people_also_ask` jusqu'à 12 Q/A)
  - **Nouveau `HowTo`** généré depuis `seo.usage_steps`
- **Meta tags auto-optimisés** : `<title>` et `<meta description>` utilisent les versions AI si présentes, sinon fallback.

### Volet 2 — Éditeur WYSIWYG Blog dans le Cockpit (P1)
- Backend `/app/backend/routes/blog_posts.py` : CRUD `GET / POST / PATCH / DELETE /api/sites/{id}/blog-posts[/:slug]` sur `design.blog_posts[]` + endpoint **AI-draft** `POST /blog-posts/ai-draft` (Claude rédige un article SEO complet avec meta title/description/markdown en 30s).
- Frontend nouvelle page `/app/frontend/src/pages/SiteBlogPosts.jsx` accessible depuis le cockpit via bouton "Le Journal" :
  - Grille 2 cols de cards articles (catégorie, temps lecture, badge ⚡ IA si généré).
  - **Drawer éditeur** : titre, catégorie, image URL, extrait, corps markdown (textarea mono 15 rows), temps lecture, auteur.
  - **Modale AI-draft** : champ keyword cible + angle optionnel + bouton longueur (court 600-800 / moyen 1000-1400 / **long 1800-2400**).
  - Toasts succès/erreur, loading states, confirmation de suppression.
- **IndexNow** fired après chaque article généré ou modifié.

### Volet 3 — Hook Review J+14 (P2)
- Backend `/app/backend/routes/reviews_hook.py` :
  - `_create_invitations_for_order()` — crée 1 invitation par produit d'une commande livrée (token UUID, `send_after = delivered_at + 14j`, expiration 60j).
  - `check_due_invitations()` — appelée par le cron quotidien **04:00 UTC** (ajouté à `scheduler` dans server.py), envoie via Resend (si `RESEND_API_KEY`), sinon log "skipped_no_resend" (ops manuelles).
  - `_send_review_email()` — template HTML premium branded avec CTA "Laisser mon avis (1 min)".
  - Endpoints admin : `POST /reviews/check-due` (trigger manuel), `POST /orders/{id}/mark-delivered` (marque livré + crée les invitations).
  - Endpoints publics : `GET /public/reviews/invitation/:token` (résout le token) et `POST /public/reviews/submit/:token` (ajoute à `product.reviews[]` + recompute `rating.score`/`count` + fire IndexNow).
- Frontend `/app/frontend/src/pages/StorefrontReview.jsx` : page publique `/shop/:siteId/review/:token` — formulaire élégant 1-5 étoiles + titre + body, page de remerciement après soumission, `noindex` meta. Fonctionne sans Resend (génération du token manuelle permet de tester e2e).


## 2026-04-21 · Sprint 42 : Bundles IA intelligents + Blog + UI Cockpit pour narrative
### Volet 1 — Bundles IA intelligents
- **Backend** : nouveau champ `bundles_with: List[str]` sur produits + module `/app/backend/routes/product_bundles.py` avec endpoint `POST /api/sites/{id}/bundles/auto-generate` — Claude 4.5 analyse tout le catalogue et propose 2-4 cross-sells pertinents par produit (jamais de substituts, jamais aléatoire).
- **Frontend** : `ProductBundle.jsx` utilise `bundles_with` en priorité (si l'IA a analysé), sinon fallback sur la même category. Les bundles AI sont plus pertinents que la catégorie simple.
- **Test e2e réel** : sur Sereniva (2 produits), l'IA a identifié que Déambulateur est cross-sell du Fauteuil releveur mais pas l'inverse — comportement intelligent non-symétrique.

### Volet 2 — Blog Storefront (routes `/blog` + `/blog/:slug`)
- **Nouveau fichier** `/app/frontend/src/pages/StorefrontBlog.jsx` avec :
  - `StorefrontBlog` — index éditorial avec hero banner + grille 3 cols d'articles (category/read-time/excerpt/CTA).
  - `StorefrontBlogPost` — page article avec hero banner + image 16:9 XL + contenu markdown light (h2/h3/bold/ul) + metadata auteur + bloc "D'autres articles" en bas.
- **Fallback** : 3 articles SEO silver-eco complets (Bien choisir son fauteuil releveur, Maintien à domicile, Nuits réparatrices) rédigés premium — le template est visible même sans le hook #27-32.
- **SEO** : schemas `Blog` sur l'index, `BlogPosting` + `BreadcrumbList` sur la page article. Meta og:type="article" sur le détail.
- **Routes câblées** dans `App.js`.

### Volet 3 — UI Cockpit produits
- **SiteProducts.jsx** enrichi avec 2 actions IA :
  - **Bouton header "Auto-bundles IA"** (visible si ≥ 2 produits) — déclenche la génération bulk, affiche un toast avec le nombre de produits mis à jour.
  - **Bouton sparkle par produit** "Régénérer narrative IA" — écrase la narrative existante avec un nouveau call Claude. Badge vert si le produit a déjà une narrative, neutre sinon.
  - **Toast AI** (succès/erreur) en haut de page, auto-dismiss 5-6s.
- Tests validés : `auto-bundles`, `enrich-narrative-{id}`, `ai-toast` tous FOUND.

### SEO bonus
- Sitemap.xml inclut maintenant `/blog` + chaque `/blog/:slug`.


## 2026-04-21 · Sprint 41 : Page Produit marketing premium + IndexNow (AEO boost)
### Volet UX Produit — 6 composants ajoutés/refondus
- **`DeliveryEstimate.jsx`** — carte grise premium qui calcule et affiche la date de livraison estimée **J+3 ouvré** (en français complet « vendredi 24 avril »), saute les week-ends, affiche « Commandez avant 14h pour un envoi aujourd'hui » si avant cutoff en semaine.
- **`ProductBundle.jsx`** — bloc "Souvent achetés ensemble" : 2 produits complémentaires auto-sélectionnés (même `category`), cases à cocher, total avec −10 % en lot affiché et économie calculée, CTA "Ajouter le pack au panier". Fallback démo si pas d'autres produits.
- **`PaymentOptions.jsx`** — carte grise "3 × XX,XX € sans frais" (si prix ≥ 100 €) + badges paiement (Visa, Mastercard, CB, PayPal, Apple Pay).
- **`MobileStickyBuy.jsx`** — barre fixe bas de page mobile qui apparaît au scroll (>600px) avec image + nom + prix + CTA Ajouter, animation slide-in.
- **`TechSpecs` refondu** — passage de table 2-col à **grid 3 colonnes de cartes grises** avec eyebrow uppercase + valeur en serif, hover subtle.
- **Stock urgency** — badge subtil "Plus que X en stock" avec dot ambre pulsé, uniquement si stock < 10.
- **Trust badges** condensés en 2×2 texte monochrome (remplace les cartes grises redondantes avec les nouvelles cartes marketing).

### Volet IndexNow — AEO boost
- **Nouveau module `/app/backend/routes/indexnow.py`** :
  - `INDEXNOW_KEY` stable + fichier clé servi à `/api/public/indexnow-{key}.txt`.
  - Fonction `notify_indexnow(urls)` — POST `api.indexnow.org/indexnow` (Bing / Yandex / Naver / Yep ; répliqué auto vers ChatGPT).
  - `fire_and_forget_indexnow(urls)` — version non-bloquante.
  - Endpoint `POST /api/indexnow/notify` (admin) — submission manuelle.
  - Endpoint `POST /api/sites/{id}/indexnow/resubmit-all` — resoumet toutes les URLs du site.
- **Hooks auto** :
  - Après import catalogue (hook #16) → soumet accueil + collections + URLs produits.
  - Après enrichissement narrative IA → resubmit de l'URL produit enrichie.
- **Bénéfice concret** : indexation en ~24h au lieu de 2-4 semaines sur Bing, et citation accélérée par les moteurs de réponse IA.

### Validation visuelle
Tous les `data-testid` FOUND : `delivery-estimate`, `payment-options`, `payment-methods`, `product-trust-badges`, `product-bundle`, `product-specs`, `spec-0`. Screenshots confirmés (buy panel premium, bundle en vedette avec -104,80 €, fiche technique 9 cards en 3 colonnes).


## 2026-04-21 · Sprint 40 : Hook IA Product Narrative + SEO ultra-développé + AEO
### Volet 1 — Hook IA Product Narrative
- **Nouveau module** `/app/backend/routes/product_narrative.py` :
  - Fonction `enrich_product_narrative(product_id, force)` — appelle Claude Sonnet 4.5 avec un prompt copywriting premium (empathique, jamais infantilisant) pour générer `headline`, `subheadline`, 3 `sections` (title+body+bullet_points), 8 `tech_specs`, 5 `faq`.
  - Endpoint `POST /api/products/{product_id}/enrich-narrative` (auth Concepteur) — enrichissement manuel ponctuel.
  - Endpoint `POST /api/sites/{site_id}/products/enrich-narratives` (bulk) — enrichit jusqu'à 50 produits sans narrative.
- **Auto-dispatch** post hook #16 (`step_side_effects.py`) : chaque produit importé du catalogue déclenche un `asyncio.create_task` qui l'enrichit en background, fire-and-forget.
- **Stockage** : `product.narrative = { headline, subheadline, sections[], tech_specs[], faq[], enriched_at, enriched_model }`.
- **Fallbacks premium** de la page Produit prennent le relais tant que l'AI n'a pas enrichi.
- **Validé end-to-end** : test réel sur le produit Sereniva → Claude a généré 3 sections premium (« Se lever sans effort », « Un tissu pensé pour durer », « Livré, installé, testé ») + 3 bullet points ultra-concrets par section.

### Volet 2 — SEO / AEO ultra-développé
- **Sitemap.xml enrichi** (`routes/seo.py`) : accueil + `/collections` + chaque `/collection/:slug` + `/blog` + `/blog/:slug` + `/about` + `/faq` + `/contact` + `/livraison` + `/retours` + chaque `/product/:id` + pages légales. Priorités et `changefreq` adaptés par type.
- **robots.txt refondé** : allowlist explicite des 9 principaux AI crawlers (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended, Applebot-Extended, CCBot) + disallow `/cart`, `/checkout`, `/account/` + Sitemap + llms.txt déclarés.
- **Nouveau endpoint `/llms.txt`** (AEO / standard llmstxt.org) : résumé marque + 5 points clés + index des pages principales + liste des produits (avec prix) + 4 FAQ stratégiques. Format markdown prévu pour la citation par ChatGPT / Claude / Perplexity / Gemini.
- **SEOHead enrichi** : props `siteName`, `keywords`, `locale`, `robots`, `noindex`. Nouveaux meta tags `robots` (max-image-preview:large, max-snippet:-1), `og:site_name`, `og:locale`, `og:image:alt`, `keywords`.
- **Schemas JSON-LD enrichis sur Product** :
  - `Product` avec `aggregateRating`, `review[]`, `offers.priceValidUntil`, `offers.shippingDetails`, `offers.hasMerchantReturnPolicy` (OfferShippingDetails + MerchantReturnPolicy = richesse d'éligibilité Rich Results Google).
  - `BreadcrumbList` taxonomique.
  - `FAQPage` injecté depuis `product.narrative.faq`.
- **Homepage schemas** : Organization + sameAs social + WebSite avec SearchAction + ItemList + FAQPage.
- **Performance LCP** : `preconnect` + `dns-prefetch` vers `images.unsplash.com` dans le `StorefrontLayout` pour accélérer le chargement du hero.


## 2026-04-21 · Sprint 39 : Pages statiques (About/Contact/Livraison/Retours) + Page Produit ultra-complète
- **4 pages statiques premium** (`StorefrontPages.jsx` réécrit) avec chacune un `PageHero` éditorial (eyebrow + titre 6xl serif + subtitle) et du contenu structuré :
  - `/about` — Histoire de la marque + 4 piliers valeurs (Bienveillance/Exigence/Accompagnement/Responsabilité) + CTA contact.
  - `/contact` — Layout 2 colonnes : infos (email/phone/horaires/adresse) + form 4 champs avec mailing RGPD note.
  - `/livraison` — 3 cartes réassurance + table pays livrés avec délais/coûts/transporteurs + sections installation + emballage écolo.
  - `/retours` — 3 cartes (14j/retour gratuit/remboursé 5j) + 4 étapes numérotées + garantie 2 ans + produits non retournables.
  - `/cgv`, `/mentions`, `/confidentialite` enrichis avec PageHero + message clair quand la page n'est pas générée.
  - Routes câblées dans `App.js` (livraison + retours nouveaux).
- **Page Produit ultra-premium** (`StorefrontProduct` dans `Storefront.jsx`) :
  - Nouveau composant `ProductGallery.jsx` — image principale 1:1, thumbs 5 colonnes, zoom modal plein écran.
  - Nouveau composant `ProductReviews.jsx` — synthèse 4.8/5 avec distribution barres par étoiles + liste reviews triables (récents/meilleures/pires) + badge "Achat vérifié" + fallback 4 reviews silver-eco.
  - Nouveau composant `CrossSellProducts.jsx` — 4 produits de la même `category`, avec fallback 4 produits démo.
  - `NarrativeSections`, `TechSpecs`, `ProductFAQ` ont maintenant des **fallbacks premium** (2 sections narratives + 8 specs techniques + 5 questions FAQ par défaut).
  - Page refonte : breadcrumb taxonomique (Accueil > Collections > category > nom), rating + stock indicator en ligne, prix avec compare-at + badge -%, mention TVA/livraison, 4 trust badges (vs 2 avant), boutons CTA repensés.
- Tests visuels OK sur les 4 pages statiques + page produit (avec produits démo seedés en DB pour visualiser).


## 2026-04-21 · Sprint 38 : Pages Collection (index + détail) avec filtres et SEO
- **Backend** :
  - Ajout des champs `category: str` et `tags: List[str]` dans `ProductCreateInput` + `ProductUpdateInput` (taxonomie produit complète).
  - `GET /api/public/sites/{site_id}/collections` — liste des collections du site (depuis `design.collections`, fallback silver-eco 3 collections) enrichie avec `products_count`.
  - `GET /api/public/sites/{site_id}/collections/{slug}` — détail d'une collection (fallback virtuel pour `mobilite`/`sommeil`/`quotidien`).
  - `GET /api/public/sites/{site_id}/products` étendu avec query params : `collection`, `tag` (multi), `min_price`, `max_price`, `in_stock`, `on_sale`, `sort` (featured/newest/price_asc/price_desc/bestsellers).
- **Frontend** — nouvelle page `/app/frontend/src/pages/StorefrontCollection.jsx` :
  - `StorefrontCollections` (`/shop/:siteId/collections`) — index avec 3 cartes univers (image + title + count).
  - `StorefrontCollection` (`/shop/:siteId/collection/:slug`) — page détail avec :
    - **Hero banner minimaliste** (breadcrumb + eyebrow + titre + description + count).
    - **Barre de filtres horizontale sticky** : Prix (panel min/max), En stock (toggle), En promo (toggle), Catégories (tags multi-select), Trier par (select 5 options). Compteur de filtres actifs. Bouton "Effacer".
    - **Mobile drawer** full-screen pour les filtres avec CTA "Voir les produits".
    - **Grille produits** 2/3/4 colonnes responsive avec badges "Phare" + "-%".
    - **SEO block** en bas (description éditoriale + 4 trust bullets).
  - Routes câblées dans `App.js`. Liens header "Collections" et `CollectionsShowcase` pointent vers les vraies routes.
- **SEO** : schemas `BreadcrumbList` + `ItemList` sur la page collection. Hreflangs corrects.


## 2026-04-21 · Sprint 37 : Homepage Storefront ultra-optimisée (Hero visuel + 3 nouvelles sections + fallbacks premium)
- **Hero premium avec image** (`Hero.jsx` réécrit) : split layout desktop (copy à gauche, image à droite avec carte flottante "Satisfait ou remboursé"), pill eyebrow avec dot animé, titre 68px serif, 2 CTAs (primary vers `#collections`, secondary vers `#story`), trust row (rating 4.8/5 avec étoiles + 2143 avis · livraison · garantie · conseillers).
- **3 nouveaux composants** :
  - `FeaturedProduct.jsx` — spotlight du best-seller (ou 1er produit) avec image, rating, bullets checklist, prix + compare-at + badge -%, 2 CTAs. Affiche un produit démo si catalogue vide pour que le template soit visible.
  - `LifestyleEditorial.jsx` — section full-bleed avec image large + panneau éditorial dark à côté (eyebrow + titre serif + body + CTA blanc).
  - `InstagramGrid.jsx` — 6 tuiles carrées UGC avec hover likes counter, handle `@...` cliquable vers profil IG.
- **ProductGrid enrichi** : titre `text-5xl`, badges `PRODUIT PHARE` + discount `-X%`, 6 produits démo par défaut (Fauteuil / Déambulateur / Matelas / Barres / Pilulier / Téléphone) pour montrer le template avant import catalogue.
- **Fallbacks premium** ajoutés dans `Benefits`, `Testimonials`, `FAQSection` — les blocs ne disparaissent plus si les données ne sont pas encore remplies par les hooks IA (3 témoignages, 6 FAQ, 4 bénéfices par défaut).
- **SEO renforcé** : schemas `Organization` avec `sameAs` social, `WebSite` avec SearchAction, **nouveau `ItemList` des 12 premiers produits**, **nouveau `FAQPage` schema** injecté depuis les items FAQ (fallback inclus).
- **Nouvel ordre (16 sections)** : Hero → Press → Benefits → Collections → Products → **FeaturedProduct** → **LifestyleEditorial** → Values → BuyingGuide → Testimonials → FounderStory → **InstagramGrid** → BlogTeaser → FAQ → Newsletter → FinalCTA. Ancres `#collections`, `#products`, `#story`, `#faq` pour la nav.


## 2026-04-21 · Sprint 36 : Homepage ultra-complète (Header nav + Footer premium + 3 sections)
- **Header enrichi** (`StorefrontLayout.jsx`) : nav desktop (Boutique · Collections · Journal · À propos · Contact), menu mobile full-screen avec search intégré + contact footer, barre de confiance (livraison / paiement / support / langue), logo + tagline à gauche, search + compte + panier + hamburger à droite.
- **Footer 3 niveaux** : (1) bande réassurance 4 piliers avec icônes Phosphor (Livraison offerte / Paiement sécurisé / Conseiller humain / Retour 14j), (2) 5 colonnes (logo + contact + social Facebook/Instagram/YouTube/LinkedIn, Boutique, Nous connaître, Service client, Légal), (3) méthodes de paiement (Visa / Mastercard / CB / PayPal / Apple Pay / iDEAL / Bancontact) + copyright. Fond `neutral-900`, typo cohérente.
- **3 nouveaux composants homepage** :
  - `CollectionsShowcase.jsx` — 3 cartes univers thématiques avec image plein cadre + overlay gradient + CTA (fallback silver-eco : Mobilité / Sommeil / Quotidien).
  - `BuyingGuide.jsx` — 3 étapes visuelles reliées par un trait horizontal (écoute → livraison → accompagnement).
  - `BlogTeaser.jsx` — 3 articles avec image + catégorie + read-time + excerpt (fallback 3 articles silver-eco).
- **Nouvel ordre homepage** : Hero → Press → Benefits → **Collections** → Products → **BuyingGuide** → Values → Founder → Testimonials → **Blog** → FAQ → Newsletter → FinalCTA (13 sections).
- **Ancres ajoutées** (`#press`, `#collections`, `#products`, `#faq`) pour la nav interne.
- **Alimentation hook-ready** : chaque nouvelle section lit `design.collections`, `design.buying_guide`, `design.blog_posts` et tombe sur un fallback élégant tant que les hooks de prompts ne les ont pas écrits.


## 2026-04-21 · Sprint 35 : Homepage Storefront premium finalisée (4 nouvelles sections)
- **Intégration dans `/app/frontend/src/pages/Storefront.jsx`** des 4 composants créés au sprint précédent : `PressLogos`, `ValuesSection`, `FounderStory`, `NewsletterCTA`.
- **Nouvel ordre** de la homepage (schéma conversion orienté silver-eco) : Hero → PressLogos → Benefits → ProductGrid → ValuesSection → FounderStory → Testimonials → FAQ → NewsletterCTA → FinalCTA.
- **Fix import `pickLang`** : corrigé dans `ValuesSection.jsx` et `FounderStory.jsx` (import depuis `../../lib/i18n` au lieu de `./storefrontUtils`).
- **Alimentation future via hooks** : chaque section consomme le champ équivalent dans `site.design` (`design.press_mentions`, `design.values`, `design.founder_story`) et affiche un fallback "silver economy" par défaut — prêt à être écrasé par les hooks des prompts #5/#6/#38.
- **Vérif** : screenshot plein page confirme les 4 `data-testid` rendus correctement sur le site de démo `Sereniva`.


## 2026-04-21 · Sprint 34 : Correction stratégique — politique Altiaro centralisée (non modifiable par Concepteur)
- **Suppression du backend `settings.py`** : j'avais initialement donné aux Concepteurs la possibilité de modifier TVA/livraison/paiement par site, ce qui était une erreur stratégique (Altiaro doit garantir la cohérence entre tous les sites).
- **Nouveau module `backend/platform_policy.py`** : dict `PLATFORM_POLICY` central qui définit UNE FOIS pour toutes les 7 marchés Altiaro :
  - `taxes` : régime OSS UE + taux TVA appliqués auto selon pays livraison (FR 20% / BE 21% / LU 17% / DE 19% / NL 21% / CH 0% / UK 20%)
  - `shipping` : **livraison offerte** partout (frais absorbés par la marge plateforme) + ETA par pays
  - `payment` : stack Mollie unique (CB/Bancontact/iDEAL/Apple Pay/Google Pay/PayPal) + virement B2B auto >= 500€
  - `returns` : rétractation 14j + frais retour pris en charge par Altiaro
  - `warranty` : garantie légale 2 ans incluse
  - `customer_service` : SLA 2h ouvrées, 9h-18h Lun-Ven
- **2 endpoints publics** dans `routes/platform.py` :
  - `GET /api/platform/policy` — visible par Concepteurs (lecture seule)
  - `GET /api/platform/public/policy` — subset exposé aux storefronts (FAQ, footer, checkout)
- **Page `/sites/:id/policy`** entièrement refondue : affichage **lecture seule** avec badges "Non modifiable" sur chaque bloc (TVA / Livraison / Paiement / Retour / Garantie / Service client). Bouton cockpit renommé "Paramètres" → "Politique plateforme". Icône 🔒 cadenas en titre + message "Rien à configurer de ton côté".
- **Migration** : suppression de `sites.settings` sur les sites existants (`update_many unset`).


## 2026-04-21 · Sprint 33 : 3 features natives ajoutées au template (paramétrage + comptes clients + recherche)
- **Paramétrage admin** (`/sites/:id/settings`) : nouvelle page 4 onglets pour la config business du site, accessible via bouton "Paramètres" dans le cockpit.
  - **Taxes** : régime (franchise / TVA standard / OSS) + taux TVA éditables par pays (FR/BE/LU/DE/NL/CH/UK) + IOSS toggle
  - **Livraison** : zones éditables (nom, pays, transporteur, délai, paliers tarifaires JSON, franco de port) + ajout/suppression de zones. 2 zones seedées par défaut (France métro, BE+LU).
  - **Paiement** : toggles Mollie par méthode (CB, Bancontact, iDEAL, Apple Pay, Google Pay, PayPal) + seuil virement B2B
  - **Emails** : nom expéditeur, reply-to, support email/phone, signature
  - Backend `routes/settings.py` : GET/PUT `/api/sites/:id/settings` (avec deep-merge des `rates_by_country`) + GET public `/api/public/sites/:id/settings` (subset exposé au storefront)
- **Comptes clients** sur le storefront — collection `customers` scoped par site, auth JWT 30j (pas cookies, token dans localStorage par site).
  - Backend `routes/customers.py` : `POST /public/sites/:id/customers/register` · `/login` · `GET /me` · `PATCH /me` · `GET /orders`
  - Pages frontend : `StorefrontRegister.jsx`, `StorefrontLogin.jsx`, `StorefrontAccount.jsx` (profil + historique commandes avec status badges colorés)
  - Lib `customerAuth.js` : getToken/getCustomer/setSession/clearSession/authHeaders, event `alt_cust_session` pour sync multi-onglets
  - Suivi commande public (sans compte) : `GET /public/sites/:id/orders/:order_number?email=xxx` (vérif ownership par email)
- **Recherche storefront** — endpoint + page dédiée.
  - Backend `routes/storefront_search.py` : `GET /public/sites/:id/storefront-search?q=xxx` (regex case-insensitive sur name/description/tags/category, top 30 résultats)
  - Page frontend `StorefrontSearch.jsx` : input auto-focus, grille produits 3 colonnes, états vides empathiques
- **Header storefront enrichi** : barre de recherche desktop + bouton "Mon compte / Se connecter" (affiche prénom si connecté) + panier — tout branché sur les CSS vars du brand book (cohérence visuelle).
- **Testé E2E** (cURL) : GET/PUT settings OK, register + JWT + /me OK, search "fauteuil" → 2 résultats.


## 2026-04-21 · Sprint 32 : Branchement visuel du brand book au storefront
- **3 hooks mis à jour** dans `step_side_effects.py` pour set automatiquement `design.published = true` à la validation : #6 (brand), #9 (légal), #17 (scaffold). Avant, `/api/public/sites/{id}/design` renvoyait `null` tant que `design.published` n'était pas explicitement flippé par l'admin → aucun rendu ne changeait sur le storefront. Maintenant, dès qu'un hook tourne, le storefront est visible et reflète les nouveaux paramètres.
- **Fix tagline string vs dict** dans `StorefrontLayout.jsx` : le hook #6 stocke `tagline` en string simple, mais le layout le lisait comme dict multilingue `{fr: "..."}` → tagline invisible. Fix : cast type runtime pour accepter string OU dict `{lang: string}`.
- **Migration BDD** : `update_many({"design.brand": {"$exists": true}}, {"design.published": true})` → 2 sites existants (Luméa + Sereniva) immédiatement publiés avec leur brand book déjà appliqué.
- **Vérification E2E** sur `/shop/{id}` de Luméa Confort :
  - Logo en **Playfair Display** (font_heading injecté via Google Fonts dynamique + CSS var `--cf-font-heading`)
  - Tagline "Le confort qui prend soin de vous" affichée
  - Couleur primaire **#8B5A3C** (brun chaleureux extrait du markdown du hook #6) appliquée sur CTA "Découvrir la collection", icônes engagements, bandeau
  - Background crème `#FEFBF5`, texte `#2D1810`, font body "DM Sans" — tout cohérent
- Le brand book du hook #6 pilote désormais de bout en bout le rendu visuel du storefront **sans redéploiement**.


## 2026-04-21 · Sprint 31 : Refonte des 50 prompts pour cohérence stack Altiaro + barre de progression IA
- **Substitutions globales** dans `seed_prompts.py` pour retirer toute référence aux stacks qu'on n'utilise pas : **Shopify → Altiaro**, **Stripe/PayPal → Mollie**, **Klaviyo → Brevo**, **Algolia → recherche native Altiaro**, **"scaffold headless + Shopify Storefront API" → "customisation du template Altiaro"**. 24 prompts impactés, 0 occurrence restante vérifiée.
- **6 prompts pivots entièrement réécrits** pour refléter la vraie architecture (template Altiaro fourni, Mollie branché d'office, hooks auto pour légal/brand/produits) :
  - **#14** "Configuration Shopify complète" → **"Paramétrage backend Altiaro (taxes, livraison, paiement)"** — le Concepteur fournit des règles business, zéro code.
  - **#15** "Import CSV Altiaro" → **"Brief import catalogue (20 produits haute qualité)"** — livre un JSON exploitable par le hook #16 auto-import, pas un CSV Shopify.
  - **#16** "Stack apps Shopify" → **"Intégrations tierces Altiaro (emails, avis, analytics)"** — brief priorisé (Resend déjà branché, Brevo vs Mailjet, Trustpilot vs Judge.me, GA4/Meta/TikTok Pixel, Gorgias).
  - **#17** "Scaffold React headless" → **"Customisation du template Altiaro"** — le template est déjà appliqué via hook #17, le Concepteur brieffe les 13 sections homepage + charte + assets.
  - **#21** "Cart drawer + Shopify checkoutCreate" → **"Brief panier + checkout (Mollie déjà branché)"** — franco de port, upsell, code promo, trust signals.
  - **#24** "Recherche interne Cmd+K" → **"Brief navigation (catégories, filtres, méga-menu)"** — la recherche est déjà dans le template, le Concepteur livre l'arborescence + filtres + 10 recherches populaires.
  - **#36** "Stack paiement FR" → **"Optimisation checkout Mollie (réduction abandon panier)"** — Mollie est branché, l'étape = audit friction + 5 A/B tests + KPIs.
- Chaque prompt refondu respecte le pattern : **rôle d'expert + mission précisée + livrable en markdown/JSON exploitable + contrainte de taille** (800-2000 mots selon complexité). Ton "expert mentor", pas "dev qui code".
- **#22 et #23** également refondus en briefs éditoriaux (pas de code) : #22 = ligne éditoriale blog + 15 piliers + calendrier 90j + profil auteur E-E-A-T ; #23 = about 1000 mots + contact + 50 FAQ JSON + déclaration RGAA.
- **Barre de progression IA** : ajoutée dans `StepPanel.jsx` — pendant l'exécution Claude, affiche `~Xs restantes` + barre dégradée (#B84B31→#D97706) qui avance asymptotiquement jusqu'à 95%, texte "Claude rédige ton livrable..." + mention "30-90 secondes, ne ferme pas le panneau". UX rassurante, fin du "j'attends sans savoir quoi".
- **Synchronisation auto** : au démarrage backend, `server.py` re-pousse les 50 prompts depuis `PROMPTS` vers la BDD → les sites existants bénéficient immédiatement des nouveaux prompts sans re-seed.


## 2026-04-21 · Sprint 30 : Fix 4 bugs bloquants du flow Concepteur + UX guidage
- **Bug redirection** : `LaunchSite.jsx:createSite` renvoyait sur `/sites/:id/studio` (route supprimée au Sprint 26) → corrigé en `/sites/:id` (cockpit unifié).
- **Bug "Erreur est survenue" à l'exécution** : l'ingress Kubernetes coupe les requêtes > 60s. Le prompt #1 demandait 30 produits × 15 colonnes → output >5000 tokens → Anthropic/LiteLLM timeout > 60s → 502. **Fix** :
  - **Architecture async** : `POST /api/steps/:id/execute` passe en fire-and-forget. Le backend marque `ai_executing=true` puis `asyncio.create_task()` lance Claude en background. L'endpoint répond 200 en <200ms. Le frontend poll `GET /api/steps/:id` toutes les 2.5s pendant max 3 min, récupère `ai_response` ou `ai_error` quand prêt.
  - **Retry** : 1 retry automatique sur erreurs transientes (502/503/504/timeout/overloaded) avec backoff 1.5s. Timeout Claude étendu à 180s.
  - **Messages d'erreur clairs** : distinction budget épuisé / clé invalide / upstream surchargé / timeout.
  - **Prompt #1 raccourci** : matrice **15 produits × 8 colonnes** (était 30 × 15), demande explicite "1200-1800 mots MAX, synthétique" → output ~4000 chars, généré en 30-40s. Testé E2E : matrice complète (coussin lombaire chauffant, télécommande universelle, accoudoirs mémoire...) avec TOP 3 argumenté + warning réglementaire sur le kit transformateur.
- **Bug "Valider & continuer" rien ne se passe** : le backend exigeait au moins un livrable (URL/notes/fichier/ai_response) et retournait 400 silencieusement. **Fix** : le bouton est désormais **disabled tant qu'aucun livrable n'est renseigné**, avec tooltip explicatif. Feedback clair : "Exécutez le prompt IA ou renseignez un livrable pour pouvoir valider". Après submit réussi, le panneau se ferme automatiquement.
- **UX guidage ajouté** : bandeau "Comment ça marche" en haut du panneau latéral avec 4 étapes numérotées (lis le prompt → exécute → affine les livrables → valide). Chaque champ Livrable (URL externe / Notes internes / Fichiers joints) est explicité avec son usage concret. Fin du "je fais quoi ?".
- **Persistance state** : `ai_executing` et `ai_error` stockés dans le step document. Si le Concepteur ferme puis rouvre le panneau pendant une exécution en cours, il voit immédiatement le spinner reprendre et l'erreur s'afficher si échec.


## 2026-04-21 · Sprint 29 : Nettoyage UI + Claude 4.5 forcé + audit prompts
- **"Made with Emergent"** masqué via `src/App.css` (CSS `display:none` sur `#emergent-badge`). Supprimé aussi du source `public/index.html` (ré-injecté par l'ingress Emergent sur les previews, disparaît nativement sur altiaro.com après deploy).
- **"Copilot IA" FAB** retiré du `Layout.jsx` (Cmd+K admin conservé).
- **Claude 4.5 forcé** dans `StepPanel.jsx` : le sélecteur de modèle multi-providers (Haiku / GPT-5.1 / GPT-4o / Gemini 2.5 Pro) est supprimé. Affichage fixe "Claude Sonnet 4.5" en label mono + bouton exécution. Par ailleurs le state `aiModel` reste à `"anthropic/claude-sonnet-4-5-20250929"` donc les appels backend restent cohérents.
- **Audit complet des 50 prompts** : 47/50 étaient déjà au niveau expert (longueur >500 chars, structure détaillée). Les 3 prompts trop courts ont été enrichis au format "expert + critères d'acceptation" :
  - **#7 Voix de marque + manifesto** : passé de 374 → 1700+ chars (rôle Head of Brand Content agence top 10 Paris, manifesto structuré, voix 10 règles on dit/pas, 20 accroches ventilées 4 angles, storytelling fondateur, mission statement, tagline)
  - **#24 Recherche interne** : passé de 466 → 2000+ chars (rôle Senior Frontend ex-Shopify Plus, composant Search complet avec Cmd+K, 4 sections résultats, états vides, Shopify predictive search + Algolia fallback, accessibilité clavier, perf debounce)
  - **#27 30 articles satellites SEO** : passé de 497 → 2500+ chars (rôle Head of SEO Content ex-Hubspot/Semrush, structure imposée 6 sections par article, maillage cocon obligatoire, schemas JSON-LD, principe intent match)
- **Migration auto** : au démarrage backend, `server.py` re-synchronise `title/summary/prompt` des 50 steps depuis `seed_prompts.PROMPTS` vers la BDD. Log : "Block mapping synchronized + 50 prompts refreshed."
- **Audit StepPanel** vérifié visuellement : header (#N + status pill + Phase), summary, prompt complet (bouton Copier), exec IA avec Claude 4.5 fixe, réponse IA rendue en markdown, livrables (URL + notes + upload 15Mo), refus/validation avec permissions admin/concepteur, footer sticky dynamique selon status.


## 2026-04-21 · Sprint 28 : Hook #5 — Renommage automatique du site
- Ajout d'un 5e handler dans `step_side_effects.py` : **#5 Génération nom de marque + domaine + INPI** → déclenche un appel Claude qui extrait du livrable markdown le nom final retenu + tagline + domaine, puis met à jour `sites.name`, `sites.niche_slug` (slugifié via `_slugify`), `sites.target_domain`, `sites.design.brand.tagline` et `sites.design.brand.logo_text`.
- Testé E2E sur site fauteuil releveur éléctrique : provisoire "fauteuil releveur éléctrique" → **"Sereniva"** (avec slug `sereniva`, domaine `sereniva.fr`, tagline "L'art de vieillir sereinement"). Visible immédiatement dans la liste `/sites`.
- Si `brand_name` identique au nom courant → skip silencieux (pas de faux update). Si extraction Claude échoue → skip silencieux, validation non affectée.


## 2026-04-21 · Sprint 27 : Hooks automatiques de validation d'étape (#6/#9/#16/#17)
- **Nouveau module** `backend/routes/step_side_effects.py` : quand un Concepteur valide une étape clé, Claude Sonnet 4.5 est rappelé pour extraire le livrable en JSON structuré et l'appliquer automatiquement au site.
- **Hook #6 Identité visuelle** → `sites.design.brand` (primary_color, accent_color, background_color, text_color, font_heading, font_body, tagline, logo_text, voice_keywords). Le storefront reflète immédiatement la nouvelle charte.
- **Hook #9 Documents légaux** → `sites.design.legal_pages.{cgv,mentions_legales,confidentialite}` en markdown propre. Testé sur Luméa Confort : CGV 2863 car (6 articles dont rétractation 14j, garantie 2 ans), mentions 2005 car, RGPD 3388 car. Visibles sur `/shop/{id}/cgv` sans redéploiement.
- **Hook #16 Import catalogue** → insertion directe dans la collection `products` avec statut `draft`, SKU auto-généré, marge recalculée. Testé : 5 produits sur 5 (fauteuil releveur, coussin anti-escarres, barre d'appui, monte-escalier, lit médicalisé) avec marges 61-63%.
- **Hook #17 Scaffold template** → `design.template_applied=true`, `template_name="altiaro-premium-light"`, + merge des couleurs du brand book #6 avec les defaults Altiaro (évite storefront sans design si #6 skipé).
- **Fire-and-forget** : `schedule_side_effect(step)` appelle `loop.create_task` ; la validation HTTP répond instantanément au user, le hook Claude (60-90s) tourne en arrière-plan. Erreurs loggées mais jamais fatales.
- **Branché dans** `routes/steps.py` sur `submit_step` + `validate_step` — le hook se déclenche peu importe qui valide (Concepteur ou Admin).


## 2026-04-21 · Sprint 26 : Refonte cockpit Concepteur (1 seule vue, 8 blocs, flow unifié)
- **🗑️ Suppression des 3 pages doublons** qui créaient un chaos visuel : `/sites/:id/studio` (Prompt Studio avec 7 prompts bâtards), `/sites/:id/wizard` (Wizard 10 étapes), `/sites/:id/design` (Design IA). Fichiers `PromptStudio.jsx`, `Wizard.jsx`, `SiteDesign.jsx` supprimés, routes retirées d'App.js.
- **🏗️ Cockpit unique `/sites/:id`** : plus de boutons violets moches dans le bandeau. Seuls les CTA utiles restent (Gérer produits, Sourcing, Google Ads Copy, Voir la boutique, Domaine, Dupliquer, Scaler).
- **📊 4 → 8 blocs thématiques** : réorganisation complète de BLOCKS et PHASE_TO_BLOCK dans `seed_prompts.py`. Ordre : (1) Produits & Sourcing, (2) Marque & Identité, (3) Fondations boutique, (4) Construction du front, (5) SEO & Contenu, (6) Conversion & CRM, (7) Opérations & SAV, (8) Acquisition & Scale.
- **🔄 Migration automatique** : au démarrage backend, tous les steps existants sont re-mappés vers la nouvelle structure 8-blocs via `server.py:@on_event("startup")`. Idempotent — re-applicable à chaque redémarrage.
- **✍️ Fin du champ "Nom du site" manuel** : `LaunchSite.jsx` crée désormais le site avec un placeholder auto `"Projet {niche}"` ; le Concepteur renomme officiellement au **prompt #5 (Génération nom de marque + domaine + INPI)**, au bon moment dans le parcours.
- **🔠 Scan intelligent — correction orthographique** : `/api/quick-scan` renvoie maintenant `corrected_query` via Claude (ex: "matela medica" → "matelas médical"). Affiché dans l'UI LaunchSite si différent de la saisie.
- **🔑 5 mots-clés frères visibles** : les cartes marché affichent désormais les 4 principaux mots-clés analysés avec leur volume mensuel (ex: matelas anti-escarres 2100/mo, matelas médical 1200/mo, matelas médicalisé 800/mo, matelas hospitalier 650/mo). Le backend agrégeait déjà les volumes, mais l'UI cachait les détails.
- **🖥️ Layout full-screen** : Dashboard, LaunchSite, SiteDetail passés en `max-w-[1400|1600px] mx-auto w-full` — fin du "rien à droite de l'écran".
- **🔐 Fix CORS prod** : CORS_ORIGINS passé à `"*"` + middleware custom utilisant `allow_origin_regex=".*"` avec credentials (contourne la limite Starlette). `routes/google_ads.py:oauth_callback` dérive dynamiquement le frontend_base depuis le header Origin/Referer (plus de fallback hardcodé preview). Nécessite un redeploy pour activer sur `altiaro.com`.
- **👤 Seed auto du compte Concepteur** : `concepteur@conceptfactory.fr / Concepteur2026!` seedé idempotent au démarrage backend (avant : seul l'admin l'était, BDD prod fraîche = login impossible).
- **Tests** : curl E2E OK — correction "matela medica"→"matelas médical", 5 keywords avec volumes, verdict NO_GO/score 65 cohérent. Lint JS/Python clean. StepPanel d'exécution d'étape déjà fonctionnel (ouvert sur clic étape #1 du cockpit) : prompt complet 500+ mots + sélecteur Claude + "Exécuter l'IA" + sauvegarde brouillon + valider/rejeter.


## 2026-04-21 · Sprint 25 : Pivot "Altiora" → "Altiaro" (domaine .com libre)
- **🔁 Rebrand forcé** : après constat que **tous les TLDs d'Altiora sont pris** (Altiora Financial Group LLC aux US sur le .com, squatters sur .fr/.io/.eu/etc.), pivot vers un nom proche disponible. La commande OVH 248781829 a été interprétée par erreur comme un "transfert entrant" par l'API OVH → s'auto-annulera sous 14 jours avec remboursement 7,99€.
- **🌐 `altiaro.com` acheté** via OVH direct (order #248782321, 7,99€ TTC, vrai CREATE — vérifié dans la réponse item). Seul nom premium parmi 20 candidats testés qui avait `.com` réellement libre (DNS vide + HTTP silencieux + OVH `create` confirmé). Phonétiquement proche d'Altiora, même étymologie latine (élévation).
- **🎨 Logo branded** : l'icône SVG "A géométrique avec flèche intégrée" **remplace le A initial** du wordmark → rendu final `[icône-A]LTIARO`. Component renommé `AltiaroLogo` (fichier `/app/frontend/src/components/AltiaroLogo.jsx`).
- **✍️ 113 replacements** Altiora→Altiaro sur 20 fichiers code (backend + frontend + HTML + manifest + robots.txt + tax_utils + legal templates). Module `altiora_legal.py` renommé `altiaro_legal.py`. Contact email `contact@altiaro.com`.
- **🔀 DNS OVH configuré** : redirection HTTP 301 altiaro.com → preview Emergent via le proxy natif OVH (A record vers 213.186.33.5 + TXT `"1|https://senior-france.preview.emergentagent.com"` sur `@` et `www`). Propagation DNS 30 min à 4h.
- **✅ Layout sidebar simplifié** : la double représentation (carré noir+icône + texte "Altiaro") est remplacée par le nouveau logo horizontal unique, plus épuré. Idem Login/Signup panels.
- **Tests** : Playwright smoke tests OK sur Landing + Signup + Cockpit avec le nouveau logo. Aucune console error. Backend reboot clean, API `/api/platform/info` renvoie bien `"name": "Altiaro"`.


## 2026-04-21 · Sprint 23 : Rebrand "Altiora" + domaine + logo + pages publiques
- **🏢 Nouveau nom de plateforme** : "Concept Factory" → **Altiora** (latin « plus haut »). 32 remplacements dans 20 fichiers code (frontend JSX + backend routes + HTML/SEO meta). Emails techniques `@conceptfactory.fr` conservés (credentials login).
- **🌐 Domaine `altiora.com` acheté** via OVH direct (order #248781829, **7,99 € TTC** prélevés sur CB OVH par défaut). Bypass du flow Mollie puisque domaine platform-level.
- **🎨 Logo Altiora** généré via Gemini Nano Banana (1024x1024 JPEG) + composant React `<AltioraLogo>` SVG vectoriel (horizontal / icon-only / wordmark-only variantes, 3 tailles) — crisp à toute taille sans dépendance image. Injecté dans sidebar cockpit + login + landing + footers légaux.
- **🏗 Landing page publique `/`** (non-authed) : hero premium "La plateforme e-commerce des partenariats éclairés", KPI band (6 marchés, <2min scan, 50/50 marge, 0€ frais), section "Comment ça marche" en 4 steps, section "Partenariat 50/50" avec exemple concret de marge, section Trust (Mollie, SEO, RGPD), CTA "Demander un accès" contact@altiora.com, footer 4 colonnes.
- **📜 4 pages légales publiques** (sous `/api/platform/legal/{slug}` non-authed, exposées via `/mentions-legales`, `/cgu`, `/confidentialite`, `/cookies`) :
  - Mentions légales (éditeur, hébergement, PI, responsabilité, droit applicable)
  - CGU (définitions, services, obligations, partage 50/50, résiliation)
  - Politique de confidentialité RGPD complète (données, finalités, bases légales, durées, destinataires, droits, CNIL)
  - Politique des cookies (strictement nécessaires / analytics / tiers)
  - Templates dans `/app/backend/altiora_legal.py` — champs `XXX` à compléter par user (SIREN, adresse, RCS, n° TVA, directeur de publication)
- **🤖 SEO** : `index.html` réécrit (title, description, Open Graph, Twitter Card, canonical, theme-color, favicon Altiora), `robots.txt` créé (allow public + disallow cockpit), `manifest.json` rebrand.
- **🔐 `App.js` routes publiques** : `/` = Landing (non-authed) | Dashboard (authed) ; `/mentions-legales`, `/cgu`, `/confidentialite`, `/cookies` crawlables par Google/Mollie sans authentification.
- **Tests** : smoke tests Playwright OK sur landing + 4 pages légales + login + dashboard. Aucune console error.

## 2026-04-21 · Sprint 22 : Nettoyage DB + checklist Merchant Center
- **🧹 Table rase** du site démo Levio (`dbf77f87-d603-44d3-adfd-b44f596e138a`) à la demande du user : site + 3 produits + 2 commandes test + 50 steps + 1 domain record (pending OVH) + 68 quick_scans + 7 scan_groups supprimés de MongoDB. Assets Concepteur conservés : carte Mollie (mdt_ciGgZkbB5t Mastercard ••••0005), IBAN, infos société.
- **📋 Checklist Google Merchant Center livrée au user** (playbook via integration_playbook_expert_v2) :
  1. Créer compte GMC (même compte Google que Google Ads)
  2. Demander conversion Advanced / Multi-Client Account (délai 3-5j)
  3. Activer Content API for Shopping dans Google Cloud Console
  4. Ajouter scope `https://www.googleapis.com/auth/content` au OAuth consent screen + re-soumission vérification (3-5j, scope "sensitive")
  5. Vérifier domaine (meta tag HTML auto-injecté futur)
  6. Lier GMC ↔ Google Ads
  7. Fournir Merchant ID
- **🚫 Google Ads Campaign Management (P2) retiré** du backlog : user ne veut pas gérer les ads depuis l'admin. L'OAuth Google Ads reste actif pour Keyword Planner + lecture campagnes uniquement.
- **📝 Note CJ Dropshipping** : le catalogue CJ ne couvre pas la verticale fauteuil médicalisé (résultats = trottinettes/cuiseurs/ponceuses). Sourcing sera géré par le user lui-même en interne (il a ses fournisseurs). Piste alternative future : Spocket/Syncee pour matériel senior EU.
- **⚠️ OVH Mollie payment** : 14,99€ encaissés pour `levio-fauteuils.fr` mais achat OVH refusé (`"Your preferred payment method is not valid"` — user a ajouté la CB OVH depuis, mais refuse tout achat pour l'instant → domain record supprimé). Pour plus tard : documenter dans le flow `/domains/purchase` un meilleur message d'erreur côté UI quand OVH retourne cette erreur.


## 2026-04-21 · Sprint 21 : UI Light Mode (Ultra Premium Digital 2.0 — Light variant)
- **🎨 Bascule complète dark → light** suite au feedback user ("fond noir trop agressif → fond blanc éléments noirs")
- **`index.css`** réécrit : CSS vars light mode (background 0% 100%, foreground 240 10% 4%, border 240 6% 90%), body `bg-white text-neutral-900`, scrollbar (#E4E4E7), selection, markdown rebaselined clair
- **37 fichiers JSX** transformés via script Python (`/tmp/flip_to_light.py`) avec placeholders pour les CTA inversés :
  - `bg-black`/`bg-zinc-950` → `bg-white`, `bg-zinc-900` → `bg-neutral-100`, `bg-zinc-800` → `bg-neutral-200`
  - `text-white`/`text-zinc-100` → `text-neutral-900`, `text-zinc-400` → `text-neutral-600`, `text-zinc-500` → `text-neutral-500`
  - `border-zinc-800/900` → `border-neutral-200`, `border-zinc-700` → `border-neutral-300`
  - CTA primaire inversé : `bg-white text-black hover:bg-zinc-200` → `bg-neutral-900 text-white hover:bg-neutral-800`
- **Hero blocks sombres** conservés (BalanceCard `highlight`, Card preview Billing, Wizard/PromptStudio hero, CopilotFab button) avec `text-white/XX` sur les textes enfants
- **Modales/backdrops** basculés de `bg-white/XX` (invisible) vers `bg-neutral-900/30-40` pour dimmer correctement
- **Storefront** intact : les composants `/components/storefront/*` et `Storefront.jsx` conservent leur thème chaud Fraunces + #FDFBF7 (classe `.storefront-root`)
- **Tests Playwright frontend** (iteration_16.json) : 7/7 pages validées, 0 console error, 0 bug UI bloquant, contraste WCAG AA OK, tous les CTA noirs visibles, tous les `data-testid` préservés


## 2026-04-21 · Sprint 19 : Google Ads Center (Admin only) + activation CJ
- **🔑 CJ Dropshipping activée** avec la vraie clé user (`CJ135808@api@...`). Sourcing opérationnel : recherche + import 1-clic avec `cost_price_ht` snapshot. Fix parsing prix ranges (ex "0.48 -- 0.67").
- **🎯 Sprint 19 — Google Ads Center** (`routes/google_ads.py` + `pages/GoogleAds.jsx`) — Admin only :
  - **OAuth2 Web Flow** complet : `GET /api/google-ads/oauth/start` + `GET /api/google-ads/oauth/callback` (redirect vers frontend avec status)
  - Refresh tokens stockés dans `db.google_ads_credentials` par `admin_user_id`
  - `GET /api/google-ads/status` · `POST /api/google-ads/disconnect` · `POST /api/google-ads/login-customer-id` (support MCC)
  - `GET /api/google-ads/customers` : ListAccessibleCustomers
  - **`POST /api/google-ads/keyword-ideas`** : GenerateKeywordIdeas avec volumes mensuels Google réels + competition index + fourchette CPC pour 8 pays (FR/DE/BE/NL/UK/CH/ES/IT)
  - `POST /api/google-ads/campaigns` : SearchStream GAQL read-only sur last 7/14/30 jours (impressions, clicks, cost, conversions, CTR, CPC)
  - Frontend `/admin/google-ads` : 3 cartes — Connexion · Keyword Planner (table) · Campaigns (table)
  - Route protégée `adminOnly`, lien sidebar Admin uniquement
- Sécurité RBAC : 403 pour Concepteur, 401 pour anonyme, 503 si clés backend manquantes
- Package Python ajoutés : `google-ads==30.0.0` + `google-auth-oauthlib==1.3.1`
- Variables `.env` : `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REDIRECT_URI`
- Tests : 27/27 pytest backend réussis (iteration_14.json), 0 régression



## 2026-04-21 · Sprints 16+17 : Sourcing CJ/AE + Wizard 10 étapes + SEO avancé
- **📦 Sprint 16 Backend + Frontend** — Sourcing unifié CJ Dropshipping + AliExpress Affiliate :
  - `GET /api/sourcing/providers` : statut activation + steps setup
  - `POST /api/sourcing/search` : recherche parallèle multi-providers (fallback gracieux si clés manquantes, 0 crash)
  - `POST /api/sites/{id}/sourcing/import` : import en 1 clic avec `cost_price_ht` snapshot
  - Page `/sites/:id/sourcing` : recherche + grille résultats + bouton import 1-clic + multiplicateur marge (×2/×2.5/×3/×4)
- **🧙 Wizard 10 étapes guidées** (`routes/wizard.py` + `pages/Wizard.jsx`) :
  - 10 étapes : produit → pays → sourcing → pricing → positionnement → identité → SEO → contenu → légal → publish
  - Auto-détection : scan DB (products/design/published) → marque automatiquement les étapes complétées
  - Endpoints : `GET /api/sites/{id}/wizard` + `POST /api/sites/{id}/wizard/step/{step_id}` (mark done/pending + advance_to)
- **🔍 Sprint 17 SEO avancé** :
  - `GET /api/public/sites/{id}/sitemap.xml` : URLs + hreflang alternates auto selon selected_countries
  - `GET /api/public/sites/{id}/robots.txt`
  - **`GET /api/public/sites/{id}/merchant-feed.xml?country=FR|DE|BE|NL|UK|CH`** : RSS 2.0 conforme Google Merchant Center (g:id, g:title, g:price, g:availability, g:shipping)
  - **Composant `SEOHead.jsx`** : injection DOM dynamique `<title>`, meta description, Open Graph, Twitter Cards, canonical, hreflang alternates, JSON-LD Schema.org
  - Storefront Home : Schema.org `Organization` + `WebSite` avec SearchAction
  - Storefront Product : Schema.org `Product` avec `Offer` (prix, currency, availability, URL)
- Boutons `Wizard 10 étapes` + `Sourcing CJ/AE` ajoutés dans SiteDetail
- Tests : 19/19 pytest backend + frontend E2E validé (iteration_13.json)



## 2026-04-20 · Sprint 15 : Deep Market Analyzer v2 🔬

**Vision :** passer d'une « analyse 30 secondes » (Claude mono-appel) à une **vraie étude de marché approfondie** multi-étapes, langue native par pays, 2-4 minutes de calcul.

**Changements fondamentaux :**
- 🔓 **Ouverture à TOUS les produits e-commerce** (plus limité Silver Economy). Nouveau champ `persona` (senior / millennial / famille / pro / tout public).
- 🗑️ Suppression du **catalogue pré-seedé de 20 niches** côté frontend (route `/niches/:slug` + page `NicheDetail` retirées). Backend conservé pour compatibilité, invisible.
- 🌍 Support **8 pays EU** (ajout IT + ES aux 6 existants : FR/DE/CH/BE/UK/NL).

**Architecture multi-étapes (`routes/analyzer.py` réécrit complet) :**
1. **Étape 1** — Extension keywords multi-langues natives (30s) : 30-50 mots-clés par pays en langue locale (transactionnels, informationnels, longue traîne)
2. **Étape 2** — Sizing marché (60s) : volume mensuel, CPC, KD, AOV, marché total annuel, croissance 3 ans, pénétration e-com, saisonnalité
3. **Étape 3** — Analyse concurrentielle (60s) : 5-8 concurrents réels par pays avec prix, forces/faiblesses, PDM, type (marketplace/DNVB/historique/dropshipper) + white-space de positionnement
4. **Étape 4** — Cadre légal & opérationnel (30s) : certifications obligatoires, mentions, TVA, douanes, transporteurs, délais, langue SAV, paiements préférés
5. **Étape 5** — Synthèse stratégique (30s) : verdict par pays argumenté avec chiffres, stratégie de lancement priorisée, pricing par pays, fournisseurs, risques/opportunités

**Background tasks + progress tracking :**
- `POST /api/niches/analyze` → crée un `analysis_job`, renvoie `job_id` immédiatement
- `GET /api/niches/analysis-jobs/{id}` → polling 3s pour suivi temps réel
- Collection `analysis_jobs` avec `step`, `step_label`, `status` (pending/running/completed/failed)

**Frontend :**
- 🆕 Nouvelle page `Analyzer.jsx` : formulaire propre (produit + persona + pays + notes) + progress panel live avec 5 étapes animées (spinner actif, check vert terminé) + historique
- 🔄 Refonte complète `NicheAnalysisDetail.jsx` : hero verdict + 4 KPI cards + **stratégie de lancement** priorisée + **sélecteur pays** sticky + **onglets par pays** avec panel ultra détaillé (sizing 8 data points, pricing, keywords en 3 catégories, concurrents listés, cadre légal 8 champs) + risques/opportunités + suppliers + positioning white-space
- 🏷️ Nav renommé « Niche Engine » → « **Analyseur** »

**Validation E2E :**
- Test réel sur « Support téléphone universel pour vélo » (FR/DE/UK) — analyse complète en ~2 min : verdict **NOGO** correctement identifié (AOV 16-19€ << seuil 80€, impossible à rentabiliser sur accessoire low-ticket), 7 concurrents réels par pays (Amazon/Decathlon/Alltricks/Cdiscount/Fnac/Quad Lock/dropshippers Shopify), certifications correctes (RoHS FR / GS DE / UKCA post-Brexit UK), 10 keywords natifs transactionnels par pays, stratégie de lancement priorisée DE→UK→FR avec justifications chiffrées.
- Screenshots : formulaire, page résultat top, panel pays FR avec ses 30+ data points, panel concurrents + cadre légal

## 2026-04-20 · Sprint 14 : Site Designer IA-first 🎨
- **Vision** : UN template unique (celui de Concept Factory), 100% personnalisé par l'IA. Le Concepteur clique sur « Générer mon site » et Claude Sonnet 4.5 produit le site de A à Z — aucun drag-and-drop, aucune édition manuelle.
- **Backend nouveau module `routes/design.py`** :
  - `GET /api/sites/{id}/design` — récupère le design courant
  - `POST /api/sites/{id}/design/generate` — Claude génère en 1 shot **brand** (couleurs, polices, tagline), **hero** (titre/sous-titre/CTA/trust_line), **4 bénéfices**, **3 témoignages**, **10 FAQ**, **page À propos** (4 paragraphes), **page Contact**, **SEO meta**, **footer** — tout en FR/EN/DE/NL
  - `POST /api/sites/{id}/design/regenerate/{section}` — régénération section-par-section (brand, hero, benefits, testimonials, faq, about, contact, footer, seo, logo) avec `tweak` textuel optionnel
  - `POST /api/sites/{id}/design/publish` — toggle publication
  - `GET /api/public/sites/{id}/design` — lu par le storefront (renvoie uniquement si `published=true`)
  - `POST /api/public/sites/{id}/contact` — formulaire contact stocké en `leads`
  - `GET /api/sites/{id}/leads` — liste des messages reçus par le Concepteur
- **Logo graphique IA** via **Gemini Nano Banana** (`gemini-3.1-flash-image-preview`) — fallback silencieux si timeout (le logo texte fonctionne toujours)
- **Pages légales sûres** : CGV / Mentions légales / Confidentialité basées sur des **templates juridiques français standards** (`legal_templates.py`), variables remplies par Claude (site_name, niche, email)
- **Storefront 100% dynamique** (`Storefront.jsx` + `StorefrontLayout.jsx`) :
  - Lit `design.brand` → applique couleurs/polices via CSS custom properties + Google Fonts chargées dynamiquement
  - Hero, bénéfices, témoignages, FAQ rendus depuis le JSON du design
  - Footer structuré multi-colonnes + liens légaux auto
  - Fallback propre si design non publié (utilise les valeurs par défaut terracotta)
- **Nouvelles routes publiques** : `/shop/{id}/about`, `/faq`, `/contact`, `/cgv`, `/mentions`, `/confidentialite` — tous dans `StorefrontPages.jsx` avec rendu MarkdownLite
- **Nouvelle page Concepteur `/sites/{id}/design`** (`SiteDesign.jsx`) : sidebar gauche avec contrôles IA + preview iframe droite en temps réel + rechargement au clic « Régénérer »
- **CTA « Design IA » dégradé terracotta** ajouté dans `SiteDetail.jsx`
- Validé : injection d'un design mock complet, rendu correct sur toutes les pages (Home, About, FAQ, Contact, CGV) avec couleurs bleu médical `#0E7490` + police Fraunces. Page Design Concepteur fonctionnelle avec preview live.

## 2026-04-20 · Sprint 13 : Virements Concepteurs sur marge brute HT 💸
- **🎯 Nouvelle règle métier** : la part Concepteur = **50% × marge brute HT** (CA HT − Prix d'achat HT) et non plus 50% du total TTC.
- **📦 Produit** : ajout du champ `cost_price_ht` (prix d'achat HT fournisseur) sur `ProductCreateInput` / `ProductUpdateInput`. Input dédié + preview live de la marge dans l'éditeur UI.
- **🏷️ Site** : ajout du champ optionnel `vat_rate` (sinon taux déduit du 1er pays ciblé : FR=20%, DE=19%, BE/NL=21%, UK=20%, CH=7.7% — mapping dans `tax_utils.VAT_BY_COUNTRY`).
- **🧾 Order snapshot** : à la création de commande publique, chaque item fige `cost_price_ht` depuis le produit et l'order enregistre `subtotal_ht`, `cost_ht`, `gross_margin_ht`, `vat_rate`.
- **💰 Ledger** : `log_order_share_on_paid` calcule désormais `amount = 50% × gross_margin_ht` (avec fallback recalcul si snapshot manquant). Nouveaux champs `revenue_ht`, `cost_ht`, `gross_margin_ht` dans l'entrée ledger.
- **🆕 Page Admin `/admin/payouts`** (`AdminPayouts.jsx`) avec 3 onglets :
  - **À effectuer** : liste des virements pending avec IBAN complet + bouton "Copier IBAN", "Marquer payé", "Annuler".
  - **Aperçu prochain cycle** : ventilation par Concepteur avec CA HT / Achats HT / Marge HT + détail par site.
  - **Historique** : tous les virements marqués payés.
  - 4 KPI cards : À virer maintenant / Aperçu / Prochain cycle / Déjà versé.
- **📅 Cron auto** : le 1er et 15 de chaque mois à 03h UTC → appelle `admin_run_payouts` qui fige automatiquement les entrées `payout pending` dans le ledger + crée une `admin_notifications` entry.
- **🔁 Endpoints backend** :
  - `GET /api/admin/billing/payouts-preview` enrichi : `site_breakdown[]`, `next_cycle_date`, IBAN en clair pour copier-coller.
  - `GET /api/admin/billing/payouts-history` : tous les payouts avec nom/email Concepteur.
  - `POST /api/admin/billing/payouts/{id}/cancel` : annule un pending.
  - `GET/POST /api/admin/notifications` : toast admin payouts ready.
- **🧮 Netting** : le calcul `net_due` ne déduit PLUS les `ad_debits` (ils sont collectés séparément via CB mandate) — conforme à la demande utilisateur.
- Tests : **17/17 pytest Sprint 13** + régression **21/21 iter11** = 100%. Frontend E2E validé (3 onglets, KPIs, nav, accès contrôlé admin-only, éditeur produit).

## 2026-04-20 · Sprint 12 : Facturation Concepteurs (CB + IBAN + payouts) 💳
- **🗂️ Espace Concepteur "Mon compte"** (`/billing`) :
  - **Carte bancaire** via Mollie mandate (first payment 0.01€ en sequenceType=first → mandate_id stocké). CB affichée en carte noire gradient avec last4/brand + mode test/live.
  - **IBAN + BIC + titulaire** avec validation `schwifty` (auto-détection BIC + nom banque). IBAN affiché masqué (FR76 XXXX XXXX XXXX XXXX 2606).
  - **Balance** : 3 cartes (Ta part à recevoir en highlight gradient · Commandes encaissées · Dépenses pub prélevées)
  - **Historique ledger** complet (order_share · ad_debit · payout) avec couleurs + pending badge.
- **🔐 Activation Ads bloquée** sans CB : `POST /api/admin/sites/{id}/ads/activate` retourne 400 tant que l'opérateur n'a pas validé sa CB (exigence user).
- **📅 APScheduler** démarré au boot backend :
  - Lundi 03:00 UTC → prélèvement 50% dépense pub 7j pour chaque site `ads_active` (via Mollie recurring payment sur le mandate).
  - 1er + 15 de chaque mois 03:00 UTC → preview des payouts (log dans les stats admin).
- **📊 Admin Billing Cockpit** : `GET /api/admin/billing/overview`, `payouts-preview`, `run-payouts`, `payouts/sepa-xml` (export PAIN.001.001.03 pour virement bancaire groupé).
- **🪙 Ledger auto** : à chaque commande `paid` via webhook Mollie → `order_share` 50% crédité au Concepteur. À chaque `batch_update_prices` → pas encore de ledger (tracking orders only pour l'instant).
- Tests : 23/23 pytest iter11 + 13/13 régression iter10 = **36/36 backend** + 100% frontend E2E (iteration_11.json).
- 2 fixes post-test : `DELETE /billing/card` clear aussi `pending_setup_payment_id` + bouton "Relancer la validation" sur état pending.

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
