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
    "E": "backend Altiaro",
    "F": "Front React (template Altiaro fourni)",
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
        "description": "Cadre légal, backend Altiaro, sourcing fournisseurs, import catalogue 20 produits — les fondations avant le front.",
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
        "description": "CRO, social proof, Brevo 7 flows, paiement optimisé, chatbot, helpdesk, téléphonie.",
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
    "E": "fondations",   # backend Altiaro (inclut import catalogue)
    "F": "front",        # Front React (template Altiaro fourni) + pages
    "G": "seo",          # SEO technique
    "H": "seo",          # AEO/GEO
    "I": "conversion",   # CRO + social proof + Brevo
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

Je lance une boutique Altiaro FR/EU sur la niche : **[NICHE]**.
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

1. CGV B2C 25 articles min (identité, prix TTC/TVA, commande, paiement CB/Mollie (Bancontact, iDEAL, Apple Pay)/Alma, livraison drop transparente, IOSS, rétractation 14j + formulaire annexe I, garantie légale 2 ans, SAV, RGPD, médiation CE2C, droit applicable)
2. Mentions légales (hébergeur, éditeur, directeur pub, RCS, TVA, DEEE, contact)
3. Politique RGPD (6 finalités, durée, droits, DPO, transferts hors UE Altiaro/Google US)
4. Politique cookies bannière CNIL conforme
5. Politique rétractation + formulaire-type
6. CGU newsletter/fidélité

Livrable: 6 fichiers .md + version HTML Altiaro pages""",
    },
    # PHASE E — Altiaro Backend
    {
        "number": 14,
        "phase": "E",
        "title": "Paramétrage backend Altiaro (taxes, livraison, paiement)",
        "summary": "Configuration du backend Altiaro : taxes OSS/IOSS, zones livraison FR/UE/DOM-TOM, méthodes de paiement Mollie, emails transactionnels — tout est déjà branché, il ne reste qu'à paramétrer.",
        "prompt": """Tu es ops manager d'un e-commerce FR senior, 8 ans sur stack custom (pas Shopify).

La boutique [NOM_MARQUE] tourne sur **Altiaro** (notre plateforme propriétaire React + FastAPI + Mollie). Le template, le checkout, les pages légales, les webhooks Mollie sont **déjà branchés d'office**. Tu n'as **rien à coder**.

Ta mission : me livrer un **brief de paramétrage** prêt à exécuter dans le back-office Altiaro.

**1. Taxes (niche [NICHE], cible FR+UE)**
- Régime TVA : franchise en base ? TVA 20% ? OSS (One-Stop Shop UE) si > 10k€ UE ?
- Taux applicables par catégorie produit (standard 20% / taux réduit 5,5% si catégorie médicale / exonération si certif)
- IOSS si import direct Chine < 150€

**2. Zones de livraison et transporteurs**
- Tableau des zones : FR métropole, Corse, DOM-TOM, Belgique+Luxembourg, Allemagne, Pays-Bas, Suisse, UK
- Pour chaque zone : transporteur recommandé (Colissimo/Mondial Relay/Chronopost/DHL), délai, prix par palier de poids
- Seuil franco de port (ex: 150€ France)

**3. Méthodes de paiement Mollie**
- Méthodes à activer par pays : CB/VISA (tous), Bancontact (BE), iDEAL (NL), Apple Pay + Google Pay (tous), PayPal Mollie (tous), virement B2B si panier > 500€
- Alma 3x/4x (si éligible, seuil 100€)
- Frais vs conversion attendue par méthode

**4. Emails transactionnels**
- Liste des 8 emails à configurer (commande reçue / payée / expédiée / livrée / retour / rétractation / relance panier / welcome)
- Ton à adopter (chaleureux sans infantiliser, voix de marque prompt #7)

**Livrable** : `backend_setup_checklist.md` avec chaque section en check-list actionnable (✅ à cocher une fois configuré dans l'admin Altiaro). 800-1200 mots MAX, pas de code.""",
    },
    {
        "number": 15,
        "phase": "E",
        "title": "Brief import catalogue (20 produits haute qualité)",
        "summary": "Rédaction complète des 20 fiches produits (titre SEO, body 700+ mots, meta, tags, alt image). Le hook #16 injecte automatiquement les produits en BDD à validation.",
        "prompt": """Tu es copywriter e-commerce FR spécialisé senior (fiches Fauteuils de France, Domitys, Hagnoss).

Pour la boutique [NOM_MARQUE] (niche : [NICHE]), rédige les **20 fiches produits prioritaires** retenues dans la feuille de route (prompt #4). Le backend Altiaro importera ces fiches automatiquement à validation — **livre un JSON exploitable**.

**Format strict pour chaque produit** :
```json
{
  "handle": "nom-produit-kebab-case",
  "title": "Nom commercial FR 60 caractères max",
  "short_description": "Pitch 1 phrase (120 car. max) — le bénéfice clé",
  "description_md": "Body 700-900 mots en markdown, structuré ainsi :\\n\\n## Ouverture émotionnelle (100 mots)\\n\\n## 5 bénéfices clés\\n(bullets avec preuve pour chaque)\\n\\n## Pour qui ?\\n(3-5 personas)\\n\\n## Caractéristiques techniques\\n| Dimension | Valeur |\\n\\n## Contenu du colis\\n\\n## Notre engagement marque (garantie, SAV, livraison)\\n\\n## FAQ (5 Q/R)\\n\\n## Conformité et certifications (CE, REACH, etc.)",
  "price_eur": 149.00,
  "compare_at_price_eur": 199.00,
  "supplier_cost_eur": 42.00,
  "sku": "SKU-0001",
  "weight_kg": 2.5,
  "category": "Confort",
  "tags": ["aidance", "arthrose", "salon", ...],
  "meta_title": "60 caractères max",
  "meta_description": "155 caractères max",
  "image_alt_hero": "Description sémantique de l'image principale"
}
```

**Règles** :
- **20 produits minimum**, tous cohérents avec la niche et la feuille de route #4
- Prix vente avec marge ≥ 70% (cost/price)
- Zéro placeholder dans les livrables finaux
- Ton chaleureux senior (vouvoiement, pas d'infantilisation, voix de marque #7)
- Conformité : pas de promesse thérapeutique si pas de marquage CE médical

**Livrable** : bloc JSON unique (array de 20 objets), exécutable par le hook #16 auto-import. **C'est tout** — pas de code CSV, pas d'images à générer.""",
    },
    {
        "number": 16,
        "phase": "E",
        "title": "Intégrations tierces Altiaro (emails, avis, analytics)",
        "summary": "Brief d'activation des intégrations natives Altiaro : Resend (emails transac), Brevo (marketing), Trustpilot + Judge.me (avis), GA4 + Meta Pixel + TikTok Pixel. Les connecteurs sont déjà codés.",
        "prompt": """Tu es growth / martech lead (10 ans e-commerce FR > 5M€/an).

La boutique [NOM_MARQUE] tourne sur **Altiaro** — les connecteurs backend pour toutes les intégrations sont **déjà codés**. Ta mission : définir **quelles intégrations activer, dans quel ordre, et avec quelle config**.

**Couvre impérativement** :

**1. Emails transactionnels et marketing**
- **Resend** (transactionnel) : déjà branché côté backend. Paramètres à définir : from-name, reply-to, template design (header logo + footer mentions).
- **Brevo** ou **Mailjet** (marketing) : lequel choisir ? Plan recommandé ? 7 flows à créer (welcome, abandon panier, relance client, post-achat, review request, winback 60j, anniversaire).

**2. Avis clients et social proof**
- **Trustpilot** (site-level, gratuit puis payant) vs **Judge.me** (produit-level) vs **Loox** (photo-first). Recommandation pour niche [NICHE] senior.
- Flow de collecte automatique post-achat (J+14, J+30)
- Injection schema JSON-LD `AggregateRating` sur fiches produit

**3. Analytics + tracking**
- **GA4** : config propriétés, événements e-commerce (view_item, add_to_cart, purchase), conversion funnel
- **Meta Pixel** + **Conversions API** (côté serveur via webhook Altiaro)
- **TikTok Pixel** (si cible silver < 75 ans active sur TikTok)
- **Mixpanel** ou **PostHog** (optionnel, pour comportement utilisateur granulaire)

**4. Service client**
- **Gorgias** (helpdesk unifié email + chat + Meta DM) dès 20 tickets/jour
- **Tawk.to** ou **Intercom** (chat live) — recommandation

**Pour chaque intégration** : plan tarifaire recommandé, seuil de déclenchement (quand activer), config exacte (clés API à créer où), KPI à tracker.

**Livrable** : `integrations_stack.md` en tableau priorisé (À activer maintenant / Phase 2 / Phase scale) + 800-1500 mots MAX.""",
    },
    # PHASE F — Front (prompts 17-24)
    {
        "number": 17,
        "phase": "F",
        "title": "Customisation du template Altiaro (design, sections homepage)",
        "summary": "Le template Altiaro (React premium light) est déjà appliqué au hook #17. Ce brief affine les choix de sections homepage, couleurs finales, typographies, assets visuels à produire.",
        "prompt": """Tu es directeur artistique e-commerce FR (ex-Sézane, ex-Petit Bateau).

Le template **Altiaro Premium Light** est **déjà appliqué** à la boutique [NOM_MARQUE] (hook #17 automatique, brand book du #6 injecté). Tu n'as rien à coder.

Ta mission : livrer le **brief de customisation** pour que les développeurs front appliquent les dernières touches visuelles propres à la niche.

**1. Sections homepage à activer/désactiver**
Le template propose 13 sections modulaires (hero, personas, produits phares, social proof, engagements, comparatif, blog, fondateur, FAQ, newsletter, footer). Pour [NICHE] :
- Quelles 7-9 sections retenir (priorités) ?
- Dans quel ordre (funnel de conversion) ?
- Pourquoi retirer les autres ?

**2. Charte finale**
- Couleurs validées (reprend #6 brand book) : primary, accent, background, text — vérifier contrastes WCAG AAA
- Typographie : tailles par breakpoint mobile/tablet/desktop
- Radius, ombres, espacements (grid 4 vs 8)

**3. Assets visuels à produire**
Liste exhaustive des médias à produire (ou sourcer) :
- 1 hero vidéo 15-30s (scénario en 3 lignes)
- 6-8 photos produits lifestyle (styling, décor, mannequin silver)
- 3-5 photos équipe / coulisses / fondateur
- 4 illustrations vectorielles pour sections engagements
- 1 logo animé pour preloader

Pour chaque : format, dimensions, style (photo réelle vs IA vs illustration), brief de direction artistique en 1 paragraphe.

**4. Micro-interactions et motion**
- Hover states (boutons, cards produits, liens)
- Transitions de page (fade/slide ?)
- Animations scroll reveals
- Feedback tactile (add-to-cart anim, toast confirmation)

**5. Accessibilité renforcée senior**
- Taille corps minimale 18px (pas 16px)
- Boutons min 56px haut
- Contraste AAA (pas AA)
- Alternative texte tous médias
- Raccourcis clavier (skip-links, Cmd+K recherche)

**Livrable** : `homepage_customization_brief.md` (1500-2000 mots MAX) + `assets_shotlist.csv` (liste médias à produire). PAS DE CODE.""",
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
7. Logos paiement (CB, Mollie (Bancontact, iDEAL, Apple Pay), Alma, Apple Pay)
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
        "title": "Brief panier + checkout (Mollie déjà branché)",
        "summary": "Le panier et checkout Mollie sont déjà fonctionnels. Ce brief affine les règles business : franco de port, upsell, code promo, réassurance.",
        "prompt": """Tu es CRO lead e-commerce FR senior.

Le **panier drawer** et le **checkout Mollie** sont **déjà codés** dans le template Altiaro. Tu ne codes rien. Tu **brieffes les règles business** à appliquer.

**1. Règles panier**
- Franco de port à quel montant ? (par pays — FR, BE+LU, DE, NL, CH, UK)
- Upsell au panier : produit recommandé auto (cross-sell) ? Critères ?
- Code promo : lesquels proposer (WELCOME10, NEWSLETTER15), durée, seuil de panier min
- Cart abandonment : après combien de minutes déclencher email de rappel ?

**2. Messages de réassurance au checkout**
Pour [NICHE] cible senior — liste 5-8 messages clés :
- Livraison (délai précis, transporteur, suivi)
- Paiement sécurisé Mollie + 3DS
- Rétractation 14 jours
- Garantie 2 ans
- Service client (téléphone, email <2h)

**3. Méthodes de paiement visibles**
Quelles icônes afficher par défaut ? Ordre recommandé ?

**4. Top 5 causes d'abandon à éviter** sur cible senior, pour chaque une règle à appliquer.

**Livrable** : `cart_checkout_rules.md` (800-1200 mots) en check-list. Aucun code.""",
    },
    {
        "number": 22,
        "phase": "F",
        "title": "Brief éditorial blog (15 piliers + calendrier)",
        "summary": "Le blog est intégré au template. Ce brief livre la ligne éditoriale, 15 sujets piliers, le profil auteur E-E-A-T et le calendrier 90 jours.",
        "prompt": """Tu es rédacteur en chef e-commerce senior (ex-Notre Temps, ex-Silver Économie).

Le **blog** est **déjà intégré** dans le template Altiaro. Ta mission : livrer la **ligne éditoriale** et les **15 sujets piliers** à rédiger en priorité.

**1. Ligne éditoriale**
- 3 promesses du blog (pas de remplissage SEO)
- Ton (reprend voix de marque #7)
- 3 rubriques (ex: Guides pratiques, Avis d'experts, Témoignages)
- Persona type du lecteur

**2. 15 sujets piliers prioritaires** pour [NICHE]
| # | Titre | Cluster | Mot-clé | Intention | Volume/mois | Priorité |

Chaque titre : accroche sans clickbait, UNE question précise, commence par Comment/Quel/Pourquoi/Où/Combien.

**3. Calendrier 90 jours** (2 articles/semaine = 24 articles)
- Phase 1 (priorité max), Phase 2 (approfondissement), Phase 3 (longue traîne)

**4. E-E-A-T** : profil auteur (nom, photo, bio 80 mots, crédentials crédibles — médecin/ergothérapeute). Injecté en schema.

**Livrable** : `editorial_guidelines.md` + `pillar_articles.csv` (15 lignes) + `publishing_calendar.csv` (24 lignes) + `author_profile.md`. 1500-2000 mots MAX.""",
    },
    {
        "number": 23,
        "phase": "F",
        "title": "Brief contenu pages statiques (About, Contact, FAQ)",
        "summary": "Les pages About/Contact/FAQ/Legal sont dans le template. Ce brief livre le contenu : storytelling fondateur, 50 FAQ, coordonnées support, charte accessibilité.",
        "prompt": """Tu es content strategist e-commerce senior.

Les pages **About / Contact / FAQ / Accessibilité / Legal** sont **déjà présentes** dans le template (les docs légaux sont auto-injectés au hook #9). Ta mission : **écrire le contenu éditorial**.

**1. About (1000 mots)**
- Storytelling fondateur (reprend #7, amplifie)
- Équipe : 3-5 membres (nom, rôle, citation 20 mots, photo brief)
- 3 engagements mesurables (ex: SAV <2h ouvrées)
- Chiffres clés, mentions presse

**2. Contact**
- Email support + délai <2h ouvrées
- Téléphone (horaires)
- Formulaire : champs minimaux (nom, email, tél optionnel, motif dropdown 8-10 motifs, message)
- Confirmation post-envoi

**3. FAQ — 50 questions structurées** en 7 catégories (Livraison 8, Paiement 7, Produits 12 spécifiques à [NICHE], Retours 6, SAV 8, Compte 5, Engagement 4)
Format JSON :
`[{"category":"Livraison","q":"...","a":"..."}]`
Vraies questions de seniors/aidants, pas de questions marketing.

**4. Accessibilité**
Déclaration RGAA 4.1 (taille 18px, contraste AAA, navigation clavier) + référent accessibilité.

**Livrable** : `about.md` + `contact.md` + `faq.json` (50 items) + `accessibility_statement.md`. 2500-3500 mots MAX total.""",
    },
    {
        "number": 24,
        "phase": "F",
        "title": "Brief navigation (catégories, filtres, méga-menu)",
        "summary": "La navigation et la recherche sont dans le template. Ce brief définit l'arborescence catégories, filtres collection, méga-menu header et recherches populaires.",
        "prompt": """Tu es UX e-commerce senior.

La **navigation** et la **recherche interne** sont **déjà codées** dans le template Altiaro. Ta mission : livrer l'**architecture de l'information**.

**1. Arborescence catégories**
Pour [NICHE], 2 niveaux max :
- Niveau 1 : 4-6 catégories (nav principale)
- Niveau 2 : 3-6 sous-catégories par L1

Par catégorie : nom court (20 car max, KW SEO), slug, meta title, meta description, image hero brief.

**2. Filtres par page collection**
- Prix (slider, tranches)
- Caractéristiques spécifiques [NICHE] (ex fauteuils : nb moteurs, charge max, revêtement)
- Notes clients (3+, 4+, 5★)
- Disponibilité (en stock)

**3. Méga-menu header**
Si L1 > 4 catégories :
- Colonnes thématiques (max 3)
- Image d'ambiance + CTA collection phare
- Lien "Voir tous" en bas

**4. Recherches populaires par défaut** — 10 requêtes pré-affichées :
- 5 produits top volume
- 3 informationnelles ("comment choisir...")
- 2 offres ("promo", "soldes")

**5. Footer navigation** : colonnes (Marque / Aide / Légal / Réseaux)

**Livrable** : `ia_navigation.md` + `collection_filters.json` + `footer_links.md`. 1000-1500 mots MAX.""",
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

Livrable: 15 fichiers .md prêts import Altiaro Blog""",
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
10. A/B test infra: PostHog feature flags OU Altiaro Shogun/GemPages

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
3. Live social proof: "Emma de Nantes a commandé canne il y a 12 min" bas-gauche 45s → VRAI via webhook Altiaro orders/paid anonymisé prénom+ville, RGPD
4. Vu dans la presse: 6 logos cliquables modal article
5. Partenaires: 4 logos (asso, experts)
6. Compteur "+X familles équipées" scroll animé (DATA RÉELLE Altiaro count)
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
        "title": "Brevo 7 flows email + SMS complets",
        "summary": "Welcome, abandon panier, abandon navigation, post-achat, winback, review request, VIP. Copywriting complet 50 emails + 6 SMS en ton marque vouvoiement chaleureux.",
        "prompt": """Configure 7 flows Brevo avec COPYWRITING complet ton marque (vouvoiement, chaleureux, jamais infantilisant):

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
        "title": "Optimisation checkout Mollie (réduction abandon panier)",
        "summary": "Mollie est déjà branché. Ce brief identifie les leviers pour baisser le taux d'abandon panier (FR ~ 70%) : friction, trust signals, A/B tests prioritaires.",
        "prompt": """Tu es CRO senior (ex-Oui.sncf, ex-Vestiaire Collective).

**Mollie** est **déjà branché** comme PSP unique (CB, Bancontact, iDEAL, Apple Pay, Google Pay, virement B2B). Taxes/transport paramétrés au prompt #14. Ta mission : **optimiser le checkout** pour réduire l'abandon (moyenne FR ~ 70%).

**1. Audit friction (liste 10 frictions classiques e-commerce senior)**
Pour chaque friction, la règle à appliquer sur le checkout Altiaro :
- Obligation de créer compte ? (recommandation : guest checkout autorisé)
- Trop de champs ? (quelle liste minimale ?)
- Frais de port révélés tardivement ? (règle : afficher dès le panier)
- Pas de numéro téléphone support visible ?
- Process > 3 steps ?
- ...

**2. Trust signals à ajouter au checkout**
- Logos paiements acceptés + icône cadenas SSL
- Bandeau "Paiement 100% sécurisé Mollie"
- Note Trustpilot / Avis Vérifiés visible
- Mention satisfaction ou remboursé
- Promesse livraison (délai + transporteur)
- Politique retour visible en footer sticky

**3. Paiement 3x/4x sans frais**
Alma est-il pertinent pour [NICHE] ? (seuil 100€) — marge rognée vs conversion boostée. Alternatives : Younited Pay, Franfinance, Cofidis. Recommandation argumentée.

**4. 5 A/B tests prioritaires à lancer**
- Hypothèse, variation, métrique primaire, durée d'estimation
Exemples : "Déplacer le code promo de l'étape 2 à l'étape 1 → augmente perception de bonne affaire"

**5. KPIs de monitoring**
- Taux d'abandon panier global
- Taux d'abandon par étape (panier → adresse → paiement → confirmation)
- Taux de conversion par méthode de paiement
- Panier moyen par device

**Livrable** : `checkout_optimization.md` (1500-2000 mots MAX) avec sections priorisées P0/P1/P2 et backlog A/B tests en tableau.""",
    },
    # PHASE K — Service client
    {
        "number": 37,
        "phase": "K",
        "title": "Chatbot GPT multi-canal avec RAG",
        "summary": "Chatbot FastAPI + LLM (Claude/GPT) + RAG sur catalogue, FAQ, politiques, blog. Widget frontend + WhatsApp + Messenger + email. RGPD opt-in. Escalade humaine auto. Dashboard admin.",
        "prompt": """Chatbot IA intégré:

Stack: Backend FastAPI /api/chat streaming SSE, LLM GPT-4o-mini OU Claude Haiku via Emergent LLM Key, RAG vector store (Chroma/Qdrant) sur catalogue Altiaro + FAQ 50Q + politiques + articles blog (chunking 500 tokens). Session memory 10 msg. RGPD opt-in, purge 90j, export/delete rights.

Frontend: widget bouton flottant bas-droit, modal chat élégant, typography accessibility 18px, suggested prompts initiaux, indicateur typing + streaming.

Capacités: qualification besoin 5Q max, reco produit avec lien+image, explication politiques, suivi commande Altiaro (session email+order), escalade humaine (détection frustration OU hors périmètre) → Gorgias avec contexte.

Canaux phase 2: WhatsApp Business Twilio/360dialog, Messenger + IG DM, email auto-reply support@ (GPT pré-remplit, humain valide).

Ton: vouvoiement, phrases <20 mots, empathique, offrir alternative humaine. Interdits: "ma petite dame", "c'est facile", jugement.

Dashboard admin: conversations récentes, KPIs (volume, taux escalade, satisfaction thumbs), topics émergents, conversations à review.

Livrable: backend + Chat.tsx + system_prompt.md + RAG pipeline + dashboard""",
    },
    {
        "number": 38,
        "phase": "K",
        "title": "Helpdesk centralisé + 30 macros",
        "summary": "Gorgias centralise email/chat/WhatsApp/Messenger/IG/téléphone. Règles auto-tag ML, priorités, SLA <2h, intégration Altiaro fiche client, 30 macros pré-écrites, dashboard KPI.",
        "prompt": """Setup Gorgias (recommandé e-commerce Altiaro):

Centralisation canaux: support@ email, chat site (hand-off bot prompt 37), WhatsApp Business (Twilio/WATI 20€/mois), Messenger+IG DM, téléphone Aircall transcription auto.

Configuration:
1. Règles auto-tag par motif (ML Gorgias): livraison/SAV/avant-vente/paiement/facture/retour/garantie/compte/autre
2. Priorités auto: P1 VIP/réclamation forte, P2 avant-vente, P3 info
3. SLA: 1ère réponse <2h jour (9h-19h LS), <24h hors
4. Intégration Altiaro: fiche client dans conversation (commandes, AOV, tags)
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
        "summary": "Aircall/Ringover numéro FR 01/09, menu vocal chaleureux, 9h-19h L-S, enregistrement RGPD, intégration Altiaro, 3 scripts (vente entrante, SAV, rappel lead).",
        "prompt": """Setup téléphonie pro:

1. Numéro FR fixe virtuel: Aircall (30€/mois), Ringover (20€/mois), Onoff Business. Numéro 01 Paris ou 09 dédié (PAS 06). Enregistrement avec annonce RGPD obligatoire.
2. Menu vocal humain court:
"Bonjour, bienvenue chez [NOM]. Pour suivi commande, tapez 1. Conseil avant achat, tapez 2. Autre demande, restez en ligne. Décrochage <1 minute."
3. Horaires 9h-19h L-S (samedi critique seniors retraités) + renvoi répondeur promesse rappel <2h (SLA)
4. Intégration Altiaro: pop fiche client Aircall au décroché (nom, dernière cmd, historique)
5. Logging: appels → Altiaro customer notes + Gorgias transcription

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
        "summary": "Backend webhook Altiaro + AfterShip/Track123, frontend page /suivi-commande timeline 7 étapes, estimation dynamique, photos preuve, notifications email+SMS, anti-où-est-mon-colis.",
        "prompt": """Module tracking post-achat:

Backend:
- Webhook Altiaro orders/fulfilled → stock n° tracking + carrier
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

Livrable: /api/tracking/* + Suivi.tsx + Brevo transactional templates""",
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
- Motif "changement d'avis" (14j rétractation): étiquette prépayée auto (Sendcloud, ShippyPro, Altiaro Returns), email instructions, remboursement auto dès scan retour 3PL
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

1. Merchant Center setup: flow Altiaro via app Google & YouTube Channel, GTIN ou MPN obligatoire, images ≥800×800, titres <150 car. (KW+brand+attribut), descriptions ≥250 car., catégorie Google précise. Fix disapprovals prioritaire.

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

6. Remarketing Display: audiences Altiaro (all visitors 30j, product viewers 30j, cart abandoners 14j), bannières responsives + 6 visuels produit top, cap fréquence 3/j/user

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
        "summary": "GTM Web+Server, GA4 events ecommerce, Consent Mode v2 CNIL, Enhanced Conversions, Meta CAPI, Altiaro Pixel custom, backend FastAPI tracking, tests DebugView/Tag Assistant/Events Manager.",
        "prompt": """Mesure AVANCÉE (perte signal iOS14 / Consent Mode v2):

1. Google Tag Manager Web + Server containers:
- Web GTM: events client-side GA4 + Google Ads enhanced conversions (email hash SHA-256)
- Server GTM: relai vers GA4 + Google Ads API + Meta CAPI + TikTok Events API + Pinterest

2. GA4 events ecommerce complets:
view_item_list, view_item, select_item, view_promotion, select_promotion, add_to_cart, remove_from_cart, view_cart, begin_checkout, add_shipping_info, add_payment_info, purchase (value/currency/tax/shipping/items[]), refund, sign_up, login, generate_lead, search (query)
Custom: phone_click, whatsapp_click, form_submit_lead, newsletter_signup, exit_intent_shown, chat_opened

3. Consent Mode v2 (obligatoire UE): bannière CNIL Cookiebot/Axeptio/Didomi, signaux ad_storage/analytics_storage/ad_user_data/ad_personalization, GTM conditionnel consent

4. Enhanced Conversions Google Ads: données hash (email, phone, name, address) client + offline upload backend long cycle

5. Meta CAPI (phase Meta Ads): backend FastAPI /api/tracking/meta reçoit webhook Altiaro order + emit event PurchaseserverSide event_id dédoublé côté pixel. Stape.io/Rudderstack simplifier (alt: native)

6. Altiaro Pixel custom: web pixel extension Altiaro manifest v3 capture events checkout

7. Backend FastAPI /app/backend/routes/analytics.py: POST webhook Altiaro orders/paid → push GA4 Measurement Protocol + Google Ads offline + Meta CAPI + TikTok + server log. Anti-tampering hash. Event_id standard dédup client vs server.

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

Centralisation config: /config/brand.config.ts unique avec Brand (name, tagline, manifesto, storyteller bio), Visual (colors CSS vars, fonts Google imports, logos URLs), Products (catégories, hero, USPs), Legal (entité, SIRET, adresse, DPO), Integrations (Altiaro domain, Brevo list ID, GA4, Meta Pixel), Copy (20 textes fréquents), i18n (langues, default).

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
