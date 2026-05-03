# Cockpit — Étape 9 SEO/AEO/GEO — Spec industrielle

> **Scope** : ce document décrit ce que l'étape 9 du Cockpit (SEO) DOIT faire
> **automatiquement, pour chaque site livré par un concepteur**. C'est la
> spec cible, pas un audit Altea.
>
> **Contexte produit** : usine à sites e-commerce premium Silver Economy.
> Cible : 10 sites/jour/concepteur. Chaque site sort à 100 % SEO-ready sans
> intervention manuelle, avec l'ambition de ranker sur un bassin de ≥1 000
> keywords longue traîne dès le lancement.
>
> **Date** : 2026-05-03
>
> **Légende** : ✅ implémenté · ⚠️ partiel · ❌ absent · 💰 coût LLM additionnel
> par site · ⏱ effort dev (heures d'un bon dev IA-assisté)

---

## A. URL & technique (auto sur publish)

| # | Item | Statut | Détail |
|---|------|--------|--------|
| A1 | **URLs slug-based + 301 UUID→slug** | ✅ | Corrigé le 2026-05-03. `GET /api/public/sites/{id}/products/{slug_or_uuid}` accepte les deux et renvoie la ressource. Frontend `StorefrontProduct` fait `history.replaceState` UUID→slug au chargement. Helper `lib/shopUrls.js::productCanonicalUrl`. |
| A2 | **Sitemap XML auto + hreflang + lastmod + image:image** | ✅ | `/api/public/sites/{id}/sitemap.xml` utilise `custom_domain` comme base quand vérifié, URLs slug-based, `<image:image>` par produit (AI + supplier), hreflang multi-marchés dérivé de `seo_countries`, `x-default`. |
| A3 | **robots.txt smart** | ⚠️ | Endpoint `/api/public/sites/{id}/robots.txt` existe mais à auditer : doit bloquer `/cart`, `/checkout`, `/account/*`, les paramètres `?lang=`, `?ref=`. Inclure `Sitemap:`. **Action** : revoir `seo.py:198` pour ajouter les Disallow manquants. ⏱ 0.5h. |
| A4 | **Schema.org JSON-LD complet** | ⚠️ | PDP : Product + BreadcrumbList + AggregateRating + Review + Offer + MerchantReturnPolicy + ShippingDetails ✅. **Manquants systématiquement** : FAQPage (A4a), HowTo (A4b), Organization (A4c global site), WebSite+SearchAction (A4d home), ItemList (A4e collections), BlogPosting (A4f blog). **Action** : étendre `services/seo_jsonld.py` + injecter dans `StorefrontHome`, `StorefrontCollection`, `StorefrontBlog`. ⏱ 4h. 💰 0 (pur code). |
| A5 | **Open Graph + Twitter Card par page** | ⚠️ | PDP OK. Home/Collections/Blog : à vérifier dans `SEOHead`. Il manque `og:image:width/height`, `twitter:card=summary_large_image`. **Action** : audit + normalisation `components/SEOHead.jsx`. ⏱ 1h. |
| A6 | **Canonical + hreflang sur toutes les pages** | ⚠️ | PDP ✅ (slug). Home/Collections/Blog : à contrôler. Le helper `buildHreflangs(site, path)` existe — faut s'assurer qu'il est appelé partout. ⏱ 1h. |
| A7 | **Image alt SEO-rich** | ❌ | Aujourd'hui les alt sont `""` ou le nom brut. 8 styles × 9 produits = 72 alts à générer. **Action** : prompt Claude dans le pipeline variant (`product_variant_pipeline.py`) pour chaque style : "alt de 80-120 car contenant {nom_produit} {material} {couleur} {contexte_style}". Persister dans `generated_images_by_variant[style].alt`. Le frontend lit déjà `alt` (voir `ProductGallery.jsx`). ⏱ 2h. 💰 +0.01 $/site (72 courts calls Claude Haiku). |
| A8 | **WebP/AVIF + srcset + lazy** | ❌ | Aujourd'hui : images Nano Banana en PNG brut servies via URL preview emergent (pas de CDN, pas de variants responsive). **Action** : pipeline de transformation côté backend sur upload vers `uploads/` — stocker 3 formats (AVIF @ 800, WebP @ 800, JPG @ 800) + un @ 1600 pour retina. Expose `<picture>` + `srcset`. ⏱ 6h. Ou plus rapide : intégrer `imgproxy` ou `cloudinary` côté frontend via URL transform. 💰 0 (pur code si local). |
| A9 | **URLs slug-based sur Link / Navigate** | ⚠️ | PDP + ProductCard + FeaturedProduct ✅ migrés (2026-05-03). Restent ~80 occurrences `/shop/${siteId}/...` dans d'autres composants (Hero, Collections, Blog, Upsells, etc.) qui fonctionnent mais ne sont pas en format propre. **Action** : migration sed globale `/shop/${siteId}/product/${xxx}` → `productPath(siteId, xxx)`. ⏱ 2h. |

---

## B. Contenu PDP enrichi (auto par produit à l'étape 5 ou 9)

| # | Item | Statut | Détail |
|---|------|--------|--------|
| B1 | **Description longue ≥800 mots** | ⚠️ | Aujourd'hui : `narrative.subheadline` (~40 mots) + `narrative.body` (~300 mots) + USPs + How-To (3-4 étapes) + Manifesto + Editorial cards + FAQ produit (~6 Q/A) + Specs. Total réel ≈ 500-700 mots. **Action** : ajouter 2 sections au prompt Claude de `product_variant_pipeline.py` / `narrative` : "Use Cases détaillés (3 scénarios de vie ~80 mots chacun)" + "Garantie & SAV spécifique produit (~60 mots)". Total : 800-1000 mots. ⏱ 2h. 💰 +0.02 $/produit × 9 = 0.18 $/site. |
| B2 | **FAQ structurée 8-10 Q/A par produit + Schema FAQPage** | ⚠️ | Aujourd'hui ~6 Q/A dans `narrative.faq_product[]`. Pas de Schema FAQPage injecté. **Action** : (1) pousser le prompt à 8-10 Q/A ; (2) ajouter Schema FAQPage dans `schema=[...]` du `<SEOHead>` PDP. ⏱ 1h + 0.5h. 💰 +0.01 $/produit. |
| B3 | **HowTo Schema 3-5 étapes** | ⚠️ | Données existent dans `narrative.how_to_steps[]`. Schema HowTo non injecté. **Action** : ajouter dans JSON-LD du `<SEOHead>` PDP avec étapes, image par étape, nom, texte. ⏱ 0.5h. |
| B4 | **"À qui s'adresse ce produit" + "Garanties" + "Comparatif vs alternatives"** | ❌ | Aucune des 3 sections n'existe. **Action** : étendre le prompt `narrative` avec `target_audience`, `warranty_details`, `vs_alternatives[]` (3-5 comparateurs génériques). Ajouter blocs React dans StorefrontProduct. ⏱ 4h. 💰 +0.03 $/produit × 9 = 0.27 $/site. |
| B5 | **Tableau spécifications structuré** | ⚠️ | `narrative.specs[]` existe (clé/valeur) mais rarement ≥10 lignes. **Action** : forcer 12-15 lignes dans le prompt ; render en `<table>` structurée + Schema PropertyValue. ⏱ 1h. 💰 +0.005 $/produit. |
| B6 | **Internal linking : 5 produits connexes + 2 blog + 1 buyer guide** | ⚠️ | `CrossSellProducts` + `UpsellsRecommendations` ✅ (4-6 produits). Liens blog ❌. Buyer guide ❌ (car pas de buyer guide généré). **Action** : bloc "À lire aussi" (3 articles blog + 1 buyer guide) en bas de PDP, sélectionnés par overlap de keywords avec le produit. ⏱ 2h. |

---

## C. Pages SEO structurelles (auto-générées à l'étape 9)

| # | Item | Statut | Détail |
|---|------|--------|--------|
| C1 | **Buyer Guides ≥5 × 2000 mots** | ❌ | Rien aujourd'hui. C'est LE gap n°1 pour la longue traîne ("guide d'achat X", "comment choisir Y", "meilleur Z 2026"). **Action** : nouveau service `services/buyer_guides_generator.py` lancé dans `launch.py` étape 9. Prompt Claude par guide : 2000 mots structurés (intro 150 + critères d'achat 400 + 5-8 top products 900 + FAQ 300 + CTA 150). Persister dans collection `landing_pages` (déjà existante, 0 docs) avec `kind="buyer_guide"`. Router `/guides/:slug`. Sitemap + Schema Article. ⏱ 8h. 💰 5 guides × 0.15 $ = **0.75 $/site**. Gain : +60 keywords positionnables. |
| C2 | **Pages comparaison X vs Y — top 10** | ❌ | Rien. **Action** : générer automatiquement les 10 couples les plus pertinents (ceux qui partagent la catégorie et diffèrent par prix/feature). Prompt Claude : 800-1000 mots, tableau comparatif, verdict, Schema Article + `about`/`mentions`. Router `/compare/a-vs-b`. Sitemap. ⏱ 4h. 💰 10 × 0.08 $ = **0.80 $/site**. Gain : +20 keywords navigationnels haut de funnel. |
| C3 | **Top X de l'année — 5 à 10 listes** | ❌ | **Action** : 5 pages "Top 5 {catégorie} {année}" par site, format ItemList + Article. Prompt Claude 1200 mots avec 5 produits du catalogue + alternatives marché + FAQ. ⏱ 3h. 💰 5 × 0.10 $ = **0.50 $/site**. Gain : +25 keywords transactionnels. |
| C4 | **Glossaire niche 30-50 termes** | ❌ | **Action** : service `glossary_generator.py` → 40 termes métier (ex : "fauteuil releveur", "aide au lever", "repose-pieds", …) avec définition 80-150 mots, internal links vers PDP/guides. 1 page index + 40 ancres OU 40 pages séparées (meilleure longue traîne → pref). Schema DefinedTerm + DefinedTermSet. ⏱ 5h. 💰 40 × 0.015 $ = **0.60 $/site**. Gain : +40 keywords informationnels très ciblés. |
| C5 | **About page enrichie** | ❌ | Aujourd'hui : page stub générique. **Action** : prompt Claude "About premium" 1000 mots (histoire fictive cohérente avec niche + équipe 3-4 persons fictives avec noms/bios/photos Nano Banana + valeurs + certifications crédibles + NAP visible). Persister dans `site.about_rich`. ⏱ 3h. 💰 0.05 $/site + 4 images Nano Banana (0.02 $ × 4) = **0.13 $/site**. Gain : E-E-A-T + +5 keywords marque. |
| C6 | **FAQ globale site — 20+ Q/A** | ⚠️ | FAQ actuelle est courte (6-8 Q/A génériques). **Action** : forcer 22-25 Q/A couvrant livraison, retours, paiement, garantie, SAV, paiement en plusieurs fois, éligibilité assurance, conseil personnalisé. Schema FAQPage. ⏱ 1h. 💰 +0.02 $/site. |

---

## D. Blog SEO premium

| # | Item | Statut | Détail |
|---|------|--------|--------|
| D1 | **Rythme 4 articles/semaine** | ⚠️ | Aujourd'hui : blog_worker tick toutes les 30s mais limité à ~1/semaine par site (configurable via `BLOG_SCHEDULE_WEEKLY`). **Action** : passer à 4/semaine par défaut, répartis sur les jours. Nécessite cluster keyword ≥50 pour éviter la répétition. On a 299 sur Altea → OK. ⏱ 0.5h. 💰 ×4 le coût blog actuel. |
| D2 | **Auteur premium E-E-A-T** | ❌ | Aujourd'hui : articles sans author structured. **Action** : (1) créer 2-3 personas fictifs par site (déjà en cohérence avec About), (2) persister dans `site.authors[]` avec bio 150 mots + photo Nano Banana + credentials, (3) assigner aléatoirement à chaque article + Schema `author: Person { sameAs }`. ⏱ 3h. 💰 3 × 0.02 $ image + 3 × 0.01 $ bio = **0.09 $/site** (unique). Gain : E-E-A-T fort. |
| D3 | **Internal linking dense articles → PDP/guides** | ⚠️ | Quelques liens. **Action** : passe LLM dédiée post-génération qui ajoute 8-12 liens internes par article (vers ≥3 PDP, ≥1 buyer guide, ≥2 autres blog posts, ≥1 glossaire). ⏱ 2h. 💰 +0.01 $ par article. |
| D4 | **Schema BlogPosting + Article complet** | ⚠️ | Schema basique. **Action** : enrichir (wordCount, headline, author Person, publisher Organization, image, articleSection, keywords). ⏱ 0.5h. |

---

## E. AEO (featured snippets + ChatGPT/Perplexity/Gemini)

| # | Item | Statut | Détail |
|---|------|--------|--------|
| E1 | **Réponse directe en 1er paragraphe** | ❌ | Aujourd'hui le 1er paragraphe d'une PDP est marketing, pas une réponse directe à la query. **Action** : ajouter au prompt narrative une section `aeo_snippet` de 40-60 mots qui répond directement à "qu'est-ce que {produit}" / "comment fonctionne {produit}". Render en haut de description. ⏱ 1h. 💰 +0.005 $/produit. |
| E2 | **Listes + tableaux structurés** | ⚠️ | Specs OK. Listes to-do/features pas toujours présentes. **Action** : forcer au moins 1 `<ul>` et 1 `<table>` par PDP. ⏱ 0.5h. |
| E3 | **Voice search queries couvertes** | ✅ | 299 keywords sur Altea répartis sur 10 intents dont conversationnels ("comment choisir", "pour quel usage"). Suffit. |
| E4 | **llms.txt + llms-full.txt** | ✅ | Endpoints `/api/public/sites/{id}/llms.txt` et `llms-full.txt` déjà servis. À valider qu'ils sont bien référencés dans le sitemap et `robots.txt`. ⏱ 0.25h. |

---

## F. GEO (Generative Engine Optimization — être cité par les LLMs)

| # | Item | Statut | Détail |
|---|------|--------|--------|
| F1 | **Schema.org Organization avec sameAs** | ⚠️ | Organization émis mais `sameAs` vide ou partiel. **Action** : obliger le remplissage des `sameAs` (LinkedIn, Instagram, Pinterest, Facebook) à la création du site (même vers comptes vides dans un 1er temps → fill plus tard). Persister dans `site.brand_social[]`. ⏱ 1h. |
| F2 | **Press release auto** | ❌ | **Action** : service `press_release_generator.py` — à chaque publish initial, générer 1 communiqué 400 mots avec Schema NewsArticle, publié sur `/press/{slug}` + POST vers un agrégateur gratuit (openpr.com, webwire) OU simplement publié localement + ping IndexNow. ⏱ 4h. 💰 0.05 $/site. Gain : +1-2 backlinks + signaux de fraîcheur. |
| F3 | **Citation tracker actif** | ✅ | Service `CitationTrackerPanel` existe dans admin. À valider qu'il tourne et remonte des insights. ⏱ 0h (existant). |
| F4 | **Brand mentions monitoring** | ⚠️ | Voir F3. Panel existe, à câbler dans cron si pas déjà fait. |

---

## G. Server-side rendering / SEO crawling 🚨

| # | Item | Statut | Détail |
|---|------|--------|--------|
| G1 | **SSR / pré-rendering meta tags** | ❌ **CRITIQUE** | **Preuve** : `curl https://altea-home.com/products/<slug>` retourne **UNIQUEMENT le shell Altiaro plateforme** : `<title>Altiaro`, `<meta description>=Altiaro`, `og:url=altiaro.com`, 0 occurrence du nom du produit. Le HTML brut fait 7794 octets dont 3865 sans scripts. **Googlebot moderne rend bien le JS mais Bing, DuckDuckGo, Yandex, Qwant et surtout les bots des LLMs (GPTBot, ClaudeBot, PerplexityBot) ne le font PAS ou mal.** Conséquence : tout le travail SEO/AEO/GEO est invisible pour ces bots → ranking effondré sur 40 % du trafic organique potentiel. **Action impérative** : ajouter un middleware FastAPI qui, pour les paths `/products/*`, `/collection/*`, `/blog/*`, `/about`, `/`, sert un `index.html` modifié avec `<title>`, `<meta>`, `og:`, `<script type=application/ld+json>` injectés côté serveur. Les données viennent de Mongo avec le site_id résolu via custom domain middleware. React hydrate par-dessus. ⏱ 8h (architecture + implémentation + tests). 💰 0. **C'est la tâche n°1 absolue pour gagner en SEO.** |
| G2 | **Full SSR du body (pré-render)** | ❌ | Idéal mais plus coûteux en infra. **Alternative MVP** : G1 suffit pour la plupart des bots si le body reste React-only, à condition que la meta/schema soient SSR et que le content soit facilement crawlable via les endpoints `/api/public/`. Googlebot suit `<script type=application/ld+json>` même si le DOM est JS-only. ⏱ 24h si on veut vraiment faire du full SSR Nuxt-like. À reporter post-MVP. |

---

## H. Off-page

| # | Item | Statut | Détail |
|---|------|--------|--------|
| H1 | **Pinterest auto-publication** | ❌ | Silver Economy + mobilier = formidable fit Pinterest. **Action** : OAuth Pinterest + service qui pin chaque nouveau produit avec 3-4 styles/couleurs × lifestyle image + description + link PDP. ⏱ 8h + OAuth. 💰 0. Gain potentiel : +1000 vues/mois par épingle virale. |
| H2 | **Reddit / forums niche scraping** | ❌ | **Action** : service qui scrape hebdomadairement r/AskOldPeople, r/ElderAbuse (prévention), forums seniors-actifs, et identifie 5 questions chaudes → suggère sujets blog via `content_gaps`. ⏱ 6h. |
| H3 | **HARO / SourceBottle automation** | ❌ | **Action** : monitoring des alerts journalistes sur la niche + auto-répond via Claude avec quote + link. Génère des backlinks DR 50+. ⏱ 10h. Plutôt V2. |
| H4 | **Post sur le blog IndexNow ping** | ✅ | `indexnow.py` + cron daily resync + ping on publish présents. |

---

## Synthèse effort total par bloc

| Bloc | Heures | $/site (LLM) | Priorité |
|------|--------|------|----------|
| A — URL & technique | ~13h | +0.01 | Haute |
| B — Contenu PDP | ~11h | +0.51 | Haute |
| C — Pages structurelles | ~24h | +2.78 | **Maximum** |
| D — Blog premium | ~6h | +0.10 (unique) + ×4 blog actuel | Moyenne |
| E — AEO | ~2h | +0.01 | Haute |
| F — GEO | ~5h | +0.05 | Moyenne |
| G — SSR/prerendering | ~8h | 0 | **Critique** |
| H — Off-page | ~24h | 0 | Moyenne (V2) |
| **Total MVP v2** | **~69h** | **~3.5 $/site** | |

Cible : **+150 à +250 keywords positionnables par site en 60-90 jours**, +30 % chance featured snippets, visibilité dans ChatGPT/Perplexity/Gemini pour les requêtes de longue traîne.

---

# 🎯 TOP 10 CHANTIERS PRIORISÉS

Par ordre décroissant d'impact/coût — ce qu'il faut faire dans le prochain sprint.

### 1. 🚨 SSR meta/schema injection (G1)

- **Why** : sans ça, 40 % du trafic organique (Bing + LLM bots) est invisible. Tout le reste est conditionné à ce prérequis.
- **Where** : nouveau middleware FastAPI `backend/middleware/spa_seo_renderer.py` (après `custom_domain_middleware`). Intercepte `GET /` + `/products/*` + `/collection/*` + `/blog/*` + `/about`, résout le site via `custom_domain`, lit `products`/`sites`/`blog_posts`, génère un `index.html` modifié avec `<title>`, `<meta>`, `og:*`, `twitter:*`, `<link rel=canonical>`, `<link rel=alternate hreflang>`, `<script type=application/ld+json>`. Frontend hydrate par-dessus sans régression.
- **Effort** : **8h**
- **Coût LLM** : 0 $
- **Gain SEO concret** : **+40 %** de couverture crawl (Bing/LLM bots) + featured snippets possibles sur Google sans dépendre du JS rendering.

### 2. 🏗 Buyer Guides auto × 5 (C1)

- **Why** : C'est le single biggest SEO lever après le SSR. Le trafic "guide d'achat / comment choisir" est massif et converti bien.
- **Where** : nouveau `backend/services/buyer_guides_generator.py`, appelé en step 9 de `launch.py` (juste après `keywords/discover`). Output persisté dans `landing_pages` (existe déjà, kind=`buyer_guide`). Frontend : route `/guides/:slug` + template React `pages/StorefrontGuide.jsx`.
- **Effort** : **8h**
- **Coût LLM** : +0.75 $/site
- **Gain SEO** : **+60 keywords positionnables** longue-traîne, +5 pages structurelles de 2000 mots ranking top 10, hausse de la confiance E-E-A-T.

### 3. 📚 Glossaire niche (C4)

- **Why** : chaque terme = 1 page longue-traîne SEO. 40 pages = 40 keywords très ciblés très peu concurrentiels, backlinks internes denses.
- **Where** : `backend/services/glossary_generator.py`, appelé step 9. 40 docs dans `glossary_terms` (nouvelle collection). Route `/glossaire` (index) + `/glossaire/:term`. Schema `DefinedTerm`.
- **Effort** : **5h**
- **Coût LLM** : +0.60 $/site
- **Gain SEO** : **+40 keywords informationnels**, +40 pages internes qui drainent du jus SEO vers PDP/buyer guides.

### 4. 🔄 Comparison pages X vs Y × 10 (C2)

- **Why** : requêtes "X vs Y" = intent commercial fort, faible concurrence SEO, conversion boost.
- **Where** : `backend/services/comparison_generator.py`, step 9. 10 docs dans `landing_pages` (kind=`comparison`). Route `/compare/a-vs-b`.
- **Effort** : **4h**
- **Coût LLM** : +0.80 $/site
- **Gain SEO** : **+20 keywords navigationnels** haut de funnel, +10 pages ranking.

### 5. 📝 About page premium + persona auteurs E-E-A-T (C5 + D2)

- **Why** : E-E-A-T est maintenant un critère majeur de ranking Google. Un site avec About pauvre et auteurs anonymes perd 20-30 % de son potentiel. Ici 2-3 personas fictifs premium cohérents avec la niche + About 1000 mots.
- **Where** : `backend/services/brand_narrative_generator.py` étendu ; persister dans `site.about_rich` + `site.authors[]`. Photos via Nano Banana avec prompt "portrait studio editorial". Frontend : enrichir `StorefrontPages.jsx::/about`.
- **Effort** : **6h**
- **Coût LLM** : +0.22 $/site (unique par site, pas par article)
- **Gain SEO** : E-E-A-T boost (effet multiplicateur sur ranking de tout le site) + +5 keywords marque.

### 6. 🏆 Top X de l'année × 5 (C3)

- **Why** : requêtes "Top 5 {catégorie} {année}" très demandées, évergreen (juste mettre à jour l'année chaque 1er janvier via cron).
- **Where** : `backend/services/top_lists_generator.py`, step 9. Route `/top/:slug`. Schema `ItemList` + `Article`.
- **Effort** : **3h**
- **Coût LLM** : +0.50 $/site
- **Gain SEO** : **+25 keywords transactionnels** haute-intention.

### 7. 🖼 Image alt SEO-rich auto (A7) + WebP/AVIF pipeline (A8 light)

- **Why** : Google Image Search = source de trafic sous-exploitée pour le mobilier/Silver Eco. Alt riches + WebP = double win.
- **Where** : (A7) prompt additionnel dans `product_variant_pipeline.py` → Claude Haiku générant l'alt à chaque style. (A8 light) transformer PNG → WebP @ 800 à l'upload via Pillow (déjà en dépendance), stocker les deux, servir `<picture>`.
- **Effort** : **5h** (2h A7 + 3h A8 light)
- **Coût LLM** : +0.01 $/site
- **Gain SEO** : Google Image Search + LCP (Core Web Vitals) + accessibilité.

### 8. 📋 FAQ/HowTo Schema injection sur PDP (A4 + B2 + B3)

- **Why** : les PDP ont les données mais pas le Schema → invisible pour les featured snippets Google et pour les LLMs.
- **Where** : `components/SEOHead.jsx` + `services/seo_jsonld.py` — ajouter FAQPage + HowTo + Organization + WebSite+SearchAction dans la liste `schema=[...]` pushée sur chaque page.
- **Effort** : **2h**
- **Coût LLM** : 0 $
- **Gain SEO** : +30 % chance d'obtenir un featured snippet "position 0" + meilleure lecture par les LLM bots.

### 9. ✍️ Blog : 4 articles/semaine + dense internal linking (D1 + D3)

- **Why** : 4× plus de contenu frais = 4× plus de points d'entrée SEO. Internal linking = distribue le jus.
- **Where** : `routes/blog_posts.py::_schedule_next_blog_jobs` augmenter à 4/semaine. Ajouter étape post-génération dans le worker qui fait 1 call Claude pour injecter 8-12 liens internes.
- **Effort** : **2.5h**
- **Coût LLM** : ×4 coût blog actuel (≈+2 $/mois/site) + +0.01 $/article pour linking pass.
- **Gain SEO** : +200 keywords couverts en 90 jours.

### 10. 🧩 AEO snippet en haut de PDP (E1) + migration slug-based globale (A9)

- **Why** : AEO direct answer = partage ChatGPT/Perplexity instantané. A9 = cohérence SEO globale (aucune URL UUID résiduelle).
- **Where** : (E1) prompt Claude additionnel dans narrative → champ `aeo_snippet` ; render en haut de `StorefrontProduct`. (A9) sed sur 18 fichiers pour remplacer les derniers `/shop/${siteId}/...` par `shopPath(siteId)` / `productPath(...)`.
- **Effort** : **2.5h** (1h E1 + 1.5h A9)
- **Coût LLM** : +0.005 $/site
- **Gain SEO** : présence dans les réponses LLM + 0 URL UUID indexée.

---

## 💰 Budget LLM total par site (Top 10 implémentés)

| Poste | Coût/site |
|---|---:|
| Buyer Guides (5) | 0.75 $ |
| Glossaire (40 termes) | 0.60 $ |
| Comparaisons (10) | 0.80 $ |
| Top Lists (5) | 0.50 $ |
| About + personas (unique) | 0.22 $ |
| Blog dense linking (×4/semaine × linking) | +2.00 $/mois |
| Alt SEO-rich | 0.01 $ |
| FAQ étendue (PDP + site) | 0.20 $ |
| AEO snippets | 0.05 $ |
| **Total launch** | **~3.13 $/site** (+2 $/mois récurrent blog) |

Comparé au coût actuel d'un launch (~3 $), c'est un doublement du budget IA pour une multiplication par 5-10 du trafic organique attendu à 90 jours. **ROI très élevé**.

---

## ⏱ Roadmap d'implémentation suggérée

**Sprint 1 (1 semaine — dépannage critique)** : #1 SSR + #8 Schema enrichi + #10 AEO + migration slug = **12h**.

**Sprint 2 (1 semaine — gros gains content)** : #2 Buyer Guides + #3 Glossaire + #4 Comparisons = **17h**.

**Sprint 3 (1 semaine — E-E-A-T + volume)** : #5 About premium + #6 Top Lists + #9 Blog 4/sem = **11.5h**.

**Sprint 4 (perf)** : #7 Alt + WebP = **5h**.

**Total** : **~46h** sur 4 sprints pour un saut de niveau complet en SEO/AEO/GEO.

---

## Annexe — Fichiers clés référencés

- `backend/routes/seo.py` — sitemap, robots.txt, llms.txt, merchant feed, i18n-config
- `backend/routes/seo_factory.py` — keywords/discover, keywords/cluster, landings/generate
- `backend/routes/seo_studio.py` — JSON-LD per PDP, AEO readiness, bulk optimize, keyword strategy
- `backend/routes/seo_automation.py` — cron weekly reports, emerging-keywords, content-gaps
- `backend/routes/aeo.py` — AEO-specific endpoints
- `backend/services/seo_jsonld.py` — JSON-LD builders (extend ici pour FAQ/HowTo/Org)
- `backend/services/product_variant_pipeline.py` — extend ici pour alt SEO + aeo_snippet + use_cases + vs_alternatives
- `backend/routes/launch.py` — orchestrateur 10 étapes, hooker les nouveaux generators ici en step 9
- `backend/routes/blog_posts.py` — blog worker, extend cadence + linking pass
- `frontend/src/components/SEOHead.jsx` — normaliser meta + schema à un seul endroit
- `frontend/src/lib/shopUrls.js` — helpers URL canoniques (déjà créé)

Collections Mongo à utiliser :
- `landing_pages` (existe, 0 docs) — pour buyer_guides, comparisons, top_lists (`kind=`)
- `glossary_terms` — NEW
- `press_releases` — NEW (si F2)
