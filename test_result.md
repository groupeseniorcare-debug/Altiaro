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
  - task: "Lot G Fix 12 — ProductCard RICHE unifié (CORRIGÉ)"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/ProductCard.jsx + ProductGrid.jsx + CrossSellProducts.jsx + pages/StorefrontCollection.jsx + pages/StorefrontSearch.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "main"
        comment: |
          🚨 INVERSION DE LOGIQUE : 1ʳᵉ tentative avait extrait un ProductCard
          ÉPURÉ (basé sur le rendu Collection minimaliste) et l'avait appliqué
          partout, ce qui APPAUVRISSAIT la Home (perte highlights + dual CTA).
      - working: true
        agent: "main"
        comment: |
          ✅ CORRIGÉ 2026-04-27 : extraction du rendu RICHE original de
          ProductGrid.jsx (ancien) en composant ProductCard.jsx exporté.
          Design Aesop / Hermès / Apple Watch :
            · Image aspect-square sur fond BLANC (le produit IA ressort)
            · Card fond accent_color (ivoire dynamique du site)
            · Titre Cormorant 16/18px line-clamp-2
            · 4 highlights ✓ verts (auto-extraits via `getHighlights()`)
            · Border-top divider entre highlights et footer
            · Prix XL + eyebrow "FREE SHIPPING within 72h"
            · Dual CTA inline : flèche → fiche + bouton "Add to cart" w/ icon
            · Hover : shadow-[0_20px_60px_-20px] + translate-y-[-1] + scale-[1.04]
            · Variante "compact" sans CTA pour cross-sell sidebar
          Used everywhere : Home (ProductGrid), Collection, Search, CrossSell.
          Audit "from-scratch" : ✅ tout site créé via launch-auto utilise
          automatiquement ce composant (aucun rendu inline résiduel).
          Validation testing agent : cards Home = Collection PIXEL-PERFECT
          (bg rgb(245,245,245), img bg blanc, Cormorant, highlights ✓,
          €1,033.45, eyebrow "Free shipping", 2 CTAs, 384×648.5625px).
          Layout : 3 cols desktop / 2 cols tablet / 1 col mobile.

  - task: "Lot H Fix 4 — Galerie + composants editorial variant-aware"
    implemented: true
    working: true
    file: "frontend/src/lib/ProductColorContext.jsx + lib/productImage.js + lib/slugify.js + components/storefront/ProductGallery.jsx + ProductEditorialMosaic.jsx + NarrativeProduct.jsx + VariantPicker.jsx + pages/StorefrontProduct.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          React Context `ProductColorContext` propage la couleur sélectionnée
          à TOUS les composants enfants de la fiche produit.
          Architecture :
            StorefrontProduct
              └─ ProductColorProvider product={p}
                   ├─ ProductGallery (consume → display variant images + fade)
                   ├─ VariantPicker (publish → setSelectedColor on click)
                   ├─ ProductEditorialMosaic (consume → variant images for 4 tiles)
                   └─ NarrativeSections (consume → variant images for sections)
          Helpers `getProductGalleryForColor()`, `getStyleImageForColor()`
          dans `lib/productImage.js` lisent `generated_images_by_variant[slug]`
          avec fallback gracieux sur galerie classique si non dispo.
          Animation fade Framer Motion 320ms entre images sur changement couleur.
          `lib/slugify.js` : mirroir JS du `slugify_color()` Python.
          Validation testing agent : cliquer Black → White change la galerie
          principale + la mosaic + les sections narratives vers `/variants/white/`,
          idem pour Brown → `/variants/brown/`.

  - task: "Lot H Fix 2+3 — Régen images couleurs Altea (POC + masse)"
    implemented: true
    working: true
    file: "backend/services/color_variant_images.py + backend/scripts/lotH_h2h3_regen_color_variants.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Script idempotent qui pour chaque produit "main" :
          - Identifie la couleur "default" (= 1ère variante = images existantes)
          - Pour chaque autre couleur, régénère studio + lifestyle + closeup
            via Nano Banana img-to-img avec prompt strict (préservation 100%
            identité produit, change UNIQUEMENT couleur upholstery)
          - Stocke dans `generated_images_by_variant: {slug: [{style, url, ...}]}`
          - Hard cap budget MAX_LLM_CALLS=70 (~$3.50)
          Exécuté sur Altea : 2 produits multi-couleurs (fauteuil 1233€
          Black/White/Brown + fauteuil tissu Gray/Brown/Blue).
          12 LLM calls, ~$0.60 dépensés, 12 images générées + stockées.
          Validation visuelle : fauteuil blanc PARFAITEMENT cohérent avec
          le noir (mêmes proportions, télécommande, porte-gobelets, etc.).

  - task: "Lot H Fix 6 — Propagation pipeline launch.py (futurs sites)"
    implemented: true
    working: true
    file: "backend/routes/launch.py + backend/services/colormapping_py.py + backend/.env (MAX_COLOR_VARIANTS_AI=5)"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Helper `_generate_color_variant_images_for_product()` ajouté dans
          launch.py, appelé après la phase 8c (narrative sections) pour CHAQUE
          produit. Stratégie identique au script H2/H3 :
          - Skip si mono-variant
          - Détection axe couleur via `services/colormapping_py.is_color_axis()`
          - Default color = copie generated_images existants (0 LLM cost)
          - Autres couleurs = img-to-img Nano Banana, max=MAX_COLOR_VARIANTS_AI
          - Idempotent (skip couleurs déjà présentes)
          - Budget-aware : 402 → halt loop
          Garantit que TOUT futur site créé via launch-auto a automatiquement
          la galerie variant-aware (cohérent avec H4 frontend).

  - task: "Lot G Fix 13 — PageHero transparent (CORRIGÉ — Blog inclu)"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontPages.jsx + StorefrontBlog.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: false
        agent: "main"
        comment: |
          🐛 1ʳᵉ tentative ne touchait que <PageHero> de StorefrontPages.jsx.
          Le Blog avait son propre header inline avec fond accent_color.
      - working: true
        agent: "main"
        comment: |
          ✅ CORRIGÉ 2026-04-27 : aligné le hero du Blog (liste articles) +
          le hero du BlogPost (article individuel) sur la même structure
          transparente que <PageHero>. Validation : 9/9 pages secondaires
          (about, contact, faq, livraison, retours, blog, track, cgv,
          mentions) ont `background-color: rgba(0,0,0,0)` + `background-image: none`.

  - task: "Lot G Fix 13 — PageHero transparent (pages secondaires) — supersedé"
    implemented: true
    working: true
    file: "frontend/src/pages/StorefrontPages.jsx (covered by CORRIGÉ entry above)"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Voir entry CORRIGÉ ci-dessus."

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


## Phase 2.5 — Chaîne Launch-Auto bout en bout (2026-04-28)

frontend:
  - task: "Phase 2.5 Tâche D — ProductBundle responsive mobile vertical"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/ProductBundle.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Mobile (< md 768px) : 3 cards empilées verticalement (grid-cols-1),
          chaque card pleine largeur. Séparateurs "+" masqués en mobile
          (`hidden md:block`) car redondants quand les items sont empilés.
          Desktop (≥ md) : 3 cards en ligne avec "+" entre elles (md:flex-row).
          Validation auto via probe JS :
            - Viewport 390×844 : bundleLayout = 'vertical' ✅
            - Viewport 1440×900 : bundleLayout = 'horizontal' ✅
          Composant partagé → tous les storefronts héritent automatiquement.

  - task: "Phase 2.5 Tâche E — Refonte premium cartes Livraison + Paiement"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/DeliveryPaymentInfo.jsx (NEW) + pages/StorefrontProduct.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Nouveau composant `<DeliveryPaymentInfo>` qui remplace les anciens
          `<DeliveryEstimate>` + `<PaymentOptions>` empilés verticalement.
          Design premium Aesop / Hermès :
            - Fond #FDFCF9 (blanc cassé), bordure 1px #E8E2D5 (ivoire)
            - Eyebrow uppercase tracking-[0.24em] (DELIVERY / PAYMENT)
            - Titre Cormorant Garamond ≈18-19px font-light
            - Sous-ligne neutre gris #6B6B6B font-weight 300
            - Icône Phosphor weight="thin" monochrome (Truck / CreditCard / Lock)
            - Padding p-5 md:p-6 généreux, border-radius 2px strict
            - Pas d'emoji, pas d'icônes colorées
          Layout : `grid-cols-1 md:grid-cols-2 gap-3`.
          Validation probe JS :
            - Viewport 390 : dpLayout = 'vertical' ✅
            - Viewport 1440 : dpLayout = 'horizontal' ✅
          i18n : 6 langues (fr/en/de/nl/it/es).
          Installment affiché seulement si price ≥ 100 € ; sinon fallback
          carte "Paiement sécurisé" avec icône Lock.

  - task: "Phase 2.5 Tâche F — Unification design cards produit (Home ↔ bas page produit)"
    implemented: true
    working: true
    file: "frontend/src/components/storefront/CrossSellProducts.jsx + UpsellsRecommendations.jsx + ProductBundle.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          CrossSellProducts + UpsellsRecommendations passent de rendus inline
          ad-hoc à `<ProductCard variant="default">`, exactement le même
          composant riche utilisé par la Home (ProductGrid) / Collection /
          Search. Design strictement identique :
            - aspect-square image fond BLANC
            - card fond accent_color (ivoire dynamique)
            - titre Cormorant, 4 highlights ✓, prix XL, "FREE SHIPPING"
            - dual CTA (flèche fiche + bouton Add to cart)
            - hover shadow + translate-y-[-1] + scale-[1.04] image
          Grille 3 colonnes desktop (lg:grid-cols-3) au lieu de 4, pour
          matcher les proportions exactes de la Home.
          Filtre strict `hasAiImage()` : les produits sans `generated_images`
          (ex. accessoires AE bruts avec watermark "ShopYy…") sont **masqués**
          de Upsells + CrossSell pour préserver la cohérence premium.
          ProductBundle utilise un fallback doux : s'il n'y a pas ≥2
          companions avec image IA, il retombe sur `isCompanion` simple pour
          préserver la fonction bundle sur les sites en transition (Altea).
          Sur Altea à l'instant T : Upsells masqués (3 accessoires AE sans
          image IA), CrossSell affiche 3 fauteuils IA ✅, Bundle affiche
          3 cards dont l'accessoire Electric Blanket (fallback).
          NOTE : bug latent corrigé → `AiTweakPanel.jsx` importait `api`
          en default export (inexistant) → `import { api } from "../lib/api"`.
          Sans ce fix la compilation plantait ("Compiled with problems").

  - task: "Phase 2.5 Tâche C — Audit + test E2E launch-auto Altea (run dd97b247)"
    implemented: true
    working: true
    file: "backend/routes/launch.py (pipeline exécuté)"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Run `launch-auto` sur Altea — job id dd97b247-3314-4987-9314-469294d8d54e
            - Démarrage  : 2026-04-28 08:00:24 UTC
            - Fin        : 2026-04-28 08:18:06 UTC
            - Durée      : 17 min 42 s (1062 s)
            - Status     : completed_with_degraded
            - Checkpoints: 23/23 franchis
            - Étape dégradée : `testimonials_premium` (budget LLM dépassé
              à 43.13 $ / 43 $ max — alert_level=critical dans platform_health)
          Chronologie (T relatif à T0=08:00:24) :
            T+0 s       pct 5  brand (identité & palette)
            T+0 s       pct 12 logo (Nano Banana)
            T+29 s      pct 18 template
            T+29 s      pct 22 content-hero
            T+83 s      pct 28 content-benefits
            T+140 s     pct 34 content-testimonials
            T+193 s     pct 40 content-faq
            T+249 s     pct 46 content-about
            T+430 s     pct 52 content-contact
            T+547 s     pct 56 navigation
            T+551 s     pct 54 hero-image (IA Nano Banana)
            T+583 s     pct 56 testimonials-ai (6 portraits IA)
            T+583 s     pct 60 collections
            T+585 s     pct 62 legal (6 pages légales)
            T+585 s     pct 65 product-0 (Fauteuil 1/9)
            T+585 s     pct 65 product-0-copy (Haiku USPs/HowTo/FAQ/editorial)
            T+639 s     pct 65 product-0-images (5 studio Nano Banana)
            T+804 s     pct 68 product-1 (Fauteuil 2/9)
            T+804 s     pct 68 product-1-copy
            T+864 s     pct 68 product-1-images
            T+1052 s    pct 95 testimonials (3 portraits IA — DÉGRADÉ budget)
            T+1052 s    pct 97 cms-pages (About + Contact éditoriales)
            T+1062 s    pct 98 finalize (déblocage SEO)
          Coût LLM : ~43 $ cumulés (Emergent Universal Key) sur la fenêtre
          mensuelle (pas le coût marginal du run — partagé avec autres jobs).
          Le runner a été lancé avec overwrite=false pour ne PAS détruire
          les images IA pré-validées du pilote (White/Brown/Black).
          Artefacts livrés :
            ✅ design.brand (name Altea, palette, voix)
            ✅ design.hero premium + image IA lifestyle (femme lisant,
               fauteuil, lumière naturelle) — visible sur screenshot home.
            ✅ design.pages.about/contact/livraison/retours/faq (éditoriales)
            ✅ design.legal (6 pages)
            ✅ design.nav optimisée
            ✅ design.collections suggérées
            ✅ product[0].images 5 studio Nano Banana (pilote)
            ✅ product[1].images 5 studio Nano Banana
            ✅ product[0..5].usps/how_to_steps/faq_product/editorial_cards
            ⚠️ testimonials_premium dégradé (budget LLM) — fallback sur
               les 6 testimonials déjà en place via `testimonials-ai`.
          VERDICT : preuve E2E "1 clic → site premium complet" acquise.
          L'unique étape dégradée est une conséquence du cap budget LLM
          atteint, PAS un bug de pipeline. Le système résilience (circuit
          breaker + retry expo + `safe_claude_text`) a correctement détecté
          et persisté le `degraded_step` dans `launch_jobs.degraded_steps`,
          permettant un resume ciblé via POST `/launch-jobs/{id}/resume?only_degraded=true`.

metadata:
  created_by: "main_agent"
  version: "2.5"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Hotfix UX cockpit étape 8/9/10 (compteur, gating, copy) — 2026-04-29"
    - "Gating cockpit étape 9 (soft_unlocked sur content + seo) — 2026-04-29"
    - "GMC discovery relancée + sub-account Altea créé — 2026-04-29"
    - "Fallback HTML SSR /legal/* pour altiaro.com prod — 2026-04-29"
    - "Refonte UX cockpit /sites/:id (2026-04-29)"
    - "5 pages légales plateforme /legal/* (2026-04-29)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Run hotfix 2026-04-29 — 4 bugs UX + 2 améliorations :
      
      Bug 1 (compteur 3 vs 0) : `routes/blog_posts.py::list_blog_posts`
      lisait UNIQUEMENT `site.design.blog_posts` (array vide pour Altea)
      au lieu de `db.blog_posts` (collection avec 3 articles publiés par
      les workers async). Fix : merge des 2 sources avec dédoublonnage par
      slug, source de vérité = collection. Normalise aussi `title` quand
      le doc collection le stocke en dict i18n `{"fr": "..."}`. Validation :
      `list_blog_posts(altea)` retourne maintenant 3 articles → la liste
      "Vos contenus publiés (3)" affiche bien les 3, alignée avec le Stat.
      
      Bug 2 (étape 8 reste verrouillée) : `NextStepCTA.jsx` lisait UNIQUEMENT
      `current.completed`. Fix : nouveau cas "soft_unlocked" → CTA actif vers
      l'étape suivante avec message clair "Génération en cours en arrière-plan".
      Validation : sur `/sites/Altea/blog-posts`, l'encart "Verrouillé" est
      remplacé par un bouton ACTIF "Continuer vers Score SEO →".
      
      Bug 3 (étape 10 cliquable à tort) : `compute_step_statuses` faisait
      `previous_completed = (s.completed) OR soft_unlocked` → la cascade
      propageait le soft, débloquant artificiellement étape 10. Hotfix :
      `previous_completed = bool(s["completed"])` STRICT. Le `soft_unlocked`
      reste appliqué sur l'étape elle-même (pas blocked) mais ne propage
      pas. Validation : Altea — étape 10 désormais
      `blocked_by_previous=True` 🔒 (étapes 8 et 9 strictement non
      complétées).
      
      Bug 4 (erreur sur étape 10) : avec le gating serré, l'étape n'est
      plus accessible. Backend `qa_checklist` testé en direct → OK
      (score 81 ready=true, pas d'exception). Bug se résout naturellement.
      
      UX 1 (panel automatisation mou) : `SiteBlogPosts.jsx` réécrit. 7
      bullets ambitieux : "3 à 7 articles/sem", "50 pages atterrissage
      SEO/jour", "200+ mots-clés long-tail/produit (FR + 5 langues)",
      "FAQ Google PAA", "maillage", "Google/Bing/Yandex IndexNow",
      "content gaps versus concurrents". Phrase de clôture italique
      "Tout fonctionne en arrière-plan, 24/7, sans intervention".
      
      UX 2 (texte gating final) : `NextStepCTA.jsx` — nouveau cas
      `soft_unlocked` actif avec icône Hourglass ambré, label "Génération
      en cours en arrière-plan", reason de la check, et bouton noir
      `Continuer vers {nextLabel} →` qui navigue directement. Plus de
      bouton "VERROUILLÉ" qui prête à confusion.
      
      UX 3 (Google Ads multi-sites) : `AdminGoogleMaster.jsx` — bloc bleu
      "Architecture Google Ads multi-sites" avec icône ShieldCheck,
      explication 1 sous-compte/site sous MCC maître, mention que la
      création auto requiert Developer Token basic/standard.
      
      Budget LLM (vérification) : `/api/platform/llm-health` →
      `overall=healthy`, breakers `claude` et `nano_banana` CLOSED, 0
      failures sur les 60 dernières secondes. Recharge confirmée par
      l'utilisateur effective. `/api/platform/llm-status` →
      `last_error_at=2026-04-27T07:23:38` (avant la recharge).
      
      Lint JS : 3 fichiers patchés clean. Lint Py : `blog_posts.py` et
      `journey_gating.py` clean (E701 préexistantes hors patches).

## Hotfix UX cockpit étape 8/9/10 + Google Ads explainer (2026-04-29)

backend:
  - task: "list_blog_posts merge collection + array (compteur 3 vs 0)"
    implemented: true
    working: true
    file: "backend/routes/blog_posts.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Bug user : "Articles publiés = 3" en haut MAIS "Vos contenus
          publiés (0)" en bas. Source du conflit : 2 sources de blog
          posts en parallèle (collection `db.blog_posts` alimentée par
          les workers, array `site.design.blog_posts` alimentée par CRUD
          manuel). Le compteur lisait la collection (3 articles), la
          liste lisait l'array (vide). Fix : `list_blog_posts` merge les
          2 sources avec dédoublonnage par slug, source de vérité =
          collection. Normalise les titres i18n (`{"fr": "..."}`).
          Validé : 3 articles cohérents.

  - task: "Cascade gating stricte (étape 10 verrouillée si étape 9 partielle)"
    implemented: true
    working: true
    file: "backend/routes/journey_gating.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Bug user : "étape 10 cliquable alors que l'étape précédente
          n'était pas valide". Hotfix : `previous_completed` propage
          UNIQUEMENT la complétion stricte, pas le soft_unlocked. Le
          soft_unlocked permet à l'étape elle-même d'être accessible
          (anti-blocage workers async) mais ne déverrouille plus la
          suivante. Test Altea : étape 8 et 9 cliquables (soft), étape
          10 verrouillée (🔒 blocked_by_previous=True).

frontend:
  - task: "NextStepCTA — soft_unlocked CTA actif au lieu de Verrouillé"
    implemented: true
    working: true
    file: "frontend/src/components/NextStepCTA.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Quand `current.soft_unlocked === true && nextKey`, on rend une
          carte blanche bordée avec icône Hourglass ambré, eyebrow
          "Génération en cours en arrière-plan", reason de la check, et
          bouton primary noir `Continuer vers {nextLabel} →` qui navigue
          directement. Plus de bouton "VERROUILLÉ" trompeur qui bloquait
          l'utilisateur. Validé sur preview : `cta-step-soft-unlocked=1`,
          `cta-step-pending=0`.

  - task: "SiteBlogPosts — copy ambitieux 200+ mots-clés / IndexNow / content gaps"
    implemented: true
    working: true
    file: "frontend/src/pages/SiteBlogPosts.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Réécrit le panel "Automatisation active" avec 7 bullets
          ambitieux : "3 à 7 articles/sem", "50 pages atterrissage
          SEO/jour", "200+ mots-clés long-tail/produit FR + 5 langues",
          "FAQ Google PAA", "maillage auto", "Google/Bing/Yandex
          IndexNow", "content gaps versus concurrents". Closing en
          italique "Tout fonctionne en arrière-plan, 24/7, sans
          intervention". Validé visuellement : phrase clés visibles,
          state=Active.

  - task: "AdminGoogleMaster — bloc explainer Architecture Google Ads multi-sites"
    implemented: true
    working: true
    file: "frontend/src/pages/AdminGoogleMaster.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Réponse à la question concept user : ajout d'une carte bleue
          claire qui explique le pattern 1 sous-compte Ads/site rattaché
          au MCC maître. Mentionne que la création auto requiert un
          Developer Token basic/standard (l'explorer ne lit qu'en
          lecture). Carte data-testid="ads-architecture-info".

agent_communication:
  - agent: "main"
    message: |
      Run 2026-04-29 (suite) — 3 livrables :
      1) **Gating cockpit étape 9 débloqué** :
         - `routes/journey_gating.py::_check_content` accepte désormais des
           soft signals : `db.blog_jobs.count >= 1` OU `db.blog_posts.count >= 1`
           OU `automation.content_enabled = true` → `soft_unlocked=true`
           même si la complétion stricte (1 pilier + 3 satellites) n'est pas
           atteinte (les workers async produisent les articles en arrière-plan).
         - `_check_seo` accepte `automation.seo_enabled = true` OU
           `landing_pages.count >= 1` OU `keyword_universe.count >= 5` OU
           `seo_score > 0` → soft unlock.
         - `compute_step_statuses` : `blocked_by_previous = (not previous_completed)
           AND (not soft_unlocked)` — une étape qui a son propre signal d'activité
           n'est jamais bloquée artificiellement par la cascade.
         - **Test concret Altea** : étapes 1-7 complétées, 8 (content) `completed=False soft_unlocked=True` (2 jobs en file + 3 articles publiés), 9 (seo) `completed=False soft_unlocked=True` (SEO auto activé), 10 (qa) `blocked_by_previous=False` ✅. L'utilisateur peut maintenant cliquer sur les étapes 8, 9, 10.

      2) **GMC discovery relancée + sub-account Altea créé** :
         - Avant : `gmc_master.account_id=5771753328 is_mca=False` (warning "compte simple").
         - Après : `gmc_master.account_id=5776814991 is_mca=True total_subaccounts=1` ✅
           (le MCA validé par Google ce matin a été pickup automatiquement
           par `discover_merchant_mca()` via `accounts.authinfo`).
         - `provision_all(altea, force=True)` :
           ✅ GSC : property `https://altea-home.com/` créée.
           ✅ GMC : sub-account `5777050708` créé sous le MCA `5776814991`.
           ❌ Ads : `PERMISSION_DENIED` — Developer Token explorer access (action user).
           ❌ GA4 : 403 sur `dataStreams.create` (j'ai fixé le bug `type: WEB_DATA_STREAM` manquant, l'erreur 400 est passée à 403 — propagation propriété + scope edit, action Google).
         - GA4 + Ads sont 2 erreurs externes Google côté permissions.
         - Bouton "Re-découvrir" déjà présent sur `/admin/google/master-auth`
           (vérifié, ligne 129 de `pages/AdminGoogleMaster.jsx`).

      3) **Fallback HTML SSR `/legal/*`** (débloque altiaro.com prod) :
         - Diagnostic : altiaro.com sert un build React production figé
           (`main.b83d175b.js`) qui ne contient pas les routes /legal/*
           ajoutées récemment. Cloudflare devant + Emergent Native Deploy.
           Backend altiaro.com est aussi sur Emergent Native Deploy gelé.
           Pas de CF_API_TOKEN / VERCEL / NETLIFY dans .env. Pas de
           pipeline CI/CD dans le repo.
         - Solution : `routes/public_legal.py` (NEW) — 5 routes
           `GET /legal/{retours,livraison,cgv,confidentialite,mentions}`
           qui rendent du HTML pur premium (Cormorant Garamond via Google
           Fonts CDN, ivoire #F5F2EB, sidebar 5 sections, bloc société pied,
           CSS inline). Montées DIRECTEMENT sur `app.include_router(...)`
           (pas dans le router /api).
         - Sur preview Kubernetes : ingress route /legal/* au frontend port
           3000 → SPA React continue de servir, ces routes backend ne sont
           jamais appelées (cohabitation).
         - Sur prod altiaro.com (FastAPI sert aussi le frontend statique) :
           les routes FastAPI prennent priorité sur le static fallback,
           garantissant un HTML 200 valide pour Google Merchant.
         - 3 clés ajoutées dans `altiaro_legal.py::PLATFORM_COMPANY` :
           `juridiction`, `dpo_email`, `mediateur_url`.
         - **Validation curl** : 5x backend `/legal/*` → 200 + HTML valide
           avec `<title>Politique de retour · Altiaro</title>` + sidebar +
           SIREN 883 803 967 visible. 5x preview → 200 (SPA React).
         - **Pour activer sur altiaro.com prod** : l'utilisateur doit
           cliquer sur le bouton **Deploy** dans son panel Emergent pour
           pousser le commit courant en production (front + back ensemble).
           Aucun autre moyen automatisable depuis le sandbox.

      Lint Python : `routes/public_legal.py` clean. Erreurs résiduelles
      sur `journey_gating.py` lignes 103-105 préexistantes (E701) hors patches.

## Gating + GMC + Fallback /legal SSR (2026-04-29 suite)

backend:
  - task: "Journey gating soft_unlocked sur content + seo (débloque étape 9)"
    implemented: true
    working: true
    file: "backend/routes/journey_gating.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Bug user : étape 9 ne se débloquait pas après clic "Générer 3
          articles" sur étape 8 (les workers async n'avaient pas encore
          publié 1 pillar + 3 satellites). Fix : ajout d'un champ
          `soft_unlocked` retourné par chaque checker. `_check_content`
          OR sur `blog_jobs.count >= 1`, `blog_posts.count >= 1`, ou
          `automation.content_enabled = true`. `_check_seo` OR sur
          `automation.seo_enabled = true`, `landing_pages.count >= 1`,
          `keyword_universe.count >= 5`, ou `seo_score > 0`.
          `compute_step_statuses` : étape jamais blocked si
          `soft_unlocked` même quand previous_completed=False. Test Altea
          : 10 étapes accessibles, plus aucune `blocked_by_previous`.

  - task: "GMC MCA discovery + provisioning Altea sub-account"
    implemented: true
    working: true
    file: "backend/services/google_master_discovery.py + backend/services/google_provisioning.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Google a validé le compte MCA Altiaro ce matin. Re-run de
          `discover_all(creds)` : `gmc_master.is_mca` passe de `False` à
          `True`, `account_id` migre 5771753328 → 5776814991, warning
          purgé. `provision_all(altea, force=True)` crée le sub-account
          GMC `5777050708` rattaché au MCA. GSC ajouté avec
          property `https://altea-home.com/`. Bug GA4 fix
          (`type: WEB_DATA_STREAM` manquant dans `dataStreams.create`)
          — passe l'erreur 400 → 403 (PERMISSION_DENIED scope, action
          Google côté user). Ads : explorer access (action user côté
          Google Ads developer console).

  - task: "Fallback HTML SSR /legal/* pour altiaro.com prod"
    implemented: true
    working: true
    file: "backend/routes/public_legal.py + backend/altiaro_legal.py + backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          5 routes `/legal/{retours,livraison,cgv,confidentialite,mentions}`
          montées DIRECTEMENT sur `app` (pas /api), rendent du HTML pur
          premium server-side (Cormorant + ivoire + sidebar 5 sections +
          bloc société). Sur preview K8s, l'ingress route /legal/* au
          frontend port 3000 (SPA React continue de servir, cohabitation
          ok). Sur prod altiaro.com (Emergent Native Deploy où FastAPI
          sert aussi le frontend statique), les routes FastAPI prendront
          priorité sur le SPA fallback, garantissant un HTML 200 valide
          pour Google Merchant Center MCA même si le bundle JS reste figé.
          5x curl backend `/legal/*` → 200 + contenu valide. 5x curl
          preview → 200 (SPA). Lint propre. Pour activer sur prod :
          l'utilisateur clique sur Deploy dans Emergent.

agent_communication:
  - agent: "main"
    message: |
      Run 2026-04-29 — 2 livrables :
      1) Refonte UX cockpit `pages/SiteDetail.jsx` :
         - Layout 2 colonnes (sidebar 280px + main).
         - Sidebar : logo site + nom + niche + domaine + pill statut + Score
           global X/100 avec 10 dots + 7/10 étapes validées + Liens rapides.
         - Main : carte "Prochaine action" mise en avant (Cormorant Garamond,
           ambre #B8862E pour eyebrow), banner passif "Référencement Google
           géré automatiquement par la plateforme · {google_email}" si master
           OAuth connecté, CockpitJourney (10 étapes), CTA "Voir storefront"
           + "QA & mise en ligne".
         - **Supprimés** du cockpit : PulseSEOWidget, SEOCoachBell,
           MerchantShoppingPanel, SiteQAPanel (déplacés dans leurs pages
           d'étape respectives).
         - Hook `hooks/useMasterGoogleStatus.js` : lit `/admin/google/master/status`,
           retourne {connected, configured, services, googleEmail}. Sur 403
           (operator), assume connected=true.
         - `components/GSCConnectCard.jsx` patché : si master couvre GSC,
           rend un bandeau passif "Search Console géré par la plateforme"
           sans bouton "Connecter GSC". Cascade automatique à toutes les
           pages qui montent ce composant.
         - Charte ivoire #F5F2EB / cards blanches / accent vert #0F6E4D
           (succès) / ambre #B8862E (action) / bordeaux disponible.
      2) 5 pages légales plateforme Altiaro (débloque MCA Merchant) :
         - `/legal/retours`, `/legal/livraison`, `/legal/cgv`,
           `/legal/confidentialite`, `/legal/mentions` → toutes 200.
         - `components/PlatformLegalLayout.jsx` : header propre, sidebar 5
           sections, contenu blanc + bloc société en pied (SIREN, SIRET,
           APE, adresse, contact, hébergement).
         - `lib/altiaroLegal.js` : miroir frontend de
           `backend/altiaro_legal.py::PLATFORM_COMPANY` (statique).
         - `styles/legal.css` : H2/H3 Cormorant, p/ul/table juriste-pro.
         - 5 pages : Retours (L221-18, 30 jours, médiation), Livraison
           (zones, délais 1-30j L216-2, transporteurs), CGV (16 articles,
           statut TVA art. 293 B), Confidentialité (RGPD complet, table
           finalité/base légale/conservation, droits art. 15-22, CNIL),
           Mentions (éditeur, hébergeur, propriété intellectuelle).
      Validation :
         - ESLint 0 issue sur les 11 fichiers touchés.
         - Curl /legal/* → 5x 200.
         - Screenshot cockpit : "Moteur éditorial"=0, "Connecter GSC"=0,
           PulseSEOWidget=0, NextActionCard=1, ScoreCard=1,
           MasterGoogleStatusBanner=1.
         - Screenshot /legal/retours : Cormorant H1, sidebar 5 items,
           item courant surligné, SIREN affiché, contenu lisible.
      Backend non touché. Aucun mock.

## Refonte UX cockpit + pages légales plateforme (2026-04-29)

frontend:
  - task: "Refonte UX SiteDetail — layout 2 cols, sidebar score, NextAction"
    implemented: true
    working: true
    file: "frontend/src/pages/SiteDetail.jsx + hooks/useMasterGoogleStatus.js + components/GSCConnectCard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Cockpit refondu UX 2 colonnes. Sidebar gauche sticky (logo +
          nom + niche + domaine + status pill + Score global 70/100 avec
          10 dots + Liens rapides : Storefront / Analytics / Réglages /
          Domaine). Colonne principale : carte "Prochaine action" mise
          en avant (Étape 8 Blog & contenu SEO pour Altea), banner
          passif "Référencement Google géré automatiquement par la
          plateforme · groupeseniorcare@gmail.com", parcours 10 étapes,
          CTA storefront + QA. Charte ivoire #F5F2EB + Cormorant.
          Hook useMasterGoogleStatus lit /admin/google/master/status
          (403 = assume connected=true côté operator). GSCConnectCard
          patché en cascade : statut passif quand master couvre GSC.
          Supprimés du cockpit : PulseSEOWidget, SEOCoachBell,
          MerchantShoppingPanel, SiteQAPanel (présents seulement dans
          leurs pages d'étape).

  - task: "5 pages légales plateforme Altiaro (/legal/*)"
    implemented: true
    working: true
    file: "frontend/src/pages/PlatformLegal{Retours,Livraison,Cgv,Confidentialite,Mentions}.jsx + components/PlatformLegalLayout.jsx + lib/altiaroLegal.js + styles/legal.css + App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          5 pages plateforme indépendantes des storefronts clients,
          créées pour débloquer la validation MCA Google Merchant Center.
          Routes /legal/retours, /legal/livraison, /legal/cgv,
          /legal/confidentialite, /legal/mentions toutes 200 (curl
          validation OK). Layout commun : header sobre + sidebar 5
          sections (item courant surligné) + carte blanche article +
          bloc société en pied (SIREN 883 803 967, SIRET, APE 4782Z,
          siège 4 IMP CLOS FLEURI 42320 FARNAY, contact@altiaro.com).
          Données société sourcées de lib/altiaroLegal.js (miroir de
          backend/altiaro_legal.py::PLATFORM_COMPANY). Style juriste-pro
          via styles/legal.css scopé .legal-content. Charte premium
          ivoire #F5F2EB + Cormorant Garamond. Mention "TVA non
          applicable, art. 293 B du CGI" pour franchise en base.
          Conformité RGPD complète (droits art. 15-22, CNIL, table
          finalités/base légale/conservation), médiation L612-1,
          rétractation L221-18, livraison L216-2.

agent_communication:
  - agent: "main"
    message: |
      Phase 2.5 complète livrée (A/B/C/D/E/F) :
      - A : editorial_cards page produit (déjà en place, audit OK 2 cards / produit)
      - B : AiTweakPanel étape 5 Cockpit (bug import `api` default → named corrigé)
      - C : run E2E launch-auto Altea 17 min 42 s, 23/23 checkpoints,
            1 dégradé (testimonials_premium, budget LLM 100.3 % = cap atteint)
      - D : ProductBundle empilé vertical mobile, horizontal desktop (probe JS)
      - E : nouveau <DeliveryPaymentInfo> premium, 2 cols desktop / empilé mobile
      - F : CrossSell + Upsells passent sur <ProductCard variant="default">
            (même composant que la Home). Filtre `hasAiImage` strict pour
            masquer les cards dont l'image est AE brute watermarkée.
      Aucun déploiement tiers requis. Pas de push GitHub.
