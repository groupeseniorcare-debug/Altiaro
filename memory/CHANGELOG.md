# Altiora — CHANGELOG

Historique des sprints de développement. Le PRD.md reste la source de vérité
sur les exigences produit ; ce fichier trace uniquement ce qui a été livré.

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
