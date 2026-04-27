#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Lot G (14 fixes UX/SEO storefront Altea) + Lot H (variantes couleur avec images dédiées).
  Décisions user 2026-04-27 :
    Q1=c+Altea exact wording, Q2=d (SEO max), Q3=d (transparent),
    Q4=c+d (logo NB+Pillow+pipeline+migration), Q5=a+d (whitelist + log admin).

backend:
  - task: "Lot G Fix 2 — Logo transparent (Pillow remove_white_background fallback)"
    implemented: true
    working: true
    file: "backend/services/favicon_generator.py + backend/scripts/lotG_fix2_logo_transparent_v2.py + backend/routes/launch.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Nano Banana ne respecte pas la consigne `transparent background` malgré le prompt
          (le logo source était en mode RGB = fond blanc opaque).
          Fix 3 couches :
          (1) Helper `remove_white_background()` + `ensure_alpha_channel()` dans favicon_generator.py
              (détection pixels luminance > 245, alpha=0 + edge fade pour antialiasing).
          (2) Script idempotent `lotG_fix2_logo_transparent_v2.py` : nettoie le logo source
              en place (avec backup .rgb-backup.png) + regen 5 favicons.
              Exécuté pour Altea : logo passe RGB → RGBA, 45% pixels transparents,
              favicon-32 70% transparent, android-512 79% transparent.
          (3) Pipeline `launch.py` : cleanup automatique du logo source via
              `ensure_alpha_channel()` après chaque génération Nano Banana.
              Tous les futurs sites auront un logo RGBA propre.
          Idempotent — peut être réexécuté sans effet de bord.

frontend:
  - task: "Lot G Fix 12 — ProductCard unifié (Home, Collection, Search, CrossSell)"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/ProductCard.jsx + ProductGrid.jsx + CrossSellProducts.jsx + pages/StorefrontCollection.jsx + pages/StorefrontSearch.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          ProductCard unifié remplace 4 designs distincts (Home/Collection/Search/CrossSell).
          Design épuré premium type Apple Watch / Hermès : aspect-square, fond ivoire,
          rounded-2xl, hover scale subtil, badges featured + promo, typo Cormorant.
          2 modes : "default" (grilles principales) et "compact" (cross-sell).
          Pas de CTA inline (clic → fiche). Visuel cohérent partout.

  - task: "Lot G Fix 13 — PageHero transparent (pages secondaires)"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontPages.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Retrait du fond accent_color sur les <PageHero>. Hérite désormais du body
          (transparent), border-bottom subtil. Texte H1 anthracite + eyebrow accent primary.
          Cohérent multi-sites (s'adapte à toute palette).

  - task: "Lot G Fix 1 — Testimonials Embla Carousel infini"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/Testimonials.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Migration de marquee CSS vers Embla Carousel. loop:true, dragFree:true,
          autoplay setInterval 3.8s avec pause on hover. Boutons nav prev/next desktop.
          6 portraits IA en DB Altea (3 v2 + 3 g6 récents). Cards 280×420 mobile,
          320×480 desktop. Fallback DEFAULT (Unsplash) en mode FR si DB vide.

  - task: "Lot G Fix 6 — ProductBundle filter role upsell/accessory"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/ProductBundle.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Filtre `isCompanion` (role ∈ {upsell, accessory, addon, accessoire}, case-insensitive).
          S'applique aux 2 priorities : bundles_with explicites + fallback même catégorie
          (qui devient "tous les produits du site filtrés"). Si zéro candidat → return null
          (la section "Souvent achetés ensemble" disparaît proprement).
          DB Altea : 3 produits role=upsell (coussin, cover, blanket) prêts à être bundlés.

  - task: "Lot G Fix 3 — Mobile fiche produit edge-to-edge sous header"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontProduct.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          - Galerie en `-mx-6 md:mx-0` (déjà en place) → image full-width mobile.
          - Wrapper px-6 md:px-10 → `pt-0 md:pt-12` (était pt-8) → image collée au header.
          - Breadcrumb caché en mobile (`hidden md:block`) → image juste sous le bandeau récap.
          Desktop inchangé : breadcrumb + grid 1.1fr/1fr classique.

  - task: "Lot G Fix 5 — 4 USPs Altea + helper pipeline"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontProduct.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Carte grise (highlights bullets) remplacée par 4 USPs visuelles avec icônes :
            Truck → Livraison offerte / sous 72h
            ShieldCheck → Garantie 2 ans / incluse
            ArrowsCounterClockwise → Retour gratuit / 14 jours
            Headphones → Support 7j/7 / Conseillers experts
          Wording exact validé user 2026-04-27. Lecture optionnelle de `design.usps`
          (4 objets {icon, label, sub}) pour propagation multi-sites via helper Claude
          Haiku dans le pipeline launch.py (à implémenter au prochain Lot).
          Test : data-testid='product-usps' présent (1), product-usp-* (4).
          data-testid='product-highlights' supprimé (0) confirmé.

  - task: "Lot G Fix 9 — SEO Product complet (déjà très avancé)"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontProduct.jsx + components/SEOHead.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Existant déjà solide :
          - JSON-LD Product (sku, brand, offers, shippingDetails, MerchantReturnPolicy,
            aggregateRating, reviews, priceValidUntil)
          - JSON-LD BreadcrumbList
          - JSON-LD FAQPage (conditionnel, 12 max)
          - JSON-LD HowTo (conditionnel, usage_steps)
          - SEOHead : title, description, canonical, OG (title/desc/type/locale/url/image/site_name),
            Twitter (card/title/desc/image), keywords, robots max-image-preview:large,
            hreflang multi-lang + x-default
          - Alt textes déterministes via `altFor()` dans ProductGallery (style-aware)
          - Image LCP : 1ère image en `loading="eager"`, autres en lazy
          - H1 : `narrative.headline` Claude-generated (déjà brand-prefixed dans Altea :
            "Fauteuil releveur électrique Altea — Massage intégré")
          Améliorations apportées :
          - SEOHead `image={getPrimaryImage(p)}` (priorité IA studio sur AliExpress)
          - JSON-LD `image: getProductGallery(p).slice(0,6)` (gallerie IA d'abord)

  - task: "Lot G Fix 10 — Hide Altiaro markup dans Domain Purchase UI"
    implemented: true
    working: true
    file: "frontend/src/pages/Domains.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Suppression de la mention "(coût OVH X€ + frais plateforme Y€)" affichée
          au concepteur. Il ne voit que le prix TTC final (transparent commercial).

  - task: "Lot G Fix 14 — /track avec StorefrontLayout"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontTrack.jsx"
    stuck_count: 0
    priority: "low"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Déjà en place (line 64) : <StorefrontLayout site={site}>{contenu}</StorefrontLayout>.
          Aucune modif nécessaire — confirmé visuellement, header + footer storefront cohérents.

  - task: "Lot H Fix 1 — Whitelist axes variantes (Ships From, Plug Type)"
    implemented: true
    working: true
    file: "backend/services/variant_filter.py + backend/routes/sourcing.py + backend/scripts/lotH_fix1_clean_variants.py + frontend/src/components/storefront/VariantPicker.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Architecture défense en profondeur (3 couches) :
          (1) Backend `services/variant_filter.py` : heuristique de classification des
              axes par VALEURS (pas par label, schéma actuel sans axis_label).
              `classify_axis()` retourne 'ships_from' | 'plug' | 'useful'.
              `filter_useless_axes()` strip axes parasites + dédoublonne `properties[]`.
              Whitelist stricte (a) + log admin (d) selon décision user 2026-04-27.
              SHIPS_FROM_VALUES couvre ~50 pays + warehouse keywords + ISO codes.
          (2) Pipeline import `routes/sourcing.py` : appelle `filter_useless_axes_with_log()`
              juste après `_map_ae_skus_to_variants()`. Notification async vers
              `db.admin_notifications` (type=variant_axis_filtered) après insert.
              Tous les futurs imports AE auront un `variants[]` propre par défaut.
          (3) Frontend défensif `VariantPicker.jsx` : filtre `isParasiticAxis()` côté
              affichage (regex pays + plug). Sécurité si site pas encore migré.

          Audit Altea exécuté : 4/9 produits cleaned, axe "GERMANY" supprimé partout.
          DB : 10 main variants total, 0 GERMANY restant ✅.
          admin_notifications : 4 docs type=variant_axis_filtered créés (audit OK).

          Test visuel confirmé : fiche fauteuil 1233€ Altea → axe COLOR seul,
          3 swatches Black/White/Brown, "GERMANY" totalement disparu.

  - task: "Lot H Fix 5 — VariantPicker swatches couleur visuels"
    implemented: true
    working: true
    file: "frontend/src/lib/colorMapping.js + frontend/src/components/storefront/VariantPicker.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          - `lib/colorMapping.js` : dictionnaire FR + EN → CSS hex (~80 couleurs).
            Insensible à la casse + accents (normalize NFD strip diacritics).
            Helpers : colorFromName(), isColorAxis(), colorFromNameOrFallback(),
            isLightColor() (ITU-R BT.601 luminance pour border conditional).
            Cas spéciaux : "MULTI" → conic-gradient arc-en-ciel,
            "PATTERN" → repeating-linear-gradient gris diagonale.
          - `VariantPicker.jsx` : détection auto axe couleur via `isColorAxis(values)`.
            Si oui → swatches cercles 36-40px (32 mobile) avec :
              · background = colorFromNameOrFallback (gris neutre si non reconnu)
              · border subtil pour couleurs claires (white/ivory/cream)
              · ring 2px + scale 1.10 + check icon quand sélectionné
              · scale 1.10 hover + ring 2px gris léger sur hover (si dispo)
              · opacity 30% + barre diagonale si out-of-stock
              · aria-label complet pour accessibilité
              · focus-visible:ring pour navigation clavier
            Sinon (taille, modèle) → boutons rectangulaires texte (comportement initial).
          - Test visuel confirmé : 3 swatches Noir/Blanc/Brun avec ✓ blanc sur noir actif.
          - data-testid='variant-axis-X' + data-axis-kind='color' pour Playwright.

metadata:
  created_by: "main_agent"
  version: "1.3"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Lot G Fix 12 — ProductCard unifié"
    - "Lot G Fix 5 — 4 USPs Altea"
    - "Lot G Fix 1 — Testimonials Embla Carousel"
    - "Lot G Fix 2 — Logo transparent + favicons RGBA"
    - "Lot G Fix 6 — ProductBundle filter role"
    - "Lot G Fix 3 — Mobile edge-to-edge fiche produit"
    - "Lot G Fix 13 — PageHero transparent"
    - "Lot H Fix 1 — Whitelist axes variantes (ships_from filter)"
    - "Lot H Fix 5 — VariantPicker swatches couleur"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "testing"
    message: |
      ## Lot G + H1 + H5 — RÉSULTATS TESTS (Desktop 1920x1080 + Mobile 390x844)
      
      ✅ F1 Testimonials Embla — PASS
         - storefront-testimonials présent (1), 6 review-card, prev+next buttons desktop, next click fait défiler OK
         - Mobile : 6 cards présentes (swipe natif)
      ✅ F2 Logo transparent + Favicon — PASS
         - Header logo background rgba(0,0,0,0) (transparent) desktop ET mobile
         - Favicon URL /api/uploads/favicons/.../favicon-32.png → HTTP 200
      ✅ F3 Mobile edge-to-edge — PASS (code-verified)
         - Breadcrumb a classe "hidden md:block" (hidden en mobile, visible desktop confirmé)
         - Image gallery : -mx-6 md:mx-0 appliqué
         - Desktop : product-breadcrumb visible=true confirmé
      ✅ F5 4 USPs — PASS
         - product-usps container (1), product-usp-0..3 (4) présents
         - Texts exacts : "Livraison offerte/sous 72h", "Garantie 2 ans/incluse", "Retour gratuit/14 jours", "Support 7j/7/Conseillers experts"
         - 4 icônes SVG Phosphor visibles
         - product-highlights count=0 (ancienne carte grise absente) ✅
         - Mobile : grid 2-col confirmé (USPs 0&1 même y, 2&3 ligne suivante)
      ✅ F6 ProductBundle filter — PASS
         - Bundle "Souvent achetés ensemble" présent
         - Produits : "Coussin ergonomique lombaire" (39€) + "Protection anti-taches" (29€) = upsells uniquement
         - Aucun autre fauteuil principal >1000€ dans le bundle ✅
      ✅ F12 ProductCard unifié — PASS
         - Home : 6 product-card-* sans CTA inline
         - Collection : 6 collection-product-* sans CTA inline
         - Search (q=fauteuil) : 6 search-result-* sans CTA inline
         - Fiche produit cross-sell : 4 xsell-* présents
      ✅ F13 PageHero transparent — PASS
         - /about, /faq, /contact, /livraison, /retours : hero hérite body rgb(255,255,255) (blanc body)
         - Aucun fond accent_color détecté, H1 visible
      ✅ H1 Axes parasites filtrés — PASS
         - Body text ne contient NI "GERMANY"/"Germany" NI "Ships From"/"Emplacement" (desktop + mobile)
         - variant-picker (1), variant-axis (1), color axis (1) — axe couleur uniquement ✅
      ✅ H5 Swatches couleur — PASS
         - 3 variant-option-0-* swatches cercles rounded-full (border-radius 9999px)
         - Black : rgb(26,26,26) ✅ (#1a1a1a)
         - White : rgb(255,255,255) ✅
         - Brown : rgb(107,68,35) ✅ (#6B4423)
         - Aria-label format "Couleur X (sélectionnée)" — accessible
         - Click White → ring-2 ring-offset-2 appliqué (état actif OK)
         - Mobile : 40x40px (sélectionné 44x44 avec ring). Desktop md:w-10 (40px) ✅
         - Label axe "COLOR · White" affiché (nom couleur sélectionnée)
      
      AUCUNE régression visuelle détectée. Cookie banner RGPD visible et fonctionnel.
      Les 9 fixes (7 Lot G + 2 Lot H) sont VALIDÉS en production.
      
  - agent: "main"
    message: |
      Lot G + H1 + H5 livrés, prêts pour test agent.
      Validation visuelle confirmée sur Altea (fauteuil 1233€) :
      - GERMANY disparu, 3 swatches couleur Black/White/Brown
      - Logo Altea transparent dans le header
      - 4 USPs visuelles avec wording exact
      - Cookie banner RGPD actif
      - Lint Python+JS OK partout
      - Backend /api/health 200, Frontend 200

      À tester par testing agent en mobile (390x844) + desktop (1920x1080) :
      LOT G — 7 fixes :
      - F1 Testimonials carousel infinite scroll + autoplay 3.8s + pause hover
      - F3 Mobile fiche produit edge-to-edge (image full-width sous header)
      - F5 4 USPs (Livraison/Garantie/Retour/Support) au-dessus add-to-cart
      - F6 ProductBundle ne montre que upsells/accessories (pas d'autres mains)
      - F12 ProductCard cohérent partout (Home, Collection, Search, CrossSell)
      - F13 PageHero transparent sur pages secondaires (FAQ, Contact, Livraison...)
      - F2 Logo Altea transparent + favicons RGBA propres

      LOT H — 2 fixes :
      - H1 Plus aucun "GERMANY"/Ships From dans VariantPicker
      - H5 Swatches couleur (cercles ~36-40px) sur axe couleur, pills sur autres axes

  - agent: "testing"
    message: |
      ## Lot G + H — RE-VALIDATION après corrections (Desktop 1920×1080 + Mobile 390×844)
      Site Altea — 6867223e-7ea5-45a7-815a-300cd89b7656 — 2026-04-27

      ═══════════════════════════════════════════════
      PRIORITÉ 1 — G12 CARDS HOME = COLLECTION ✅ PASS (pixel-perfect)
      ═══════════════════════════════════════════════
      Comparaison strict equality Home vs Collection (même produit "Rise & recline chair…") :
        · card_bg           : rgb(245,245,245) === rgb(245,245,245)  ✅ (ivoire identique)
        · img_parent_bg     : rgb(255,255,255) === rgb(255,255,255)  ✅ (fond blanc pour image)
        · img_src           : même URL studio_v2 p_1735081a…          ✅
        · title_font        : "Cormorant Garamond", serif === même   ✅
        · title_text        : identique                                ✅
        · highlights_count  : 3 === 3                                  ✅ (check icons ✓ couleur primary rgb(10,10,10))
        · price_text        : €1,033.45 === €1,033.45                 ✅
        · eyebrow_text      : "Free shipping within 72h" === même     ✅ (FREE SHIPPING équivalent EN)
        · cta_count         : 2 === 2                                  ✅ (product-details-X + product-add-to-cart-X)
        · card_width        : 384px === 384px                          ✅
        · card_height       : 648.5625px === 648.5625px                ✅ (identique au pixel près)
        · border-top divider présent entre highlights et footer       ✅

      Layout responsive :
        · DESKTOP 1920 : Home `products-grid` = 384px × 3  /  Collection `collection-grid` = 384px × 3  ✅
        · MOBILE 390  : Home = 342px (1 col)  /  Collection = 342px (1 col)  ✅
      Note : StorefrontCollection passe testId="collection-product-{id}" (ce n'est PAS product-card-).
             Les data-testid internes product-details-{id} et product-add-to-cart-{id} restent identiques.

      ═══════════════════════════════════════════════
      PRIORITÉ 2 — H4 GALERIE VARIANT-AWARE ✅ PASS
      ═══════════════════════════════════════════════
      Fiche fauteuil 1233€ (id 2a31bb75…) — default affiche image NOIR, puis :
        · click variant-option-0-White  → galerie passe à  /variants/white/studio_dea7fd7c.png  ✅
        · click variant-option-0-Brown  → galerie passe à  /variants/brown/studio_35563578.png  ✅
        · ProductEditorialMosaic (data-testid=product-editorial-mosaic) reflète la variante :
            /variants/white/closeup_*.png + /variants/white/lifestyle_*.png + /variants/white/studio_*.png  ✅
        · NarrativeSections : 8 images /variants/white/ présentes dans la page après switch  ✅

      ═══════════════════════════════════════════════
      PRIORITÉ 3 — G13 PAGES SECONDAIRES TRANSPARENTES ✅ PASS (9/9)
      ═══════════════════════════════════════════════
      Pour chacune des 9 pages, first section/hero : background-color = rgba(0,0,0,0), background-image: none
        ✅ /about           — bg rgba(0,0,0,0)  (H1 "Altea — L'art du repos retrouvé")
        ✅ /contact         — bg rgba(0,0,0,0)
        ✅ /faq             — bg rgba(0,0,0,0)
        ✅ /livraison       — bg rgba(0,0,0,0)
        ✅ /retours         — bg rgba(0,0,0,0)
        ✅ /blog            — bg rgba(0,0,0,0)
        ✅ /track           — bg rgba(0,0,0,0)
        ✅ /cgv             — bg rgba(0,0,0,0)
        ✅ /mentions        — bg rgba(0,0,0,0)

      ═══════════════════════════════════════════════
      PRIORITÉ 4 — Régressions Lot G/H ✅ PASS
      ═══════════════════════════════════════════════
        ✅ Logo Altea transparent : bg rgba(0,0,0,0) + src …logo_*_transparent_df84281e.png
        ✅ Testimonials Embla : data-testid=storefront-testimonials présent, 6 cards
        ✅ VariantPicker swatches : 3 cercles Black/White/Brown (variant-option-0-Black/White/Brown)
        ✅ Zéro "GERMANY" / "Ships From" : has_germany=false dans page text
        ✅ 4 USPs Altea : product-usp-0..3 présents (4)
        ✅ ProductBundle : aucun produit 1000€+ parasite (bundle_prices vide ou filtré par role)

      ═══════════════════════════════════════════════
      VERDICT FINAL : TOUS LES FIXES LOT G + LOT H VALIDÉS ✅
      ═══════════════════════════════════════════════
      Aucune régression détectée. Cards Home ↔ Collection strictement identiques
      (même bg, même image, même padding, même hauteur 648.5625px, mêmes 2 CTAs).
      Galerie variant-aware fonctionnelle pour main + mosaic + narrative.
      9/9 pages secondaires avec hero transparent.

