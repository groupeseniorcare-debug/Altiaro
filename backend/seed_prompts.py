"""
Seed data for the 50 prompts that compose the e-commerce launch playbook.
Each new site created in Launch OS is auto-seeded with these 50 steps.

The 15 phases (A-O) are now grouped into 4 higher-level BLOCKS :
    1. template   — Template & Boutique (build the storefront engine)
    2. products   — Produits & Sourcing (find what to sell)
    3. seo        — SEO & Marque (organic visibility)
    4. marketing  — Marketing & Scale (paid acquisition + scaling)

Each step exposes `block`, `block_name`, `block_order` so the UI can
collapse / progress-bar per block without touching the underlying content.
"""

PHASES = {
    "A": "Étude marché & recherche produits",
    "B": "Marque, positionnement, voix",
    "C": "Sourcing fournisseurs",
    "D": "Cadre juridique",
    "E": "Shopify backend",
    "F": "Front React headless",
    "G": "SEO technique",
    "H": "AEO / GEO (IA génératives)",
    "I": "Conversion & social proof",
    "J": "Paiement",
    "K": "Service client",
    "L": "Logistique",
    "M": "Acquisition Google Ads",
    "N": "Analytics",
    "O": "Duplication",
}


# ---------- 8 blocs du parcours Concepteur ----------------------- #
BLOCKS = {
    "produits": {
        "order": 1,
        "name": "Produits & Sourcing",
        "emoji": "📦",
        "description": "Identifier les 20 produits gagnants : matrice 30 candidats, rentabilité Ads, concurrentiel, feuille de route catalogue.",
    },
    "marque": {
        "order": 2,
        "name": "Marque & Identité",
        "emoji": "🎨",
        "description": "Nommer la marque, construire l'identité visuelle, définir la voix. Le Concepteur nomme son site ici.",
    },
    "fondations": {
        "order": 3,
        "name": "Fondations boutique",
        "emoji": "🏗️",
        "description": "Cadre légal, backend Shopify, sourcing fournisseurs, import catalogue 20 produits — les fondations avant le front.",
    },
    "front": {
        "order": 4,
        "name": "Construction du front",
        "emoji": "🖥️",
        "description": "Template Altiaro appliqué : homepage, collection, fiche produit, checkout Mollie, pages légales, blog.",
    },
    "seo": {
        "order": 5,
        "name": "SEO & Contenu",
        "emoji": "🔍",
        "description": "Visibilité organique : keyword research, 15 piliers, 30 satellites, schemas JSON-LD, netlinking, AEO.",
    },
    "conversion": {
        "order": 6,
        "name": "Conversion & CRM",
        "emoji": "🎯",
        "description": "CRO, social proof, Klaviyo 7 flows, paiement optimisé, chatbot, helpdesk, téléphonie.",
    },
    "operations": {
        "order": 7,
        "name": "Opérations & SAV",
        "emoji": "🚚",
        "description": "Logistique drop, tracking client, portail retours — ce qui fait tourner une fois les commandes arrivent.",
    },
    "scale": {
        "order": 8,
        "name": "Acquisition & Scale",
        "emoji": "🚀",
        "description": "Google Ads 30€/j, landing pages, GA4+CAPI, monitoring SEO, duplication multi-niches, SOPs.",
    },
}

# Which block does each phase belong to ?
PHASE_TO_BLOCK = {
    "A": "produits",     # Étude marché & produits
    "B": "marque",       # Marque, positionnement, voix
    "C": "fondations",   # Sourcing fournisseurs
    "D": "fondations",   # Cadre juridique
    "E": "fondations",   # Shopify backend (inclut import catalogue)
    "F": "front",        # Front React headless + pages
    "G": "seo",          # SEO technique
    "H": "seo",          # AEO/GEO
    "I": "conversion",   # CRO + social proof + Klaviyo
    "J": "conversion",   # Paiement
    "K": "conversion",   # Service client (chatbot, helpdesk, tel)
    "L": "operations",   # Logistique, tracking, retours
    "M": "scale",        # Google Ads
    "N": "scale",        # Analytics
    "O": "scale",        # Duplication, SOPs
}


PROMPTS = [
    # PHASE A — Étude marché
    {
        "number": 1,
        "phase": "A",
        "title": "Matrice produits quantifiée (15 candidats)",
        "summary": "Produire une matrice de 15 produits candidats avec volumes de recherche FR, CPC Google Ads, prix, marges, score GO — assez pour identifier le TOP 5.",
        "prompt": """Tu es product researcher e-commerce drop-shipping FR (10 ans d'exp senior/silver economy).

Je lance une boutique Shopify FR/EU sur la niche : **[NICHE]**.
Contraintes : budget Google Ads 30€/jour · CPC cible < 1€ OU marge absolue > 400€/vente.

**Critères d'entrée obligatoires** :
- Pas de dispositif médical MDR (classe I accepté si auto-déclaration OK)
- Dispo dropship (Alibaba/AliExpress/CJ/Zendrop/Spocket/BigBuy)
- Poids < 20 kg · conforme import EU · marge brute ≥ 70%

**Livre une matrice de 15 produits candidats** dans ce format tableau markdown **STRICT** (8 colonnes, concis) :

| # | Produit (nom FR commercial) | KW principal FR | Volume/mois FR | CPC (€) | Prix achat Chine (€) | Prix vente conseillé (€) | Marge % | Score GO /10 |

Après le tableau, ajoute un bloc court :
- **TOP 3 retenus** avec 2 lignes de justification chacun (angle marketing + pourquoi ça rentre dans budget 30€/j)
- **1 warning** : le produit le plus risqué de la liste et pourquoi.

**Sois synthétique** — la matrice doit tenir en 1 écran. Pas de blabla, pas de variations. Cible : 1200-1800 mots MAX.""",
    },
    {
        "number": 2,
        "phase": "A",
        "title": "Rentabilité & faisabilité Google Ads par produit",
        "summary": "Simuler la rentabilité Google Ads des 15 premiers produits pour un budget 30€/j global : CPA, ROAS, break-even, viabilité.",
        "prompt": """À partir de la matrice produits (prompt 1), calcule pour le TOP 15 la simulation de rentabilité Google Ads à 30€/j budget total:

Pour chaque produit:
- Clics attendus/jour = 30 / CPC
- Conversion % attendue (senior mid-ticket 1,2-2,5% / high-ticket 0,5-1%)
- CPA estimé = CPC / CR
- CA/jour = clics × CR × PV
- Marge/jour = CA × marge% - 30 (coût pub)
- ROAS attendu = CA / Pub
- Break-even analysis: jours avant rentabilité ?
- Risque: budget suffisant pour 50 conv/mois (seuil optim PMax) ?

Classement final:
1. 🚀 Acquisition-driver (CA rapide, validation funnel)
2. 💰 Cash-cow (SEO/retargeting, pas Google Ads direct)
3. 🏆 Hero-ticket (1 vente = 15j pub amortis)
4. ❌ Non-viables à 30€/j

Recommandation: 5 produits à lancer jour 1 pour 1ère vente le plus vite possible.""",
    },
    {
        "number": 3,
        "phase": "A",
        "title": "Analyse concurrentielle chirurgicale",
        "summary": "Benchmark SERP + Google Shopping + Facebook Ads Library + Amazon pour chacun des 5 produits prioritaires avec gaps exploitables.",
        "prompt": """Pour chacun des 5 produits prioritaires (prompt 2), réalise une analyse concurrentielle:

1. SERP Google FR top 10: URL, type, DR estimé, meta title/H1, prix, réassurance, schema, trust signals, angle diff
2. Google Shopping FR: top 10 annonceurs, fourchette prix, note marchand, images
3. Facebook Ads Library: créas en cours, angle, durée
4. Amazon FR: top 5 BSR, avis, prix, bullets clés
5. GAPS: 10 angles où battre la concurrence sans gros budget

Livrable: competitive_analysis_[produit].md × 5""",
    },
    {
        "number": 4,
        "phase": "A",
        "title": "Feuille de route catalogue 90 jours",
        "summary": "Roadmap catalogue sur 90 jours: Phase 1 MVP (5+10), Phase 2 expansion (+15+2 hero), Phase 3 full-catalog (+30) avec priorité, fournisseur cible, canal acquisition et budget.",
        "prompt": """Synthèse finale de l'étude marché. Produis la FEUILLE DE ROUTE CATALOGUE 90 jours:

Phase 1 — MVP (J1-15): 5 produits prioritaires + 10 accessoires cross-sell, 2-3 collections SEO
Phase 2 — Expansion (J15-45): +15 produits mid-ticket, 2 hero high-ticket, création cocons SEO
Phase 3 — Full-catalog (J45-90): +30 produits, 2e sous-niche, test produits marque privée

Pour chaque produit: priorité ranking, fournisseur cible (nom + plateforme), canal acquisition principal, budget pub estimé, objectif CA mensuel post-J90.

Livrable: catalog_roadmap.md + forecast_90j.xlsx""",
    },
    # PHASE B — Marque
    {
        "number": 5,
        "phase": "B",
        "title": "Génération nom de marque + domaine + INPI",
        "summary": "15 noms de marque en 3 familles (évocateur FR, latin/italien, holding évolutif) avec disponibilité domaine, check INPI, slogans, TOP 3 recommandé.",
        "prompt": """Je lance une boutique e-commerce premium niche [NICHE], cible FR puis UE, ambition multi-niches futur.

Propose 15 noms de marque classés en 3 familles:
A. Noms évocateurs français poétiques (ex: Séréna, Aurélie Maison)
B. Noms latins/italiens chaleureux (ex: Dolcimo, Vivenda)
C. Noms holding évolutifs (ex: Groupe Luméa → Luméa Confort)

Pour chaque: prononciation, étymologie, dispo .fr/.com/.eu, check INPI classe 10+35, handles socials dispo, slogan 6 mots max, 3 adjectifs d'ambiance.

Finalise TOP 3 avec justification + commandes à lancer.""",
    },
    {
        "number": 6,
        "phase": "B",
        "title": "Identité visuelle complète (brand book)",
        "summary": "Brand book complet: logo (3 concepts), typographies non-génériques, palette couleurs, spacing, shadows, direction photo, iconographie, patterns, variables CSS prêtes, prompts Midjourney.",
        "prompt": """La marque s'appelle [NOM]. Brand book complet livrable markdown + CSS variables:

1. LOGO — 3 concepts textuels précis
2. TYPOGRAPHIE — display non-générique (Fraunces/Canela/Cormorant/DM Serif, PAS Inter/Poppins) + body lisible 18px+
3. PALETTE couleurs hex+usage, éviter bleu médical/AI-slop purple
4. SYSTÈME espacement 8pt grid
5. RADIUS, SHADOWS, STROKES
6. DIRECTIONS PHOTO (10 photos types)
7. ICONOGRAPHIE Lucide/Phosphor
8. PATTERNS & TEXTURES
9. VARIABLES CSS complètes
10. 3 PROMPTS MIDJOURNEY

Livrable: brand_book.md + design_tokens.css""",
    },
    {
        "number": 7,
        "phase": "B",
        "title": "Voix de marque + manifesto + 20 accroches",
        "summary": "Manifesto 120 mots, voix de marque (vouvoiement, 10 règles on dit/pas, 15 mots signature), 20 accroches testables, storytelling fondateur 450 mots.",
        "prompt": """Tu es Head of Brand Content dans une agence de naming/branding top 10 Paris (clients : Lancôme, Petit Bateau, Nature & Découvertes).

Pour la marque [NOM] positionnée sur [NICHE], niche Silver Economy, cible senior 60-80 ans + leurs aidants (enfants 45-65 ans), définis :

1. **MANIFESTO** 120 mots — émotionnel, humain, articulé autour de : dignité, longévité, autonomie, confort. À publier en page About. Ton qui fait pleurer les aidants.

2. **VOIX DE MARQUE** (2 pages .md) :
   - Principes : vouvoiement systématique, chaleur sans infantilisation
   - 10 règles "on dit / on ne dit pas" (ex: on dit "solution", pas "produit" ; on dit "vous accompagner", pas "vous aider")
   - 15 mots-signature à utiliser en priorité (confort, sérénité, ingéniosité...)
   - 10 mots à BANNIR (vieux, handicapé, invalide, sénile...)
   - Exemples avant/après : email bienvenue (bad vs good) · SAV (bad vs good) · fiche produit (bad vs good)

3. **20 ACCROCHES** testables en Ads (20-35 caractères), structurées par angle :
   - 5 bénéfice (confort/autonomie)
   - 5 preuve (garantie 2 ans, livraison France, 10000 clients)
   - 5 urgence douce (fête des mères, hiver, retraite)
   - 5 émotion (souvenir, famille, tendresse)

4. **STORYTELLING FONDATEUR** 450 mots authentique — origin story déclencheur (grand-mère chez soi, accident, aidance). Narré à la 1re personne.

5. **MISSION STATEMENT** en 1 phrase qui tient sur une tasse.

6. **TAGLINE** 3-6 mots pour le header (différent du mission statement).

Livrables : brand_voice.md + manifesto.md + about_page_copy.md + taglines.csv (20 lignes)""",
    },
    # PHASE C — Sourcing
    {
        "number": 8,
        "phase": "C",
        "title": "Dossier sourcing 50 fournisseurs",
        "summary": "50 fournisseurs répartis en 4 catégories : plateformes dropship EU, usines Alibaba, grossistes FR/EU, agents sourcing privés.",
        "prompt": """Pour les 20 produits validés (prompts 1-4), je cherche mix fournisseurs DROPSHIP 2026: délai < 10j FR, entrepôts EU priorité.

Dossier 50 fournisseurs:
A. Plateformes dropship EU (15): CJ, Spocket, Zendrop, BigBuy, Matterhorn, VidaXL B2B, Syncee, Griffati, Eprolo, BrandsDistribution...
B. Alibaba/1688 pour OEM marque privée (15 usines): Gold Supplier + Verified + Trade Assurance, certifications CE/RoHS/REACH
C. Grossistes FR/EU compte pro (10): Drive Medical, Herdegen, Hermell, Rupiani, Sofamed Pro...
D. Agents sourcing privés (10): HyperSKU, NicheDropshipping, EcomOps...

Pour chaque: nom, ville, URL, MOQ, certifications, produits phares, forces, conditions.

Livrable: suppliers_directory.md + suppliers_comparison.csv""",
    },
    {
        "number": 9,
        "phase": "C",
        "title": "Protocole qualification fournisseur",
        "summary": "Grille 3 étapes : scoring on-desk 15 critères, test commande échantillon avec unboxing, test SAV. Scoring /300, seuil GO 220.",
        "prompt": """Protocole qualification fournisseur en 3 étapes:

Étape 1 — Scoring on desk (15 critères, grille /100): ancienneté, certifications, réponse <24h, anglais, OEM possible, port transparent, délais réalistes, avis, documentation, politique retour...

Étape 2 — Test commande échantillon: 1 unité payée livraison normale, timer délai réel, unboxing caméra, checklist emballage/notice FR/sticker CE/fiche EN+FR

Étape 3 — Test SAV: provoquer un retour, mesurer délai réponse/prise en charge/refund

Scoring final /300. Seuil GO: 220+.

Livrable: supplier_qualification.md + scorecard.xlsx""",
    },
    {
        "number": 10,
        "phase": "C",
        "title": "Templates négociation multilingues FR/EN/CN",
        "summary": "12 templates emails fournisseurs : 1er contact, FOB/EXW/DDP, certifs, entrepôt EU, dropship sans logo, OEM, facture SIRET, paliers volume, 30/70, refus, litige, pause.",
        "prompt": """Génère 12 templates emails/WhatsApp en 3 versions (🇫🇷 FR / 🇬🇧 EN / 🇨🇳 phrases-clés CN+pinyin WeChat):

1. Premier contact catalogue
2. Demande prix FOB + EXW + DDP
3. Demande certifications CE + RoHS + REACH PDF
4. Entrepôt EU + dropship délais FR
5. Dropship sans logo vendeur sur colis
6. OEM marque privée (logo produit + packaging)
7. Facture avec SIRET / TVA intracom
8. Négo prix à 50/200/500 unités
9. Paiement 30/70 balance avant shipping
10. Refus fournisseur médiocre
11. Gestion défaut qualité (preuve + remplacement)
12. Pause partenariat saisonnier

Livrable: supplier_templates.md""",
    },
    {
        "number": 11,
        "phase": "C",
        "title": "Transition dropship → marque privée OEM",
        "summary": "Plan de passage en marque privée : 4 niveaux de personnalisation, MOQ, timeline, docs import, stockage 3PL, ROI break-even.",
        "prompt": """Planifie transition dropship générique → marque privée OEM. Seuil déclenchement ~50-100 unités/mois.

Pour chaque produit phare:
1. Niveau personnalisation (étiquette blanche 0,20€, logo brodé 0,50€, packaging custom 1-2€, co-design +10-15%)
2. MOQ typique + risque stock immobilisé
3. Timeline production + transport 30-60j
4. Docs: bon de commande, PI, BL, packing list, certif origine, DDP vs FOB
5. Stockage 3PL EU avant dropship EU
6. ROI break-even quantité/mois rentable

Livrable: oem_transition_playbook.md + breakeven_calculator.xlsx""",
    },
    # PHASE D — Juridique
    {
        "number": 12,
        "phase": "D",
        "title": "Cadre légal drop-shipping FR 2026",
        "summary": "Cadre minimal : structure (micro/EURL/SASU), TVA + OSS + IOSS, obligations drop (Loi Lemaire, responsabilité, info pré-contractuelle), éco-contributions DEEE/Citeo, marquage CE, assurances RC Pro.",
        "prompt": """Drop-shipping FR légal, cible particuliers FR+UE, produits grand public (pas DM, pas alimentaire, pas cosmétique).

Cadre minimal obligatoire 2026:
1. STRUCTURE — comparatif micro / EURL / SASU (seuils TVA, cotisations, crédibilité)
2. TVA — franchise base jusqu'à seuils, OSS UE >10k€, IOSS obligatoire import <150€ depuis Chine
3. Obligations drop: Loi Lemaire, responsabilité vendeur art L221-15, info pré-contractuelle délais, transparence TVA douane
4. Éco-contributions: DEEE Ecologic/Ecosystem, Citeo, Eco-Mobilier
5. Marquage CE responsabilité importateur + notice FR obligatoire
6. Assurances RC Pro + RC Produit (Hiscox, AXA Pro, Simplis)

Livrable: legal_framework_dropship.md""",
    },
    {
        "number": 13,
        "phase": "D",
        "title": "Documents légaux clé en main",
        "summary": "6 documents complets 2026 : CGV B2C (25 articles), Mentions légales, Politique RGPD, Cookies, Rétractation + formulaire, CGU programmes.",
        "prompt": """Génère 6 documents légaux complets pour [NOM_MARQUE] (SIRET placeholder, domaine [DOMAINE]) clauses 2026 FR:

1. CGV B2C 25 articles min (identité, prix TTC/TVA, commande, paiement CB/PayPal/Alma, livraison drop transparente, IOSS, rétractation 14j + formulaire annexe I, garantie légale 2 ans, SAV, RGPD, médiation CE2C, droit applicable)
2. Mentions légales (hébergeur, éditeur, directeur pub, RCS, TVA, DEEE, contact)
3. Politique RGPD (6 finalités, durée, droits, DPO, transferts hors UE Shopify/Google US)
4. Politique cookies bannière CNIL conforme
5. Politique rétractation + formulaire-type
6. CGU newsletter/fidélité

Livrable: 6 fichiers .md + version HTML Shopify pages""",
    },
    # PHASE E — Shopify Backend
    {
        "number": 14,
        "phase": "E",
        "title": "Configuration Shopify complète (backend-only)",
        "summary": "Procédure pas-à-pas : paramètres boutique, taxes OSS/IOSS, zones livraison, paiements, Custom App tokens API Admin + Storefront, webhooks.",
        "prompt": """J'ai compte Shopify Basic [URL_ADMIN]. Usage headless: Shopify backend (produits/commandes/paiement/checkout), front React via Storefront API.

Procédure pas-à-pas:
1. Paramètres: EUR, timezone Paris, kg, adresse, SIRET, coller CGV/mentions en policies
2. Taxes: franchise OU TVA 20%, registration OSS UE >10k€, IOSS si import direct Chine
3. Zones livraison: FR métropole Colissimo, DOM-TOM, UE 6 pays, tarifs par poids
4. Paiements: Shopify Payments (CB/Apple/Google Pay 3DS), PayPal, Alma 3x/4x, virement B2B
5. Localisation checkout: FR+EN, téléphone obligatoire
6. Custom App privée: scopes Admin API (products/orders/inventory/customers), Storefront API (unauthenticated_read_*), tokens dans .env
7. Webhooks vers /api/webhooks/shopify: orders/create/paid/fulfilled/cancelled, HMAC verification
8. Emails transactionnels custom template (logo, couleurs, signature)

Livrable: shopify_setup_checklist.md + routes/shopify_webhooks.py""",
    },
    {
        "number": 15,
        "phase": "E",
        "title": "Import catalogue CSV haute qualité (20 produits)",
        "summary": "CSV Shopify complet : 20 produits avec Handle SEO, Title, Body HTML 700+ mots structuré, variantes, prix, tags, meta SEO, image alts.",
        "prompt": """Génère CSV import Shopify 20 produits prioritaires (Phase 1+2 roadmap prompt 4). Format Shopify officiel 100%: Handle, Title, Body HTML, Vendor, Product Category, Type, Tags, Published, Option1 Name/Value, Variant SKU, Variant Price, Compare At Price, Variant Inventory Qty, Image Src, Image Alt, SEO Title, SEO Description, Variant Barcode.

Pour chaque produit:
- Handle SEO kebab-case
- Title <=65 car. KW+bénéfice
- Body HTML 700+ mots: ouverture émotionnelle 100 mots + 5 bénéfices bullets + Pour qui? + tableau specs + Contenu colis + Engagement marque + FAQ 5 Q/R + témoignages + conformité CE
- Variantes SKU structurés
- Prix + comparatif barré (ancrage psycho)
- Meta title 60 car. + description 155 car.
- Tags 15+
- Image Alt riche

Livrable: shopify_products_import.csv + preview_product_exemple.html""",
    },
    {
        "number": 16,
        "phase": "E",
        "title": "Stack apps Shopify optimale",
        "summary": "Installation et config apps essentielles : DSers, Judge.me, Alma, Klaviyo, Shopify Flow, + phase scale Loox, ReConvert, Gorgias, Langify, Google/Meta channels.",
        "prompt": """Installation et config apps Shopify:

Essentielles (gratuit/low cost):
1. DSers — sync AliExpress
2. Judge.me — avis produits + photos + schema SEO
3. Alma — 3x/4x sans frais FR (conv +30%)
4. Klaviyo — email + SMS flows
5. Shopify Flow — automations natives

Phase scale:
6. Loox — avis photos
7. ReConvert — upsell post-achat
8. Zipify OCU — one-click-upsell
9. Gorgias — helpdesk (>20 tickets/j)
10. Langify — traductions DE/ES/IT

Shopping feeds:
11. Google & YouTube Channel — Merchant Center
12. Meta Channel — catalog FB/IG Shop

Pour chaque: plan recommandé, coût, installation, paramétrage exact, intégration front React, KPI.

Livrable: shopify_apps_stack.md""",
    },
    # PHASE F — Front React (Prompts 17-24 condensed)
    {
        "number": 17,
        "phase": "F",
        "title": "Scaffold React headless + Shopify Storefront API",
        "summary": "App React 18 + Vite + TypeScript + Tailwind + shadcn + Framer Motion connectée à Shopify Storefront GraphQL, architecture complète, accessibilité AAA, perfs Lighthouse 95+, SEO-ready.",
        "prompt": """Crée app frontend React 18 headless connectée Shopify.

Stack: Vite + React 18 + TS strict + Tailwind + shadcn/ui + Framer Motion + Lucide + graphql-request + @shopify/hydrogen-react types + react-hook-form + zod + Zustand + react-helmet-async

Architecture /app/frontend/src/:
/pages (Home, Collection/[handle], Product/[handle], Blog, Blog/[slug], About, Contact, FAQ, Search, Legal/*, Admin/Dashboard)
/components: /layout, /ui (shadcn), /product, /blocks, /chat, /a11y
/lib: shopify.ts, analytics.ts, schemas.ts, seo.ts, i18n.ts
/hooks, /styles

Exigences: Accessibilité AAA (18px base, 56px buttons, contrastes WCAG AAA, focus rings, aria-labels), perfs Lighthouse 95+ mobile, SEO SSG/ISR + sitemap + schemas + hreflang + canonical, tracking client + server-side, PAS dark mode, PAS AI-slop purple.

Livrable: scaffold complet + README + .env.example + package.json""",
    },
    {
        "number": 18,
        "phase": "F",
        "title": "Homepage conversion-first premium",
        "summary": "Homepage 13 sections (announcement, header sticky, hero vidéo, personas, produits phares, social proof, engagements, comparatif, blog, fondateur, FAQ, newsletter+lead magnet, footer). Objectif 5% add-to-cart en 90s.",
        "prompt": """Code HOMEPAGE [NOM_MARQUE]. Objectif: 5%+ add-to-cart en 90s.

13 sections (composant par bloc avec data-testid unique):
1. AnnouncementBar livraison + tél
2. Header sticky (logo, nav 5 items, search, cart, CTA rappel, a11y panel)
3. Hero vidéo MP4 loop, H1 émotionnel, 2 CTA, bandeau 4 réassurance
4. Pour qui? 3 cards persona
5. Produits phares 6 cards avec badges
6. Social proof 4 témoignages vidéo + Trustpilot + logos presse
7. Nos engagements 4 piliers illustrés
8. Comparatif MARQUE vs grande surface
9. Blog highlights 3 articles
10. Fondateur photo + 100 mots + signature
11. FAQ accordéon 6 Q
12. Newsletter + lead magnet PDF 20 pages
13. Footer riche 5 cols

Animations Framer Motion subtiles. Icônes Lucide 1.5. PAS emoji. Photos Unsplash réalistes (URLs fournies).""",
    },
    {
        "number": 19,
        "phase": "F",
        "title": "Page collection SEO + UX",
        "summary": "Page collection avec H1 optimisé, intro SEO 250 mots visible, filtres fonctionnels, grille produits lazy, bloc conseil SEO 600 mots, FAQ schema, breadcrumb, pagination canonique.",
        "prompt": """Code /collections/[handle] SEO+conversion.

Header: breadcrumb+schema, H1 unique KW primaire, intro 250 mots 100% visible (pas caché), bandeau USP 3 items.

Sidebar filtres (drawer mobile): Prix slider, options dynamiques, dispo, note minimum, tri (pertinence/prix/nouv/top/note).

Grille 3 cols: ProductCard (image hover vidéo, badge, titre 2 lignes, note+count, prix+comparatif, mensualité Alma, CTA Voir). Lazy + pagination cliquable avec rel prev/next.

Bloc milieu grille: Besoin conseil? photo+form rappel.

Section conseil SEO bas 600 mots unique avec H2 "Comment choisir?", 4-5 paragraphes experts, liens internes blog.

FAQ SEO 6 Q/R schema FAQPage.

Cross-collection: Vous pourriez aimer (3 autres).

SEO: meta dynamiques, schema CollectionPage+ItemList+BreadcrumbList, canonical, hreflang.""",
    },
    {
        "number": 20,
        "phase": "F",
        "title": "Fiche produit haute conversion (page critique)",
        "summary": "Page produit exhaustive : galerie 6-8 images + 2 vidéos, BuyBox complète (prix, Alma, stock, CTA, réassurance, conseiller, simulateur livraison), 22 sections sous le fold, schema Product complet.",
        "prompt": """Code /products/[handle] — page la + importante (5-8% conv visé).

Layout 2 colonnes desktop:

Gauche Galerie: 6-8 images HD + 2 vidéos, miniatures, zoom hover, full-screen modal, swipe mobile, badge démo vidéo.

Droite BuyBox sticky:
1. Breadcrumb + H1
2. Judge.me étoiles + count
3. Prix + comparatif barré + % économie + mensualité Alma calculée dynamique
4. Variantes (swatches couleur 48px, tailles)
5. Stock temps réel
6. Bouton AJOUTER AU PANIER 64px AAA
7. Logos paiement (CB, PayPal, Alma, Apple Pay)
8. Bloc réassurance 4 lignes icônes (Livraison offerte, Essai 30j, Garantie 2 ans, Conseil 7j/7)
9. Conseiller personnalisé photo+tél+chat
10. Simulateur livraison code postal → date exacte

Sous le fold: description SEO 800 mots, vidéo immersion 90s, comparatif 2 produits, specs tableau, contenu colis, notice PDF, Q&R, avis Judge.me, FAQ 10+ schema, cross-sell "souvent acheté ensemble", social proof +X familles, CTA sticky mobile.

Schema Product complet (GTIN, MPN, brand, offers, shipping, returns, aggregateRating, review) + FAQPage + BreadcrumbList.

Micro: slide-in cart + exit-intent + scroll notif VRAIE.""",
    },
    {
        "number": 21,
        "phase": "F",
        "title": "Cart drawer + checkout redirect Shopify",
        "summary": "Drawer panier : liste produits, upsell, barre progressive livraison gratuite, widget Alma, code promo, redirect checkout Shopify via Storefront API mutation.",
        "prompt": """Construis CartDrawer slide-in right:
- Liste produits (image, titre, options, qty +/-, prix, remove)
- Upsell 1 produit recommandé (top collection)
- Barre progressive livraison gratuite
- Widget Alma 3x calculé
- Sous-total + total (livraison estimée)
- Code promo (validation Storefront API)
- Bouton Passer commande → checkout.shopify.com via checkoutCreate mutation line items + email
- Footer sécurité SSL + 3DS

Persistance Zustand + localStorage + sync Storefront API multi-devices.

Tracking add_to_cart/remove_from_cart/begin_checkout (GA4+Meta+server-side).

Livrable: CartDrawer.tsx + hooks/useCart.ts + lib/shopify/cart.ts""",
    },
    {
        "number": 22,
        "phase": "F",
        "title": "Blog + article template haute qualité SEO",
        "summary": "Module blog listing + article long format : TOC sticky, 2500+ mots, images/vidéos, callouts, interlinking, schema Article+Author+Publisher, auteur bio E-E-A-T.",
        "prompt": """Module BLOG:

/blog listing: grille 3 cols + catégories filter, recherche full-text, sidebar articles+newsletter+CTA produits, pagination.

/blog/[slug]: breadcrumb+schema, H1, meta auteur photo+bio+diplôme + date + temps lecture, TOC sticky sidebar desktop, contenu 2500+ mots (H2/H3, paragraphes courts, images landscape+portrait avec alt, vidéos YouTube lite, callouts info/warning/tip, listes+tableaux, citations expert, FAQ milieu, interlinking 4-6 produits + 4-6 articles + 2-3 liens externes autorité, CTA natif milieu+fin), schema Article+Author+Publisher, bloc auteur bas, 3 articles connexes rel prev/next, partage Web Share API, newsletter inline.

Source: Shopify Blog API (simple) OU MDX+Contentlayer (SEO contrôle ultime).

Livrable: /app/frontend/src/pages/Blog* + hooks/useBlog.ts""",
    },
    {
        "number": 23,
        "phase": "F",
        "title": "Pages statiques (About, Contact, FAQ, Legal, A11y)",
        "summary": "About 1000 mots storytelling, Contact form + tél + chat, FAQ 50 questions schema, pages légales du prompt 13, page accessibilité avec toggle panel (police, contraste, curseur).",
        "prompt": """Code pages:

1. /a-propos — 1000 mots storytelling, histoire fondateur, équipe photos+rôles, valeurs, engagements mesurables, vidéo manifesto, chiffres clés, presse
2. /contact — formulaire (nom, email, tél, motif, message), alternatives (tél gros + chat + WhatsApp), horaires, carte, FAQ ancre, promesse réponse <2h
3. /faq — 50 questions par catégories (Livraison/Paiement/Produit/Retour/SAV/Compte/Fidélité), recherche, schema FAQPage 50+ mainEntity
4. Pages légales (6 du prompt 13) avec TOC, ancres
5. /accessibilite — déclaration RGAA + toggle panel (taille police, contraste élevé, curseur XXL, interligne, no animations) persistant cookie

Bouton flottant bas-droit Accessibilité depuis toutes pages.""",
    },
    {
        "number": 24,
        "phase": "F",
        "title": "Recherche interne + suggestions",
        "summary": "Composant Search avec modal Cmd+K, suggestions instantanées (produits, collections, articles, FAQ), historique, populaires, Shopify predictive search API.",
        "prompt": """Tu es Senior Frontend Engineer (ex-Shopify Plus), 10 ans d'exp sur des e-commerces FR > 5M€/an.

Implémente la recherche interne complète du site Altiaro.

**Composant Search** :
- Input dans le header (icône loupe à droite) + raccourci **Cmd+K / Ctrl+K** (écoute globale)
- Clic ou raccourci → modal plein écran avec overlay dark semi-transparent
- Input auto-focus + placeholder contextuel ("Fauteuil releveur, coussin anti-escarres...")
- **Debounce 300ms** avant d'envoyer la requête (évite le spam)

**Résultats en 4 sections** (chaque item : image 40x40 + titre + meta preview + prix si produit) :
1. **Produits** (top 5 match) — image + nom + prix + disponibilité stock
2. **Collections** (top 3 match) — image + nombre de produits
3. **Articles blog** (top 3 match) — image + temps de lecture
4. **FAQ** (top 3 match) — question + début de réponse tronqué

**États vides** :
- Input vide → "Recherches populaires" (5 termes hardcodés + top 5 derniers cherchés de l'user)
- Aucun résultat → message empathique + suggestion de catégories + CTA contact
- Historique localStorage limité à 10 items, clearable

**Sources** :
- Shopify **predictive search API** en priorité (rapide, natif)
- Algolia DocSearch en fallback si catalogue > 200 produits
- Tracking events (Mixpanel/GA4) : `search_performed`, `search_result_clicked`, `search_empty`
- **Les recherches vides sont GOLD** pour détecter les gaps catalogue → export CSV mensuel

**Accessibilité** :
- Navigation clavier (↑↓ pour naviguer, Enter pour ouvrir, Esc pour fermer)
- Lecteur d'écran : aria-live="polite" pour annoncer les résultats
- Focus trap dans la modal (Radix UI Dialog recommandé)

**Performance** :
- Requête debounced + abort controller (annule si user tape vite)
- Skeletons loading animés (pas de spinner brutal)
- Cache des 20 dernières requêtes (in-memory, TTL 5min)

Livrable : `/components/SearchModal.tsx` + `/hooks/useSearch.ts` + `/lib/searchTracking.ts` + tests Playwright (ouvre Cmd+K, tape "fauteuil", clique 1er résultat)""",
    },
    # PHASE G — SEO (Prompts 25-29)
    {
        "number": 25,
        "phase": "G",
        "title": "Keyword research avancé + clusters thématiques",
        "summary": "Research 400+ KW avec méthodologie (seed, expansion, sources), clustering 12 clusters, topical authority map, 20 KW prioritaires.",
        "prompt": """AUDIT + KEYWORD RESEARCH FR pour [NICHE], objectif top 3 Google sur 20 KW prioritaires en 6 mois.

Méthodologie:
1. Seed keywords 10 termes racine
2. Expansion: modificateurs achat (meilleur, prix, avis, 2026), techniques (électrique, pliable), questions (comment, quel, pourquoi)
3. Sources: Keyword Planner, Ahrefs, SemRush, Ubersuggest, Also Asked, AnswerThePublic, Google Suggest, People Also Ask, YouTube Suggest, Amazon Suggest, Reddit, Quora
4. Scraping SERP top 10 sur chaque KW → topical authority gap

Livrables:
A. Master KW sheet CSV 400+ mots (KW, Volume FR/mois, CPC, KD%, Intent, Cluster, Pilier, Priorité, Page cible, Status)
B. 12 clusters thématiques (1 pilier 2500+ mots + 6-12 satellites longue-traîne + 1-2 landing commerciales + 3-6 FAQ)
C. Topical authority map .mermaid
D. 20 KW prioritaires Phase 1 (volume>=500, KD<=35, intent commercial/transactional, produit catalogue)

Livrables: keywords_master.csv + clusters_map.md + topical_graph.mermaid""",
    },
    {
        "number": 26,
        "phase": "G",
        "title": "15 articles piliers (3000 mots chacun, niveau expert)",
        "summary": "15 articles piliers skyscraper 3000 mots avec structure stricte (intro hook, TOC, H2 structurés, tableaux comparatifs, FAQ schema, E-E-A-T), interlinking, entités nommées, statistiques datées.",
        "prompt": """Rédige 15 premiers ARTICLES PILIERS blog qualité skyscraper (dépasser top 10 Google actuel en profondeur + fraîcheur 2026).

Pour chaque:
- Titre SEO 60 car. (inclure 2026 si relevant = CTR SERP)
- Meta description 155 car. value-packed + CTA
- URL slug optimisé
- Structure: intro hook (pain+promesse+TOC), 7-10 H2 logiques, H3 sous-découpe, paragraphes courts, 1-2 visuels décrits, 2+ tableaux comparatifs, FAQ 5+ schema FAQPage, conclusion actionnable + récap + CTA, bloc auteur
- Entités nommées: marques concurrentes, institutions (CNSA, AMELI, HAS), pathologies tangentielles, lois
- Mots-clés LSI 20+ naturels
- Data primary: stats INSEE/Silver Eco sourcées
- Interlinking: 5-7 vers satellites même cluster + 2-3 vers produits + 2-3 externes autorité .gouv.fr + 1 vers autre cluster
- E-E-A-T: signé ergothérapeute DE 10 ans exp, date pub+MAJ, bloc méthodologie, schema Author+Publisher

Livrable: 15 fichiers .md prêts import Shopify Blog""",
    },
    {
        "number": 27,
        "phase": "G",
        "title": "30 articles satellites + maillage interne intelligent",
        "summary": "30 articles satellites 1000-1500 mots longue-traîne, principe intent match, maillage cocon vers piliers et satellites voisins.",
        "prompt": """Tu es Head of SEO Content (ex-Hubspot, ex-Semrush agency lead). Tu rédiges pour des queries longue-traîne commerciales avec conversion > 3%.

Rédige 30 articles satellites (**1200-1500 mots chacun**), maillés en cocon sémantique autour des 15 piliers du prompt #26. Chaque satellite cible UNE intention ultra-précise (ex : "quel fauteuil releveur pour personne 90 kg avec arthrose").

**Structure par article** (respectée à la lettre) :
1. **Intro 80-120 mots** — contextualise le problème, empathie, promesse de réponse
2. **Réponse directe 150 mots** (pour AEO / featured snippet) — résume la solution en 3 phrases + 1 tableau comparatif 3 colonnes
3. **3-5 sections H2** ciblées sur les sous-intentions du mot-clé principal (pas de remplissage)
4. **Section expert** (H2) — citation d'un gériatre/ergothérapeute (nom fictif plausible + credentials)
5. **FAQ finale 4-6 questions** (H3 chacune, réponses 50-80 mots)
6. **Encadré CTA produit** en milieu d'article + en fin (lien vers fiche produit Altiaro)

**Maillage obligatoire par article** :
- **1 lien vers le pilier du cluster** (ancre variée, contextuelle)
- **2 liens vers satellites voisins** du même cluster
- **1-2 liens vers fiches produit** Altiaro pertinentes (ancre = intention d'achat)
- **0 lien externe** vers concurrents ; 1-2 liens sources autoritaires (INSERM, HAS, Que Choisir)

**Schemas JSON-LD** à injecter :
- `Article` (headline, author Person, datePublished, image)
- `FAQPage` (si section FAQ présente)
- `HowTo` (si article de méthode)
- `BreadcrumbList`

**Principe absolu** : intent match parfait. Rien de plus, rien de moins que ce que l'utilisateur cherche. Zéro remplissage SEO 2015.

**Livrables** :
- 30 fichiers `.md` dans `/content/blog/satellites/` avec frontmatter YAML (title, slug, cluster, pilier_parent, meta_description 155 car max, keywords, targeted_intent, image_hero, read_time_min)
- `internal_linking_map.xlsx` : matrice 30×30 montrant tous les liens internes
- `editorial_calendar.csv` : planning de publication sur 90 jours (3-4 articles/semaine)""",
    },
    {
        "number": 28,
        "phase": "G",
        "title": "Schemas JSON-LD exhaustifs + SEO technique",
        "summary": "lib/schemas.ts avec tous les schemas (Organization, Product, Article, FAQPage, BreadcrumbList, etc.) + sitemap dynamique + robots.txt + Core Web Vitals + images WebP/AVIF + preload + preconnect.",
        "prompt": """Implémente /app/frontend/src/lib/schemas.ts (JSON-LD + react-helmet-async):

Schemas:
Globaux: Organization (logo, sameAs, contactPoint), WebSite + SearchAction
Spécifiques: Home (WebPage+Organization), Collection (CollectionPage+BreadcrumbList+ItemList), Product (complet GTIN/MPN/brand/offers/shipping/returns/aggregateRating/review/additionalProperty+BreadcrumbList), Article (Article+Author Person+Publisher Org+BreadcrumbList+FAQPage si présent), FAQ globale (FAQPage 50+ mainEntity), Contact/About (AboutPage/ContactPage+LocalBusiness), Videos (VideoObject)

Tests: Schema.org validator + Rich Results Test Google + Lighthouse SEO audit

Autres optims:
- sitemap.xml dynamique (hreflang, lastmod, priority)
- robots.txt user-agents spécifiques (Googlebot, Bingbot, GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot)
- Canonical absolute URL chaque page
- hreflang fr-FR, fr-BE, fr-CH, fr-LU
- Preload fonts WOFF2 (max 2 poids)
- Preconnect cdn.shopify.com, fonts.gstatic.com, cdn.judge.me
- Critical CSS inline above-the-fold
- Images WebP+AVIF srcset 320/640/960/1280/1920
- Lazy loading natif + decoding=async
- Priority hints hero
- Web Vitals: LCP<2.2s, INP<200ms, CLS<0.05
- HTTP/2 push ou Early Hints 103
- Cache-Control long assets (1 an) + hash

Livrable: lib/schemas.ts + robots.txt + vite-plugin-sitemap + perfs_audit.md""",
    },
    {
        "number": 29,
        "phase": "G",
        "title": "Stratégie netlinking FR 90 jours",
        "summary": "30 sites prospects FR DR40+ (blogs seniors, asso, presse, annuaires, forums, partenaires), 4 tactiques (guest posts, digital PR étude, infographies, partenariats asso), calendrier 90j.",
        "prompt": """Stratégie NETLINKING FR 90 jours. Objectif: 20-30 backlinks DR40+.

A. 30 sites prospects (DR, thématique, type lien):
1. Blogs seniors (Notre Temps, Senior Actu, Les Enjoyeurs, Silver Planet)
2. Blogs aidants (Proche Aidant, Aidant.tv, Papa-Positive)
3. Associations (France Alzheimer, OldUp, Les Petits Frères des Pauvres)
4. Presse locale/régionale rubriques santé/bien vieillir
5. Annuaires qualitatifs (HOP!, Services à la personne gouv)
6. Forums actifs (Caducée, Doctissimo)
7. Partenaires BtoB (podologues, ergos, SSIAD, téléassistance)

Pour chaque: URL contact, rédac-chef LinkedIn, pitch angle, template email personnalisable.

B. 4 tactiques:
1. Guest posts experts (15 pitchs 500 mots gratuits signés ergo)
2. Digital PR / étude propriétaire (sondage YouGov/Opinea 2-3k€ → CP → reprise presse backlinks naturels)
3. Infographies shareables (5 infographies data + schema ImageObject)
4. Partenariats associatifs (article invité + kit produits donné → article remerciement)

C. Calendrier 90 jours semaine par semaine.
D. Toxic links monitoring Ahrefs/SEMrush mensuel + disavow trimestriel.

Livrable: backlinks_plan.md + 15 templates pitch + tracking_sheet.xlsx""",
    },
    # PHASE H — AEO
    {
        "number": 30,
        "phase": "H",
        "title": "Fondations AEO (Answer Engine Optimization)",
        "summary": "llms.txt + llms-full.txt + robots.txt autorisant crawlers IA (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Applebot), Bing Webmaster + IndexNow, schemas maximalistes.",
        "prompt": """Site RECOMMANDÉ par ChatGPT/Perplexity/Gemini/Claude/Bing Copilot.

Fondations AEO 2026:

1. /llms.txt racine (standard Answer.AI):
- Description marque 3 phrases
- URLs importantes curated (home, collections, articles piliers, FAQ, about, contact) + description 1 phrase chacune
- Bloc Optional politiques retour/livraison/garantie
- Version FR + llms-en.txt

2. /llms-full.txt: version complète condensée tout le contenu site en markdown LLM-optimized (génération auto au build script Node)

3. robots.txt autoriser crawlers IA:
  User-agent: GPTBot
  User-agent: ChatGPT-User
  User-agent: OAI-SearchBot
  User-agent: PerplexityBot
  User-agent: ClaudeBot
  User-agent: Claude-Web
  User-agent: anthropic-ai
  User-agent: Google-Extended
  User-agent: Bingbot
  User-agent: Applebot-Extended
  User-agent: Meta-ExternalAgent
  Allow: /

4. Indexation Bing (ChatGPT Search + Copilot + DuckDuckGo):
- Bing Webmaster Tools signup + sitemap
- IndexNow API push temps réel sur update

5. Schema.org maximaliste (déjà prompt 28)

Livrable: /public/llms.txt + /public/llms-full.txt (script auto) + /public/robots.txt + backend IndexNow auto-push""",
    },
    {
        "number": 31,
        "phase": "H",
        "title": "Content AEO-optimisé (réponses extractables)",
        "summary": "Adapter le contenu pour extraction IA : Q→R direct, listes+tableaux, stats datées, definitions encadrées, résumé 60 mots en tête, Author E-E-A-T maximisé, fact sheets produits, structure wiki-style.",
        "prompt": """Adapter style contenu pour EXTRACTION par IA:

1. Format Question → Réponse directe: H2 question, réponse directe 1-2 phrases (IA citent), puis dév long SEO
2. Listes + tableaux partout: IA extraient prioritairement
3. Statistiques citables: 3-5 chiffres datés+sourcés/article
4. Definitions encadrées: Qu'est-ce que X? sur chaque concept
5. Bloc Réponse rapide début article 60 mots (IA citent)
6. Author E-E-A-T maximisé: bio diplôme+exp+LinkedIn+affiliations, schema Author (jobTitle, worksFor, alumniOf, knowsAbout[], url), page /auteurs/[slug]
7. Fraîcheur: dates publication + dateModified visibles (2026, MAJ récente)
8. Fact sheets produits: bloc "Faits en bref" (poids, dim, origine, garantie, certifs) — extraction IA comparison
9. Mentions presse: page /presse liste mentions (URL, titre, date)
10. Wiki-style pages piliers: définition/histoire/types/critères/utilisation (mimer Wikipedia, #1 source IA)

Adapte les 15 articles piliers prompt 26 à cette structure AEO.

Livrable: content_aeo_guidelines.md + articles V2""",
    },
    {
        "number": 32,
        "phase": "H",
        "title": "Présence hors-site pour AEO",
        "summary": "Ubiquité : Wikipedia/Wikidata, Reddit/forums, YouTube, Quora/AMAs, GitHub, wiki-médias sectoriels, structured data marketplace, podcasts, CP autorité, tracking Profound/Peec AI.",
        "prompt": """IA ne citent pas que ton site — elles citent sources tierces qui te mentionnent. Stratégie ubiquité:

1. Wikipedia/Wikidata: créer entité Wikidata marque + citer dans articles Wikipedia pertinents (source fiable obligatoire → digital PR prompt 29)
2. Reddit/Forums (trustés training LLM): r/france, r/AideADomicile, r/GrandsParents, Aufeminin, Doctissimo, Caducée. Ton value-first, signature discrète. Réponses longues sourcées → Perplexity cite
3. YouTube: 10 vidéos tutoriels courts (Comment choisir, Unboxing, Démo) — Google/Gemini indexent transcripts
4. Quora/ask.fm/Reddit AMAs expert ergo → Q/A haute autorité
5. GitHub Awesome list ou datasets publics (ex: produits seniors) → citation LLM via fine-tune
6. Wiki-médias sectoriels: Gérontopedia, Fairpedia, Agorasanté
7. Structured data marketplace: Google Merchant Center riche, Bing Merchant, Meta Commerce (IA shopping consultent)
8. Interviews podcasts fondateur 4-5/an sur podcasts bien-vieillir (transcripts indexés)
9. CP schema.org NewsArticle sites autorité (PRWeb, PRNewswire France, Presse-citron)
10. Tester régulièrement: prompts IA "Meilleures boutiques [produit] FR?" tracker 30j. Outils: Profound, Peec AI, Evertune, Otterly.AI

Livrable: aeo_offsite_strategy.md + monitoring_sheet.xlsx""",
    },
    # PHASE I — Conversion
    {
        "number": 33,
        "phase": "I",
        "title": "CRO toolkit complet",
        "summary": "Exit-intent, sticky CTA mobile, sticky conseiller widget, barre livraison gratuite, countdown authentique, formulaire devis B2B, live chat, microsurvey, A/B test infra, 20 tests priorisés.",
        "prompt": """CRO toolkit:

1. Exit-intent popup desktop + scroll-up mobile: guide gratuit lead magnet contre email, 1 fois/session
2. Sticky CTA mobile bar: Ajouter panier + Appeler conseiller
3. Sticky conseiller widget bas-droit: photo+prénom+Me rappeler (form)+Chatter (bot)
4. Barre progressive livraison gratuite cart
5. Countdown expédition ("Commandez dans 2h14 pour expé aujourd'hui") horloge FR+cutoff 14h (authentique!)
6. Free shipping threshold optimizer (AOV × 1,15 auto)
7. Formulaire devis commandes >500€ (B2B, EHPAD)
8. Live chat Crisp/Tidio pré-qualif 3 questions puis bot
9. Microsurvey post-scroll 45s page produit: "Qu'est-ce qui vous retient?" 5 choix
10. A/B test infra: PostHog feature flags OU Shopify Shogun/GemPages

Plan 20 tests A/B priorisés sur 6 mois avec hypothèses chiffrées.

Livrable: CRO toolkit intégré + ab_test_roadmap.md""",
    },
    {
        "number": 34,
        "phase": "I",
        "title": "Social proof multicouche (anti-AI slop)",
        "summary": "Judge.me + Trustpilot + live social proof VRAI (webhook orders anonymisé) + presse + partenaires + compteur familles + note globale + vidéos témoignages + case studies + Instagram feed. Zero fake.",
        "prompt": """Social proof authentique:

1. Judge.me: avis produit + photos + réponses marque
2. Trustpilot widget home+footer (score réel)
3. Live social proof: "Emma de Nantes a commandé canne il y a 12 min" bas-gauche 45s → VRAI via webhook Shopify orders/paid anonymisé prénom+ville, RGPD
4. Vu dans la presse: 6 logos cliquables modal article
5. Partenaires: 4 logos (asso, experts)
6. Compteur "+X familles équipées" scroll animé (DATA RÉELLE Shopify count)
7. Note globale site (agrégation Judge.me + Trustpilot)
8. 4 vidéos témoignages clients réels (UGC ~80€/vidéo Bridge/Uprise/Influee)
9. Case studies long format blog: "Comment Jeanne a retrouvé mobilité" 1/mois
10. Mur Instagram embed (hashtag marque)

Anti-fake:
- PAS génération IA avis (illégal+détectable)
- PAS testimonials achetés Fiverr
- Modération stricte: répondre CHAQUE avis 1-3★ publiquement empathie+solution

Livrable: social_proof_stack.md + composants React + workflow modération""",
    },
    {
        "number": 35,
        "phase": "I",
        "title": "Klaviyo 7 flows email + SMS complets",
        "summary": "Welcome, abandon panier, abandon navigation, post-achat, winback, review request, VIP. Copywriting complet 50 emails + 6 SMS en ton marque vouvoiement chaleureux.",
        "prompt": """Configure 7 flows Klaviyo avec COPYWRITING complet ton marque (vouvoiement, chaleureux, jamais infantilisant):

FLOW 1 Welcome (inscription newsletter, 4 touches):
- Email 1 (instant): bienvenue + guide PDF lead magnet + histoire marque
- Email 2 (J+2): best-sellers 4 produits + témoignage vidéo
- Email 3 (J+4): -5% code BIENVENUE5 exp 7j urgency
- Email 4 (J+10): contenu valeur "10 conseils" blog + follow Insta/FB

FLOW 2 Abandon panier (checkout_started sans purchase, 4 touches):
- SMS (2h): "Votre article vous attend 🛒 [lien]"
- Email (4h): visuel cart + réassurance + témoignage
- Email (24h): -50€ si panier>200€, -20€ si 100-200€
- Email (72h): dernière chance deadline + FAQ

FLOW 3 Abandon navigation (viewed_product sans add_to_cart, 1 touche)
- Email J+1: article retenu attention? + 4 avis + comparaison

FLOW 4 Post-achat:
- Instant: confirmation + prochaines étapes
- J+3: colis arrive + notice PDF + vidéo tutoriel
- J+7: tout se passe bien? + demande avis Judge.me + produits complémentaires
- J+30: entretien + accessoires + programme fidélité

FLOW 5 Winback (60j inactif):
- Email 1: "Vous nous avez manqué" + sondage
- J+7: -15% 48h
- J+14: bye digne unsub propre

FLOW 6 Review request (delivered+14j):
- Demande avis Judge.me + Google
- Relance J+21 si pas répondu

FLOW 7 VIP (LTV>500€):
- Cercle VIP accès avant-premières + remises + conseiller dédié

Segmentations: Prospect senior/aidant, VIP/Fidèle/Occasionnel/Inactif, Acheteurs catégorie X.

Pour chaque email: objet + preheader + body + CTA + visuel décrit + timing.

Livrable: klaviyo_flows.md (50+ pages) + templates_import.json""",
    },
    # PHASE J — Paiement
    {
        "number": 36,
        "phase": "J",
        "title": "Stack paiement FR optimale dropshipping",
        "summary": "Shopify Payments (CB, Apple/Google Pay, 3DS) + PayPal Business + Alma 3x/4x (critique conversion) + virement B2B + anti-fraude + facturation auto conforme FR.",
        "prompt": """Configure stack paiement complet:

1. Shopify Payments (Stripe): CB (Visa, Mastercard, Amex optionnel), Apple/Google Pay, 3DS v2 auto dès 150€ (PSD2), descripteur bancaire clair
2. PayPal Business: Express Checkout + 4x sans frais (30-2000€ auto), compte Business Pro (+features)
3. Alma (critique high-ticket FR): 3x/4x sans frais jusqu'à 3000€ (2,5% vendeur), 10x/12x avec frais, intégration native + widget produit+cart, +25 à +40% conversion panier >300€
4. Virement bancaire B2B+grandes cmd: manual, validation 24-48h post-réception
5. Anti-fraude: Shopify Fraud Analysis activé, règle custom review manuelle >1500€ OU first order+email disposable OU billing≠shipping country, chargeback dispute kit
6. Facturation auto: app Sufio/Order Printer Pro, numéro facture séquentiel inaltérable (obligation FR), PDF conformes (raison sociale, SIRET, TVA intracom, RCS, client, TVA ventilée), envoi auto order paid
7. Conformité DSP2: 3DS challenge fluide, authentication strong customer, tokenization

Livrable: payments_setup.md + conformity_checklist.md""",
    },
    # PHASE K — Service client
    {
        "number": 37,
        "phase": "K",
        "title": "Chatbot GPT multi-canal avec RAG",
        "summary": "Chatbot FastAPI + LLM (Claude/GPT) + RAG sur catalogue, FAQ, politiques, blog. Widget frontend + WhatsApp + Messenger + email. RGPD opt-in. Escalade humaine auto. Dashboard admin.",
        "prompt": """Chatbot IA intégré:

Stack: Backend FastAPI /api/chat streaming SSE, LLM GPT-4o-mini OU Claude Haiku via Emergent LLM Key, RAG vector store (Chroma/Qdrant) sur catalogue Shopify + FAQ 50Q + politiques + articles blog (chunking 500 tokens). Session memory 10 msg. RGPD opt-in, purge 90j, export/delete rights.

Frontend: widget bouton flottant bas-droit, modal chat élégant, typography accessibility 18px, suggested prompts initiaux, indicateur typing + streaming.

Capacités: qualification besoin 5Q max, reco produit avec lien+image, explication politiques, suivi commande Shopify (session email+order), escalade humaine (détection frustration OU hors périmètre) → Gorgias avec contexte.

Canaux phase 2: WhatsApp Business Twilio/360dialog, Messenger + IG DM, email auto-reply support@ (GPT pré-remplit, humain valide).

Ton: vouvoiement, phrases <20 mots, empathique, offrir alternative humaine. Interdits: "ma petite dame", "c'est facile", jugement.

Dashboard admin: conversations récentes, KPIs (volume, taux escalade, satisfaction thumbs), topics émergents, conversations à review.

Livrable: backend + Chat.tsx + system_prompt.md + RAG pipeline + dashboard""",
    },
    {
        "number": 38,
        "phase": "K",
        "title": "Helpdesk centralisé + 30 macros",
        "summary": "Gorgias centralise email/chat/WhatsApp/Messenger/IG/téléphone. Règles auto-tag ML, priorités, SLA <2h, intégration Shopify fiche client, 30 macros pré-écrites, dashboard KPI.",
        "prompt": """Setup Gorgias (recommandé e-commerce Shopify):

Centralisation canaux: support@ email, chat site (hand-off bot prompt 37), WhatsApp Business (Twilio/WATI 20€/mois), Messenger+IG DM, téléphone Aircall transcription auto.

Configuration:
1. Règles auto-tag par motif (ML Gorgias): livraison/SAV/avant-vente/paiement/facture/retour/garantie/compte/autre
2. Priorités auto: P1 VIP/réclamation forte, P2 avant-vente, P3 info
3. SLA: 1ère réponse <2h jour (9h-19h LS), <24h hors
4. Intégration Shopify: fiche client dans conversation (commandes, AOV, tags)
5. 30 macros pré-écrites en ton marque
6. Auto-close 5j inactifs + relance CSAT
7. Escalade manager si tag réclamation ou CSAT 1-2/5

30 macros: statut commande, retard livraison reconnu, procédure retour, défectueux reçu, changement adresse, demande facture, annulation, éligibilité produit...

Dashboard KPI quotidien: volume/agent, délai 1ère réponse, CSAT, FCR, motifs top 5.

Livrable: gorgias_config.md + 30_macros.md + workflow_escalation.md""",
    },
    {
        "number": 39,
        "phase": "K",
        "title": "Téléphonie FR + 3 scripts vente senior",
        "summary": "Aircall/Ringover numéro FR 01/09, menu vocal chaleureux, 9h-19h L-S, enregistrement RGPD, intégration Shopify, 3 scripts (vente entrante, SAV, rappel lead).",
        "prompt": """Setup téléphonie pro:

1. Numéro FR fixe virtuel: Aircall (30€/mois), Ringover (20€/mois), Onoff Business. Numéro 01 Paris ou 09 dédié (PAS 06). Enregistrement avec annonce RGPD obligatoire.
2. Menu vocal humain court:
"Bonjour, bienvenue chez [NOM]. Pour suivi commande, tapez 1. Conseil avant achat, tapez 2. Autre demande, restez en ligne. Décrochage <1 minute."
3. Horaires 9h-19h L-S (samedi critique seniors retraités) + renvoi répondeur promesse rappel <2h (SLA)
4. Intégration Shopify: pop fiche client Aircall au décroché (nom, dernière cmd, historique)
5. Logging: appels → Shopify customer notes + Gorgias transcription

3 SCRIPTS:
A. Vente entrante 10 étapes: accueil personnalisé → écoute 2min → reformulation → diagnostic 3-5Q → reco 2 produits max → traitement objection prix (valeur, 3x, garantie) → objection livraison → closing doux → upsell léger → remerciement
B. SAV/litige: empathie (valider émotion) → diagnostic → solution 3 options → engagement délai → suivi J+2
C. Rappel lead (formulaire "être rappelé"): présentation contexte → script vente entrante

Livrable: telephony_setup.md + 3 scripts + objections_book.md""",
    },
    # PHASE L — Logistique
    {
        "number": 40,
        "phase": "L",
        "title": "Chaîne logistique drop optimale",
        "summary": "3 phases : dropship direct EU (0-10/j), 3PL EU 20 unités stock (10-50/j), marque privée stock EU (50+/j). Transporteurs négociés, politique livraison transparente, process colis perdu.",
        "prompt": """Chaîne logistique drop-shipping:

Phase 1 (0-10 cmd/j): dropship direct entrepôt EU (CJ EU, BigBuy, Matterhorn). Délai client 5-10j FR / 7-14j UE. Packaging fournisseur (négocier ship without brand on box). Insert carte remerciement (OEM niveau 1 ou stock tampon local).

Phase 2 (10-50 cmd/j): stocker 20 unités top chez 3PL EU (Byrd, Logsta, Eubrik, Salesupply). Packaging brandé. Délai client 2-4j (×2 conv).

Phase 3 (50+ cmd/j): stock EU marque privée, 3PL premium (Byrd multi-pays, Shipmonk EU), retours portail client auto.

Transporteurs à négocier (comptes pro): Colissimo ≤30kg, Chronopost express, DPD Predict créneaux 1h (top seniors!), Mondial Relay relais éco, UPS Standard EU, GLS rapport qualité/prix, Dachser/Geodis palettes high-ticket. Cibles -15 à -25% vs tarif carte à 50 envois/mois.

Politique livraison affichée (transparence): délai prépa 24-48h, délai transport réaliste par transporteur, n° suivi <48h, signature >300€, refus livraison = re-expé frais client.

Process colis perdu/endommagé: réclamation transporteur J+8 sans scan, client soit renvoi gratuit immédiat (experience) soit attend indemnisation (décider par valeur/LTV), documentation preuves photos avant expé si stock propre.

Livrable: logistics_playbook.md + suppliers_SLAs.xlsx""",
    },
    {
        "number": 41,
        "phase": "L",
        "title": "Module tracking client + notifications",
        "summary": "Backend webhook Shopify + AfterShip/Track123, frontend page /suivi-commande timeline 7 étapes, estimation dynamique, photos preuve, notifications email+SMS, anti-où-est-mon-colis.",
        "prompt": """Module tracking post-achat:

Backend:
- Webhook Shopify orders/fulfilled → stock n° tracking + carrier
- AfterShip API (gratuit <100/mois) OU Track123 polling multi-opérateurs
- Webhook AfterShip updates → DB update + trigger notifs

Frontend /suivi-commande:
- Input email + n° commande OU lien magique email
- Timeline 7 étapes custom: Commande reçue ✓, Paiement validé ✓, Préparation ⏳, Expédié, En transit, En tournée aujourd'hui, Livré. (Retour: 8 Retour initié / 9 reçu / 10 remboursé)
- Estimation livraison exacte (date) dynamique
- Photos transporteur si API Colissimo preuve livraison

Notifications auto (email + SMS optionnel):
- Confirmation commande (instant)
- Expédition (n° tracking)
- Sortie tournée (jour J)
- Livré
- Exceptions: retard >2j vs ETA → proactif "nous avons alerté", adresse refusée → relance, souffrance relais → reminder

Anti-"où est mon colis?": -60% tickets SAV avec tracking clair.

Livrable: /api/tracking/* + Suivi.tsx + Klaviyo transactional templates""",
    },
    {
        "number": 42,
        "phase": "L",
        "title": "Portail retours + automatisation SAV",
        "summary": "/sav self-service (tracking, formulaire retour, FAQ, RDV), backend auto (ticket Gorgias, étiquette prépayée Sendcloud, remboursement auto), dashboard admin SAV.",
        "prompt": """Portail retours client-friendly:

Page /sav:
1. Self-service: suivi commande (prompt 41), formulaire retour (commande+produit+motif dropdown+photos upload+demande remb/échange/avoir), notices PDF/vidéos, FAQ interactive recherche, RDV téléphone (Calendly)

Backend automation:
- Génération ticket Gorgias auto (tag + priorité)
- Motif "changement d'avis" (14j rétractation): étiquette prépayée auto (Sendcloud, ShippyPro, Shopify Returns), email instructions, remboursement auto dès scan retour 3PL
- Motif "défectueux": remboursement sans retour si <80€ (coût retour>valeur), sinon étiquette + remplacement parallèle (wow)
- Motif "autre choix": proposition échange auto (catalogue reco)

Dashboard admin SAV: délai résolution moyen, taux retour par produit (détection défaut), coût SAV mensuel, motifs top 5 (input amélioration fiche/sourcing).

Livrable: /app/frontend/src/pages/Sav.tsx + backend automation + Gorgias workflows + sav_dashboard.tsx""",
    },
    # PHASE M — Google Ads
    {
        "number": 43,
        "phase": "M",
        "title": "Architecture Google Ads 30€/j rentable",
        "summary": "Merchant Center, répartition 4 campagnes (Shopping Standard 40%, PMax 20%, Search 30%, Remarketing 10%), audiences, enchères, conversions, règles d'or learning phase.",
        "prompt": """Budget 30€/j = 900€/mois. Objectif 1ère vente <30j puis tuner ROAS.

Structure compte:

1. Merchant Center setup: flow Shopify via app Google & YouTube Channel, GTIN ou MPN obligatoire, images ≥800×800, titres <150 car. (KW+brand+attribut), descriptions ≥250 car., catégorie Google précise. Fix disapprovals prioritaire.

2. Répartition 30€/j:
| Campagne | Type | % | €/j | Cible |
|---|---|---|---|---|
| 1 Shopping Standard | Priority HIGH | 40% | 12€ | Conv direct top KW |
| 2 PMax | Performance Max | 20% | 6€ | Découverte + YouTube/Display |
| 3 Search haute intention | Search | 30% | 9€ | Closer chauds |
| 4 Remarketing | Display RLSA | 10% | 3€ | Panier + visiteurs |

Stratégie: commencer Shopping Standard (PAS PMax pur à 30€/j — pas assez data optim). Shopping Standard = CONTROL sur quels produits pushes.

3. Shopping Standard: groupes par marge (tag margin_high/mid/low), bidding Manual CPC début (max CPC 0,80€ mid-ticket, 1,50€ high-ticket), passer Maximize conversions après 30 conv, audience signals customer_list + visiteurs 30j + lookalike, exclure mobile si perfs mauvaises

4. PMax Retail: produits marge>70%, assets 15 images lifestyle + 5 logos + vidéo 15s + 5 headlines + 5 descriptions + audience signals, cible ROAS 3.5 début

5. Search exact+phrase: 4 AG (Nom produit, Meilleur/Avis, Concurrent, Acheter+produit), 3 RSA/AG, extensions sitelinks+callouts+structured snippets+price+location+lead form, mots négatifs (gratuit, occasion, leboncoin, définition, emploi, stage, bricolage, kijiji, solution urgence), conversions purchase primaire + lead + phone_click secondaires

6. Remarketing Display: audiences Shopify (all visitors 30j, product viewers 30j, cart abandoners 14j), bannières responsives + 6 visuels produit top, cap fréquence 3/j/user

7. Tracking: Enhanced Conversions activées, value-based bidding après 50 conv, conversion path modeling

Règles d'or: aucune décision avant 3000€ dépensés OU 50 conv, jamais couper campagne en learning (7j min), test 1 variable à la fois.

Livrable: google_ads_structure.md + naming_convention.md + merchant_feed.md""",
    },
    {
        "number": 44,
        "phase": "M",
        "title": "100 headlines + 30 RSA optimisés",
        "summary": "100 headlines (Produit+KW, USP Marque, Bénéfice, Prix/Finance, Social Proof) + 50 descriptions + 30 RSA pinning + 20 sitelinks + 10 callouts + 5 structured snippets.",
        "prompt": """Rédige 100 HEADLINES (<=30 car.) + 50 DESCRIPTIONS (<=90 car.) + 20 SITELINKS + 10 CALLOUTS + 5 STRUCTURED SNIPPETS pour [NOM_MARQUE] niche [NICHE].

100 headlines en 5 familles (20 chacune):
A. Produit+KW: "Canne Pliante Ultra Légère 279g"...
B. USP Marque: "Livraison Offerte en France", "Essai 30 Jours"...
C. Bénéfice émotionnel: "Plus d'Autonomie à Domicile"...
D. Prix/Finance: "Dès 29€ Livraison Offerte", "Payez en 3x Sans Frais"...
E. Social Proof: "+2 000 Familles Équipées", "Note 4,8/5"...

Assemblage 30 RSA avec pinning:
- Position 1 = famille B ou C (marque/bénéfice)
- Position 2 = A (KW)
- Position 3 = D ou E (trust)

Sitelinks: url + description 2 lignes (Guide d'achat, Avis, Livraison, Paiement 3x, Contact)
Callouts (25 car.): Livraison offerte, Essai 30j, SAV France, Paiement 3x, Garantie 2 ans, Conseiller dédié
Structured snippets: Types, Brands, Features, Models

Livrable: google_ads_copy.csv""",
    },
    {
        "number": 45,
        "phase": "M",
        "title": "5 landing pages ads haute conversion",
        "summary": "5 LP dédiées (SKAG friendly, sans navigation, hero match KW, vidéo 30s, produits pré-sélectionnés, témoignages, FAQ, formulaire inline rappel), Lighthouse 99.",
        "prompt": """5 LANDING PAGES dédiées Google Ads (différentes pages produit standard — ultra-focused CRO):

1. /lp/[KW-1]
2. /lp/[KW-2]
3. /lp/[KW-3]
4. /lp/[KW-4]
5. /lp/devis-gratuit (lead gen)

Structure LP:
- Header épuré: logo seul + téléphone droite (PAS nav!)
- Hero match exact KW (SKAG friendly): H1="Le meilleur [produit] pour [situation]", sous-titre bénéfice clé, vidéo démo 30s auto-play muted+controls, CTA primaire fold
- Bandeau 4 réassurance icônes
- 3 produits pré-sélectionnés + comparateur simplifié (prix, caracts, CTA)
- Bloc Comment ça marche? 3 étapes
- Bloc 3 témoignages clients réels + vidéo
- Bloc FAQ 6 questions
- CTA final + formulaire inline "Me faire rappeler gratuitement" (nom, tel, horaire) → Gorgias + SMS alerte + Google Ads conversion event
- Footer minimal: logo + mentions + téléphone

Performance: LP <1.5s LCP, Lighthouse 99, mobile first.

Tracking: GA4 lead_submit/purchase, Google Ads conversion upload valeur, Meta CAPI event.

A/B tests: hero A (bénéfice) vs B (peur), CTA color, prix showing vs hiding.

Livrable: 5 LP React + tracking gtag.ts""",
    },
    {
        "number": 46,
        "phase": "M",
        "title": "Plan optimisation ads 90 jours",
        "summary": "Semaine 1-2 learning, S3-4 tuning (négatifs, RLSA, A/B), S5-8 scale (+20% best, PMax segmenté), S9-12 maturation (value bidding, UE expansion, YouTube, scripts auto).",
        "prompt": """Plan optimisation ads 90 jours (30€/j):

Jours 1-14 — Learning phase (ne rien couper):
- Toutes campagnes tournent (sauf catastrophe)
- Monitoring quotidien basique
- Aucun ajustement budget/cible avant 7j
- Accumuler 20 conv min pour décisions statistiques

Jours 15-30 — Premier tuning:
- Analyse Search Terms → négatifs (-15% dépense inutile)
- Pause produits Shopping CTR<0,5% ET impr>500
- Ajout audiences signals supplémentaires
- A/B RSA headlines
- Ajustement tranches horaires (couper 23h-6h si pas conv)
- Activer RLSA remarketing search

Jours 31-60 — Scale ce qui marche:
- Campagnes ROAS>3: budget +20%/semaine
- Shopping: segmentation par produit → best sellers priority HIGH, reste MEDIUM
- Création annonces DSA (dynamic) longue traîne
- Début Meta Ads si Google ROAS stable 3+

Jours 61-90 — Maturation:
- Value-based bidding (max conversion value + tROAS)
- Expansion UE progressive (DE, ES, IT, BE)
- Test YouTube Ads (skippable démo 30s, CPM bas)
- Automation rules (alerts CPA>2x cible, budget pacing)
- Retargeting avancé par segment

Scripts Google Ads:
- Alerte spend inattendu (+30% jour)
- Low-CTR ads auto-pause
- 404 detection (URL désactivée → pause annonce)
- Weekly report email auto

Reporting hebdo (Looker Studio template): dépense, conv, CPA, ROAS/campagne, top 10 KW perfs + 10 mauvais, évol CR, décisions+hypothèses S+1.

Livrable: ads_optimization_playbook.md + scripts.js + weekly_report_template.md""",
    },
    # PHASE N — Analytics
    {
        "number": 47,
        "phase": "N",
        "title": "GA4 + CAPI + server-side tracking complet",
        "summary": "GTM Web+Server, GA4 events ecommerce, Consent Mode v2 CNIL, Enhanced Conversions, Meta CAPI, Shopify Pixel custom, backend FastAPI tracking, tests DebugView/Tag Assistant/Events Manager.",
        "prompt": """Mesure AVANCÉE (perte signal iOS14 / Consent Mode v2):

1. Google Tag Manager Web + Server containers:
- Web GTM: events client-side GA4 + Google Ads enhanced conversions (email hash SHA-256)
- Server GTM: relai vers GA4 + Google Ads API + Meta CAPI + TikTok Events API + Pinterest

2. GA4 events ecommerce complets:
view_item_list, view_item, select_item, view_promotion, select_promotion, add_to_cart, remove_from_cart, view_cart, begin_checkout, add_shipping_info, add_payment_info, purchase (value/currency/tax/shipping/items[]), refund, sign_up, login, generate_lead, search (query)
Custom: phone_click, whatsapp_click, form_submit_lead, newsletter_signup, exit_intent_shown, chat_opened

3. Consent Mode v2 (obligatoire UE): bannière CNIL Cookiebot/Axeptio/Didomi, signaux ad_storage/analytics_storage/ad_user_data/ad_personalization, GTM conditionnel consent

4. Enhanced Conversions Google Ads: données hash (email, phone, name, address) client + offline upload backend long cycle

5. Meta CAPI (phase Meta Ads): backend FastAPI /api/tracking/meta reçoit webhook Shopify order + emit event PurchaseserverSide event_id dédoublé côté pixel. Stape.io/Rudderstack simplifier (alt: native)

6. Shopify Pixel custom: web pixel extension Shopify manifest v3 capture events checkout

7. Backend FastAPI /app/backend/routes/analytics.py: POST webhook Shopify orders/paid → push GA4 Measurement Protocol + Google Ads offline + Meta CAPI + TikTok + server log. Anti-tampering hash. Event_id standard dédup client vs server.

8. Tests go-live: GA4 DebugView (events trigger), Google Tag Assistant (tags fire), Meta Test Events (dédup server-side), Search Console connecté GA4.

Livrable: routes/analytics.py + GTM container JSON + /frontend/src/lib/analytics.ts + testing_checklist.md""",
    },
    {
        "number": 48,
        "phase": "N",
        "title": "Audit & monitoring SEO continu",
        "summary": "Stack outils (GSC, GA4, Bing WMT, Ahrefs gratuit, PageSpeed, Screaming Frog), Looker Studio 5 onglets, rituels mensuels, alertes auto.",
        "prompt": """Dashboard monitoring SEO mensuel:

Outils connectés:
- Google Search Console (principal)
- Google Analytics 4
- Bing Webmaster Tools (AEO!)
- Ahrefs Webmaster Tools (gratuit: backlinks, top pages)
- PageSpeed Insights (Core Web Vitals)
- Screaming Frog (audit technique mensuel 500 URLs gratuit)

Dashboard Looker Studio 5 onglets:
- Overview: impressions, clics, CTR, positions
- Top pages: trafic SEO/page, évol
- Top mots-clés: opportunités top 4-20 à booster top 3
- Backlinks: nouveaux, perdus, DR
- Technical health: indexation, CWV, 404, crawl budget

Rituels SEO mensuels:
- Audit technique Screaming Frog → fix issues
- 4 articles blog (2 piliers + 2 satellites)
- Relance 10 prospects netlinking
- Update 5 articles anciens (fraîcheur)
- Monitoring positions top 30 KW (SERPRobot 20€/mois)

Alertes auto:
- Baisse trafic >20% S/S
- Pages désindexées soudaines
- CWV passées Poor
- Backlink toxique spam>80

Livrable: seo_monitoring_stack.md + Looker template URL + rituals_calendar.md""",
    },
    # PHASE O — Duplication
    {
        "number": 49,
        "phase": "O",
        "title": "Refactor en template multi-niches",
        "summary": "Config centralisée /config/brand.config.ts, features optionnels par niche, CLI npm run create-brand, docs duplication_sop + niche_checklist.",
        "prompt": """Refactore projet front+back en TEMPLATE réutilisable <5j pour nouvelle niche.

Centralisation config: /config/brand.config.ts unique avec Brand (name, tagline, manifesto, storyteller bio), Visual (colors CSS vars, fonts Google imports, logos URLs), Products (catégories, hero, USPs), Legal (entité, SIRET, adresse, DPO), Integrations (Shopify domain, Klaviyo list ID, GA4, Meta Pixel), Copy (20 textes fréquents), i18n (langues, default).

Extraire composants niche-spécifiques /features/ optionnels:
- Senior: AccessibilityPanel, LargeText, SimulatorAPA
- Kids: GamificationBadge, ParentalControl
- Pro: QuoteBuilder, B2BPricing

CLI npm run create-brand (node script):
- Prompt interactif: nom, niche, couleurs, fonts, domaine
- Génère /config/brand.config.ts
- Clone .env.example → .env
- Crée repo Git
- Deploy trigger Vercel/Emergent

Documentation duplicable:
- /docs/duplication_sop.md (workflow 20 étapes niche validée → go-live)
- /docs/niche_checklist.md (check-list produits duplicables?)

Livrable: template + CLI + docs""",
    },
    {
        "number": 50,
        "phase": "O",
        "title": "SOPs opérationnels + organigramme scalable",
        "summary": "10 SOPs (sourcing, fiche, blog, SAV, ads, revue perf, modération avis, onboarding produit, rupture, ouverture niche), organigramme Mois 6, 3 scénarios budget.",
        "prompt": """Documente tous SOPs pour faire tourner marque + dupliquer:

SOPs opérationnels (Notion/GitBook):
1. Sourcing produit (10 étapes validation fournisseur)
2. Rédaction fiche produit SEO+CRO (check-list 30 points)
3. Publication article blog (brief → rédac → SEO → pub → diffusion)
4. Gestion ticket SAV (arbres décision remboursement/retour/échange/geste commercial)
5. Lancement campagne ads (brief créatif → prod → test → scale)
6. Revue hebdomadaire perf (agenda, data, décisions)
7. Modération avis (quoi répondre à 1-2-3-4-5★)
8. Onboarding nouveau produit (7 jours découverte→live)
9. Gestion rupture stock fournisseur
10. Ouverture nouvelle niche (playbook 30j)

Organigramme cible Mois 6:
- Fondateur: stratégie, deal fournisseurs, finances
- VA FR SAV freelance (15h/sem, 300€/mois)
- Media buyer freelance (5h/sem, 500€/mois)
- Rédacteur SEO freelance (6 articles/mois, 600€)
- Graphiste/UGC freelance (mission, 300€/mois)
- Comptable (100€/mois)

Total charges op ~1800€/mois = CA nécessaire 10-15k€ pour viable.

3 scénarios budget mensuels (CA 10k / 30k / 100k) avec réallocation ads + team + stock.

Livrable: sops_notion_export.md + org_chart.md + budgets_scenarios.xlsx""",
    },
]


def get_seed_steps_for_site(site_id: str):
    """Return list of step dicts to be inserted when a new site is created."""
    from datetime import datetime, timezone
    import uuid

    steps = []
    now = datetime.now(timezone.utc).isoformat()
    for p in PROMPTS:
        block_id = PHASE_TO_BLOCK.get(p["phase"], "template")
        block_meta = BLOCKS[block_id]
        steps.append({
            "id": str(uuid.uuid4()),
            "site_id": site_id,
            "number": p["number"],
            "phase": p["phase"],
            "phase_name": PHASES[p["phase"]],
            "block": block_id,
            "block_name": block_meta["name"],
            "block_order": block_meta["order"],
            "block_emoji": block_meta["emoji"],
            "title": p["title"],
            "summary": p["summary"],
            "prompt": p["prompt"],
            "status": "locked" if p["number"] > 1 else "in_progress",
            "deliverable_url": "",
            "deliverable_notes": "",
            "deliverable_files": [],
            "ai_response": "",
            "ai_model_used": "",
            "submitted_at": None,
            "validated_at": None,
            "validated_by": None,
            "rejection_reason": "",
            "created_at": now,
            "updated_at": now,
        })
    return steps
