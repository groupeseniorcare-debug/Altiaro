# 🎯 PLAYBOOK V2 — E-commerce Drop-shipping Premium (Niche Seniors FR/EU)
## Méthodologie complète A→Z, 50 prompts séquentiels + étude marché concrète

> **Usage** : ouvrez une nouvelle session Emergent (ou Claude.ai / ChatGPT). Collez les prompts **dans l'ordre**. Chaque prompt est autonome, contextualisé, et produit un livrable concret (code React, copy, campagne, fournisseur, article SEO…).
>
> **Modèle** : drop-shipping unitaire pur. Commande client → commande fournisseur → livraison EU au client. **Aucun stock, aucune licence DM, aucun remboursement sécu** à gérer. Pour rester dans cette logique : **éviter tout produit marketé comme "médical"** (on dit "confort", "ergonomique", "senior", pas "médicalisé"/"anti-escarre" en frontal).
>
> **Stack** : Shopify (backend admin / checkout / paiement / commandes) + React custom headless (front SEO-first qui convertit). Duplicable en template multi-marques.
>
> **Budget** : 30€/jour Google Ads FR au départ. Conséquences directes (détaillées au Prompt 2) : on cible des produits à **CPC < 0,80€**, AOV **60–250€ majoritaire**, avec quelques hero-products **high-ticket 600–1800€** pour la marge.

---

## 📋 Sommaire

| Phase | Prompts | Livrable clé |
|---|---|---|
| **A** — Étude marché + research produits chiffrée | 1–4 | Matrice 30 produits avec volume/CPC/marge |
| **B** — Marque, positionnement, voix | 5–7 | Brand book complet |
| **C** — Sourcing Chine + EU (dropship direct) | 8–11 | Base 50 fournisseurs vérifiés |
| **D** — Cadre juridique minimal (drop légal FR) | 12–13 | Kit légal clé en main |
| **E** — Shopify backend | 14–16 | Boutique administrée |
| **F** — Front React headless (SEO + conversion) | 17–24 | Site ultra-performant |
| **G** — SEO technique de haut niveau | 25–29 | Top 3 Google sur 20 KW cibles |
| **H** — AEO / GEO (IA génératives) | 30–32 | Recommandé par ChatGPT/Perplexity |
| **I** — Conversion + social proof | 33–35 | CRO toolkit |
| **J** — Paiement haute conversion | 36 | Stripe + PayPal + Alma |
| **K** — Service client automatisé | 37–39 | Bot RAG + helpdesk + tél FR |
| **L** — Logistique drop + tracking | 40–42 | SLA livraison maîtrisé |
| **M** — Google Ads 30€/j performant | 43–46 | Premier ROAS 3+ |
| **N** — Analytics server-side | 47 | GA4 + CAPI + dashboard |
| **O** — Duplication framework | 48–50 | Template multi-niches |

---

# 📊 EXEMPLE CHIFFRÉ NICHE SENIORS (pour calibrer votre mental)

Ce tableau est un **APERÇU INDICATIF** pour vous montrer ce que produira le prompt 1. Les chiffres sont des estimations crédibles basées sur les patterns actuels (Keyword Planner + Ahrefs + SemRush FR). Vous devrez les confirmer avec un outil.

### Matrice produits — 15 candidats niche senior (dropship FR/EU)

| # | Produit FR | Vol. recherche /mois FR | CPC Google Ads (€) | Compétition SEO | Achat Chine (€) | Prix vente conseillé (€) | Marge brute | Note go |
|---|---|---:|---:|---|---:|---:|---:|:-:|
| 1 | Enfile-bas de contention | 2 900 | 0,45 | 🟢 Faible | 4 | 29 | 86% | ⭐⭐⭐ |
| 2 | Pince de préhension télescopique | 3 600 | 0,60 | 🟡 Modérée | 6 | 34 | 82% | ⭐⭐⭐ |
| 3 | Pilulier électronique hebdomadaire | 1 900 | 0,90 | 🟢 Faible | 12 | 49 | 76% | ⭐⭐⭐ |
| 4 | Chauffe-pieds électrique senior | 2 900 | 0,70 | 🟡 Modérée | 14 | 59 | 76% | ⭐⭐⭐ |
| 5 | Loupe éclairante LED lecture | 2 900 | 0,55 | 🟢 Faible | 8 | 39 | 79% | ⭐⭐⭐ |
| 6 | Veilleuse détection mouvement chemin | 880 | 0,40 | 🟢 Faible | 7 | 34 | 79% | ⭐⭐ |
| 7 | Réveil senior grands chiffres parlant | 1 000 | 0,65 | 🟡 Modérée | 11 | 49 | 77% | ⭐⭐ |
| 8 | Téléphone fixe grosses touches | 4 400 | 1,20 | 🟠 Élevée | 18 | 69 | 74% | ⭐⭐ |
| 9 | Canne pliante légère design | 5 400 | 0,85 | 🟡 Modérée | 13 | 59 | 78% | ⭐⭐⭐ |
| 10 | Canne-siège rétractable | 3 600 | 0,55 | 🟢 Faible | 22 | 89 | 75% | ⭐⭐⭐ |
| 11 | Rehausseur de WC avec accoudoirs | 4 400 | 0,95 | 🟡 Modérée | 19 | 79 | 76% | ⭐⭐ |
| 12 | Barre d'appui ventouses baignoire | 2 400 | 0,70 | 🟡 Modérée | 12 | 49 | 76% | ⭐⭐ |
| 13 | Coussin ergonomique assise auto | 2 100 | 0,80 | 🟡 Modérée | 16 | 69 | 77% | ⭐⭐ |
| 14 | Fauteuil releveur 2 moteurs tissu | 1 900 | 2,50 | 🟠 Élevée | 260 | 990 | 74% | ⭐⭐⭐ HERO |
| 15 | Lit électrique senior hauteur variable | 1 300 | 2,80 | 🟠 Élevée | 340 | 1 290 | 74% | ⭐⭐ HERO |

> 🎯 **Stratégie catalogue recommandée avec 30€/j ads** :
> - **20 produits mid-ticket 30-100€** (marge 75–85%, CPC faible, KW long-tail) → génèrent les premiers CA rapidement, valident l'UX, font tourner les avis, remplissent le catalogue pour SEO.
> - **5 produits high-ticket 600-1800€** (fauteuil releveur, lit senior, fauteuil massant, siège escalier portable, lève-personne léger) → tirent l'AOV. Sur ces produits, Google Ads est cher (CPC 2–4€) mais une seule vente couvre 15 jours de pub.
>
> Au global : **AOV visé ~140€** sur le mix, marge nette cible 25–30% post-pub/frais.

---

# PHASE A — ÉTUDE DE MARCHÉ & RECHERCHE PRODUIT CHIFFRÉE

## 🧠 PROMPT 1 — Matrice produits quantifiée (adaptable toute niche)

```
Tu es un expert en product research e-commerce drop-shipping. Je lance
une boutique Shopify FR/EU sur la NICHE SUIVANTE : [NICHE — ex :
"équipements de confort et d'autonomie pour seniors, PRODUITS NON
MÉDICAUX, maximum 20kg volumétrique"].

Mon budget Google Ads : 30€/jour. Donc je cible des produits dont le
CPC moyen FR < 1€ OU qui tolèrent un CPC 2-3€ par leur forte marge
absolue (> 400€ de marge brute unitaire).

Produis une MATRICE de 30 produits candidats répondant à TOUS ces
critères :

**Critères d'entrée** (chaque produit doit les cocher) :
- [ ] Pas classifié dispositif médical au sens MDR 2017/745 UE
- [ ] Dispo en dropship (Alibaba/AliExpress/CJ/Zendrop/Spocket/BigBuy)
- [ ] Poids < 20kg, colis < 150×60×60cm (dropship aérien faisable)
- [ ] Marge brute ≥ 70% minimum à la revente
- [ ] Fabrication pas interdite import EU (pas de piles lithium >100Wh
      non conformes, pas de radiofréquences illégales, pas de laser > classe 2)

Pour CHAQUE produit, donne :

| Colonne | Description |
|---|---|
| Nom produit FR (commercial) | Nom rassurant, benefit-first |
| Mot-clé principal FR | Le mot-clé d'intention d'achat le plus tapé |
| Volume recherche Google FR /mois | Estimation réaliste (cite ta source) |
| Volume longue-traîne associée | Somme des 5-10 variantes |
| CPC moyen Google Ads FR (€) | Estimation Keyword Planner |
| Compétition SEO (🟢/🟡/🟠/🔴) | Basée sur les 10 premiers résultats |
| Difficulté ranking (KD /100) | Estimation Ahrefs-style |
| Prix d'achat Chine fourchette (€ FOB) | Sur Alibaba 1 unité + port |
| Prix d'achat EU fourchette (€) | Si dispo en entrepôt EU (CJ, BigBuy) |
| Prix de vente marché FR (€ médian) | Ce que vendent les concurrents |
| Prix de vente RECOMMANDÉ (€) | Optimum conversion × marge |
| Marge brute % | (PV - PA) / PV |
| Marge brute absolue (€) | Cash généré par vente |
| LTV potentielle (€) | Cross-sell possible ? |
| Saisonnalité (mois pic) | Google Trends FR |
| Angle marketing fort | Ex : "plus de chutes la nuit" pour une veilleuse |
| Visuel UGC faisable ? | O/N — crédibilité vidéo démo |
| Angle objection principale | Pourquoi le client n'achèterait pas |
| Score GO /10 | Synthèse |

Livre la matrice en tableau markdown + CSV téléchargeable.
Après la matrice, classe le TOP 10 en expliquant pourquoi chacun
correspond à mon budget 30€/j (CPA faisable vs marge absolue).
```

## 🧠 PROMPT 2 — Rentabilité & faisabilité Google Ads par produit

```
À partir de la matrice produits (prompt 1), calcule pour chaque
produit TOP 15 la **simulation de rentabilité Google Ads** à 30€/j
budget total (pas par produit) :

Pour chaque produit :
- Clics attendus /jour = 30 / CPC
- Conversion attendue % (senior shopping 1,2-2,5% typique
  mid-ticket / 0,5-1% high-ticket)
- CPA estimé = CPC / CR
- CA par jour attendu = clics × CR × PV
- Marge par jour = CA × marge% - 30 (coût pub)
- ROAS attendu = CA / Pub
- Break-even analysis : combien de jours avant d'être rentable ?
- Risque : le budget est-il suffisant pour générer 50 conversions/mois
  (seuil optim Google Ads Performance Max) ?

Classement final :
1. Produits "🚀 Acquisition-driver" (CA rapide, validation funnel) —
   les lancer EN PRIORITÉ en ads
2. Produits "💰 Cash-cow" (rentables mais besoin SEO/retargeting, pas
   Google Ads direct)
3. Produits "🏆 Hero-ticket" (1 vente = 15 jours de pub compensés)
4. Produits "❌ Non-viables à 30€/j" — à écarter

Recommandation finale : quels 5 produits lancer en jour 1 pour toucher
la 1ère vente le plus vite possible avec 30€/j ?

Livrable : roi_simulation.md + recommendations.md
```

## 🧠 PROMPT 3 — Analyse concurrentielle chirurgicale

```
Pour chacun des 5 produits prioritaires (prompt 2), réalise une
**analyse concurrentielle chirurgicale** :

Pour chaque produit :

1. **SERP Google FR** top 10 actuel :
   - URL, type (shop, marketplace, blog, comparatif)
   - Domain Rating estimé
   - Titre H1 / meta title
   - Prix affiché
   - Éléments de réassurance utilisés
   - Schema structured data visible
   - Trust signals (avis, logos, presse)
   - Angle de différenciation

2. **Google Shopping FR** :
   - Top 10 annonceurs sur la requête
   - Fourchette de prix
   - Note marchand moyenne
   - Images utilisées (format, lifestyle vs pack shot)

3. **Facebook Ads Library** : quelles créas tournent ? (statique, vidéo,
   UGC, durée de campagne, angle)

4. **Amazon FR** :
   - Top 5 produits BSR sur le terme
   - Nombre d'avis, note moyenne
   - Prix, variations
   - Bullet points clés

5. **GAPS identifiés** : 10 angles où je peux battre la concurrence
   sans budget massif (ex : vidéo UGC authentique FR, engagement
   livraison 48h, packaging premium, accompagnement téléphonique,
   SEO sur une question que personne ne traite…)

Livre en document structuré : competitive_analysis_[produit].md × 5
```

## 🧠 PROMPT 4 — Stratégie catalogue & phases de lancement

```
Synthèse finale de l'étude marché. Produis la **FEUILLE DE ROUTE
CATALOGUE** sur 90 jours :

**Phase 1 — Minimum Viable Catalogue (J1-15)**
- 5 produits prioritaires (prompt 2) + 10 accessoires complémentaires
  pour booster l'AOV via cross-sell
- Structuration en 2-3 collections SEO

**Phase 2 — Expansion (J15-45)**
- +15 produits mid-ticket
- 2 hero-products high-ticket
- Création de cocons SEO (collections dédiées + articles piliers)

**Phase 3 — Full-catalog (J45-90)**
- +30 produits
- Ouverture 2e collection / sous-niche
- Test produits exclusifs (négo marque privée prompt 10)

Pour chaque produit listé, précise :
- Priorité ranking
- Fournisseur cible (nom + plateforme)
- Canal d'acquisition principal (Google Ads / SEO / Retargeting / Email)
- Budget pub estimé
- Objectif CA mensuel post-J90

Livrable : catalog_roadmap.md + forecast_90j.xlsx
```

---

# PHASE B — MARQUE, POSITIONNEMENT, VOIX

## 🧠 PROMPT 5 — Nom de marque + domaine + INPI check

```
Je lance une boutique e-commerce premium niche [NICHE], cible FR puis
UE, avec ambition multi-niches dans le futur (groupe de marques).

Propose 15 NOMS DE MARQUE classés en 3 familles :

**A. Noms évocateurs français poétiques** (ex : "Séréna", "Aurélie Maison",
    "Douceline")
**B. Noms latins/italiens chaleureux** (ex : "Dolcimo", "Vivenda", "Nobilé")
**C. Noms "holding" évolutifs** pour devenir un groupe avec marques-filles
    (ex : "Groupe Luméa" → Luméa Confort, Luméa Mobilité, Luméa Nature…)

Pour chaque nom :
- Prononciation simple (1-3 syllabes idéal)
- Étymologie / signification
- Disponibilité probable .fr / .com / .eu (forte/moyenne/faible)
- Check INPI risque (classe 10 + 35 surtout)
- Check Instagram / TikTok handle probabilité dispo
- Test mémorisation (peut-on l'écrire après 5s d'oubli ?)
- Slogan associé 6 mots max
- 3 adjectifs d'ambiance

Finalise avec mon TOP 3 + justification + commandes à lancer
(acheter domaine, INPI dépôt 190€, handles sociaux).
```

## 🧠 PROMPT 6 — Identité visuelle complète (brand book)

```
La marque s'appelle [NOM]. Conçois un BRAND BOOK complet livrable en
fichier markdown + CSS variables prêt à coller dans /app/frontend/src/
styles/tokens.css.

1. **LOGO** (3 concepts textuels précis pour brief designer/IA)
2. **TYPOGRAPHIE**
   - Display (titles) : choisis 1 font non-générique (PAS Inter, Poppins,
     Roboto) — ex : Fraunces, DM Serif, Tenor Sans, Gambetta, Bricolage
     Grotesque, Canela, Cormorant, Instrument Serif
   - Body : font lisible 18px minimum (ex : Source Serif, Literata,
     Newsreader, Lora)
   - Justification du choix pour cible senior premium
3. **PALETTE COULEURS** (hex + usage)
   - Primaire signature (éviter bleu médical / violet AI-slop)
   - Secondaire chaleureuse
   - 3 neutres chauds
   - Accents validation / erreur désaturés
   - Dégradés si utilisés (bannir dégradés violet/rose AI classiques)
4. **SYSTÈME D'ESPACEMENT** (8pt grid + contextes généreux 2-3x mobile)
5. **RADIUS, SHADOWS, STROKES** adaptés au premium tangible
6. **DIRECTIONS PHOTO** (lifestyle seniors chaleureux, lumière naturelle,
   intergénérationnel, mains, intérieurs cosy — décris 10 photos types)
7. **ICONOGRAPHIE** (Lucide-react en stroke 1.5px ou Phosphor)
8. **PATTERNS & TEXTURES** (grain subtil, pas flat design générique)
9. **VARIABLES CSS** complètes prêtes à injecter
10. **3 PROMPTS MIDJOURNEY/IDEOGRAM** pour générer : hero page, photo
    équipe, pattern fond

Livrable : brand_book.md + design_tokens.css
```

## 🧠 PROMPT 7 — Voix de marque + manifesto + 20 accroches

```
Pour [NOM], définis :

1. **MANIFESTO** (120 mots) — émotionnel, humain, digne, parle de temps,
   de dignité, de beauté de l'avancée en âge. Placé sur la page À propos.

2. **VOIX DE MARQUE** (document 2 pages) :
   - Niveau de langue : **vouvoiement obligatoire**, registre courant-soutenu
   - 10 règles "On dit / On ne dit pas" (tableau)
     → "seniors", "nos aînés", "longévité" > "personnes âgées", "vieux"
     → "confort", "bien-être" > "prévention chute" (pas médical)
     → "accompagnement" > "assistance"
   - 15 mots-signature du lexique de marque
   - Exemples : email de bienvenue / push notif / message SAV

3. **20 ACCROCHES PUISSANTES** réutilisables (hero, meta, emails, ads) —
   toutes doivent respecter la voix, être testables A/B

4. **STORYTELLING FONDATEUR** (page À propos 450 mots) — histoire
   authentique et crédible (proche aidant, artisan, mission personnelle)

5. **MISSION STATEMENT** 1 phrase qui tient sur T-shirt

Livrable : brand_voice.md + manifesto.md + about_page_copy.md
```

---

# PHASE C — SOURCING FOURNISSEURS DROPSHIP

## 🧠 PROMPT 8 — Dossier sourcing 50 fournisseurs

```
Pour les 20 produits validés (prompts 1-4), je cherche le meilleur mix
fournisseurs DROPSHIP en 2026 : **délai < 10 jours client final**
idéalement, entrepôts EU priorité absolue sur le premium.

Produis un DOSSIER FOURNISSEURS 50 entrées réparties :

**A. Plateformes dropship avec entrepôt EU** (15 fournisseurs)
- CJ Dropshipping (entrepôts DE/CZ/FR)
- Spocket (EU suppliers filter)
- Zendrop (EU warehouse récent)
- BigBuy (grossiste ES, dropship API Shopify)
- Matterhorn Wholesale (PL)
- VidaXL B2B (NL)
- Syncee (base EU)
- Griffati (IT premium home)
- Eprolo (EU warehouse)
- BrandsDistribution (IT, premium)
Pour chacun : forces, tarifs, MOQ, integration Shopify, délais réels FR,
fiabilité (forums, Trustpilot), type de produits matchant ma niche.

**B. Alibaba/1688 pour négo marque privée OEM** (15 usines)
- Filtre Gold Supplier + Verified + Trade Assurance
- Filtre certifications CE + RoHS + REACH
- Filtre "in stock" + délais d'expédition aérien
- Pour chacun : nom, ville, URL Alibaba, MOQ OEM, produits phares

**C. Grossistes FR/EU accessibles en compte pro** (10 entreprises)
- Drive Medical (FR non-médical consumer)
- Herdegen (accessoires mobilité)
- Hermell (confort)
- Rupiani, Sofamed Pro (compte revendeur direct)
- Dropshipping France SAS
Conditions d'ouverture compte revendeur (SIRET + commande min).

**D. Agents sourcing privés** (10 contacts) pour scale futur
- HyperSKU, NicheDropshipping, EcomOps, Yun Express Agent,
  Easy China Warehouse
- Conditions (seuil de volume requis, commission, langues)

Livrable : suppliers_directory.md + suppliers_comparison.csv
```

## 🧠 PROMPT 9 — Protocole test & qualification fournisseur

```
Construis un **protocole qualification fournisseur** en 3 étapes :

**Étape 1 — Scoring on desk** (15 critères, grille /100)
- Ancienneté, certifications, réponse < 24h, fluidité anglais,
  conditions OEM, frais port transparents, délais réalistes,
  avis existants, conformité documentaire, politique retour…

**Étape 2 — Test commande échantillon**
- Commande 1 unité en payant la livraison normale dropship
- Timer délai réel de A à Z
- Ouvrir à 100% devant caméra (unboxing)
- Checklist : emballage, notice FR présente, odeur, finitions,
  conformité photo vs produit réel, sticker CE, fiche produit EN/FR

**Étape 3 — Test service après-vente**
- Provoquer un retour (motif "changement d'avis")
- Mesurer : délai réponse, prise en charge frais, délai refund

Scoring final /300. Seuil GO : 220+.

Livrable : supplier_qualification.md + scorecard.xlsx template
```

## 🧠 PROMPT 10 — Templates négociation multilingues + OEM marque privée

```
Génère 12 templates emails/WhatsApp prêts à envoyer :

1. Premier contact (demande catalogue)
2. Demande prix FOB + EXW + DDP (comparer incoterms)
3. Demande certifications CE + RoHS + REACH PDF
4. Demande entrepôt EU + délais dropship réels FR
5. Négociation dropship sans logo vendeur sur colis (critique !)
6. Demande OEM marque privée (logo sur produit + packaging)
7. Demande facture avec mon SIRET / TVA intracom (pour comptabilité)
8. Négo prix à 50 / 200 / 500 unités (paliers volume)
9. Paiement 30/70 balance avant shipping (jamais 100% upfront)
10. Refus fournisseur médiocre avec porte ouverte
11. Gestion défaut qualité (preuve photo/vidéo + remplacement)
12. Mise en pause partenariat (saisonnalité)

Chaque template en 3 versions :
- 🇫🇷 Français
- 🇬🇧 Anglais professionnel international
- 🇨🇳 Phrases-clés chinois simplifié + pinyin (WeChat)

Livrable : supplier_templates.md
```

## 🧠 PROMPT 11 — Passage en marque privée (quand ? comment ?)

```
Planifie la transition **dropship générique → marque privée OEM** :

Seuil de déclenchement : ~50-100 unités/mois de vente d'un produit.

Pour chaque produit phare de mon catalogue, détaille :

1. Choix du niveau de personnalisation
   - Niveau 1 : étiquette blanche + notice brandée (~+0,20€/unité)
   - Niveau 2 : logo embossé/brodé sur produit (~+0,50€)
   - Niveau 3 : packaging custom full brand (~+1-2€)
   - Niveau 4 : produit co-designed (+10-15% coût)

2. MOQ typique par niveau + risque stock immobilisé

3. Timeline production + transport (30-60 jours)

4. Check-list documents : bon de commande, PI (Proforma Invoice),
   BL (Bill of Lading), packing list, certificat origine,
   DDP vs FOB calcul.

5. Stockage : entrepôt 3PL EU avant expédition dropship depuis EU
   (transition vers stock propre avec fulfillment partenaire)

6. ROI break-even : à quelle quantité vendue par mois passer en OEM
   devient rentable ?

Livrable : oem_transition_playbook.md + breakeven_calculator.xlsx
```

---

# PHASE D — CADRE JURIDIQUE MINIMAL

## 🧠 PROMPT 12 — Cadre légal drop-shipping FR 2026 (simplifié)

```
Je lance un drop-shipping FR légal, ciblant particuliers FR + UE.
Produits grand public (pas dispositifs médicaux, pas alimentaire,
pas cosmétiques, pas enfants < 3 ans).

Synthétise le **cadre minimal obligatoire 2026** :

1. **STRUCTURE** — recommandation argumentée
   - Micro-entreprise jusqu'à 77 700€ CA (HT : 37 700€ services,
     77 700€ ventes) — simple, rapide, mais cap.
   - EURL/SASU quand dépassement ou pour crédibilité B2B
   - Comparatif cotisations/impôts/franchise TVA pour 2026

2. **TVA e-commerce**
   - Franchise en base (micro) jusqu'à ~91 900€ ventes FR
     + 36 800€ services en 2026
   - Au-delà : TVA 20% à collecter, reverser mensuel/trimestriel
   - OSS (One Stop Shop) pour ventes UE > 10 000€/an cumulés EU
   - IOSS si import directement livré depuis Chine au consommateur EU
     (obligatoire pour colis < 150€ depuis 2021) → **RÈGLE CLÉ DROPSHIP**

3. **Obligations drop-shipping spécifiques**
   - Loi Lemaire (2016) : être vendeur ostensible, pas d'anonymat
   - Responsabilité de plein droit du vendeur (art L221-15) : tu es
     responsable de la livraison devant le client, PAS le fournisseur
   - Information précontractuelle claire sur délais livraison
     (éviter "7 jours" si c'est 15 en réalité → DGCCRF)
   - Clause TVA douane transparente (qui paie ?)

4. **Éco-contributions**
   - DEEE (équipements élec) : Ecologic / Ecosystem (~0,30-2€/produit)
   - Éco-emballages : Citeo
   - Éco-mobilier si meubles (Eco-Mobilier)

5. **Marquage CE & conformité produit**
   - Responsabilité de l'importateur (toi si Chine direct) : vérifier
     marquage CE présent, documentation technique disponible,
     traduction notice FR
   - Impossible à ignorer : amendes DGCCRF

6. **Assurances** (Hiscox, AXA Pro, Simplis)
   - RC Pro minimum
   - RC Produit (responsabilité dommages causés par produit défectueux)

Livrable : legal_framework_dropship.md
```

## 🧠 PROMPT 13 — Documents légaux clé en main

```
Génère les 6 documents légaux complets pour [NOM_MARQUE] (SIRET
placeholder, domaine [DOMAINE]), clauses 2026 conformes, prêts à
intégrer en page :

1. **CGV B2C** — 25 articles minimum :
   - Identité vendeur + forme juridique + SIRET + RCS
   - Prix TTC, TVA incluse OU franchisée
   - Commande, paiement, moyens (CB, PayPal, Alma)
   - Livraison : délais précis, transporteurs, zones, frais
   - Clause drop-shipping transparente : produit expédié depuis EU/Chine
   - **Information douane IOSS** si import direct consommateur
   - Rétractation 14j (formulaire annexe I Code conso inclus)
   - Garantie légale conformité 2 ans + vices cachés
   - SAV process
   - Données personnelles RGPD
   - Médiation CE2C
   - Droit applicable + juridiction

2. **Mentions légales** — hébergeur, éditeur, directeur publication,
   RCS, TVA, DEEE, contact

3. **Politique confidentialité RGPD** — 6 finalités précises, durée,
   droits, DPO, transferts hors UE (Shopify US, Google US)

4. **Politique cookies** (bannière conforme CNIL + textes granulaires
   accept/refuse/paramétrer)

5. **Politique de rétractation** avec formulaire-type intégré

6. **Conditions d'utilisation** du programme fidélité / newsletter

Livrables : 6 fichiers .md + version HTML ready-to-paste Shopify pages.
```

---

# PHASE E — SHOPIFY BACKEND

## 🧠 PROMPT 14 — Configuration Shopify complète (backend-only)

```
J'ai un compte Shopify Basic. URL admin : [MON_SHOPIFY]. Usage
headless : Shopify reste BACKEND (produits, commandes, paiement,
checkout natif sécurisé) mais TOUT le front est React custom via
Storefront API.

Procédure pas-à-pas actionnable :

1. **Paramètres boutique**
   - Devise EUR, timezone Europe/Paris, poids kg
   - Adresse entreprise, contact, SIRET dans zone légale
   - Pages policies → y coller CGV/mentions/confidentialité/cookies
     (prompt 13)

2. **Taxes (clé en dropship!)**
   - Régime : franchise en base (pas de TVA) OU TVA 20% selon seuil
   - Registration OSS UE dès 10k€ ventes autres pays
   - Configuration IOSS si import direct Chine (obligatoire <150€)

3. **Zones livraison**
   - FR métropole : Colissimo Domicile sans signature / avec signature
   - FR DOM-TOM : Colissimo International (surcoût)
   - UE cible 6 pays (DE, BE, ES, IT, NL, PT) + 10 pays phase 2
   - Tarifs step-by-step par poids volumétrique (drop a frais variables)

4. **Paiements à activer**
   - Shopify Payments (CB, Apple/Google Pay, 3D Secure automatique)
   - PayPal Express Checkout
   - Alma 3x/4x sans frais (app)
   - Virement bancaire (B2B, différé)

5. **Localisation checkout**
   - Langue FR + EN
   - Champ téléphone obligatoire (pour tracking logistique)
   - Préselection FR par défaut + IP-based country detection

6. **Créer Custom App privée** :
   - Admin API scopes : read/write products, orders, inventory, customers
   - Storefront API scopes : unauthenticated_read_*
   - Tokens → stocker dans /app/backend/.env sous SHOPIFY_ADMIN_TOKEN
     et /app/frontend/.env sous VITE_SHOPIFY_STOREFRONT_TOKEN

7. **Webhooks** à configurer sur backend FastAPI endpoint /api/webhooks/shopify
   - orders/create, orders/paid, orders/fulfilled, orders/cancelled
   - customers/create, inventory_levels/update
   - HMAC verification obligatoire (code fourni)

8. **Emails transactionnels** : customiser template Shopify (header logo,
   couleurs, signature) pour cohérence marque

Livrable : shopify_setup_checklist.md + /app/backend/routes/shopify_webhooks.py
```

## 🧠 PROMPT 15 — Import catalogue CSV haute qualité

```
Génère un CSV d'import Shopify complet pour les 20 produits prioritaires
(Phase 1 + 2 du catalog_roadmap, prompt 4).

Colonnes Shopify officielles respectées à 100% :
Handle, Title, Body (HTML), Vendor, Product Category, Type, Tags,
Published, Option1 Name/Value, Variant SKU, Variant Price,
Variant Compare At Price, Variant Inventory Qty, Image Src, Image Alt,
SEO Title, SEO Description, Variant Barcode (EAN si dispo).

Pour chaque produit, rédige :
- **Handle SEO** (URL kebab-case)
- **Title** ≤ 65 car. (mot-clé principal + bénéfice émotionnel)
- **Body HTML riche** 700+ mots structuré :
  • Paragraphe d'ouverture émotionnel (100 mots)
  • Liste 5 bénéfices clés (icônes texte)
  • Section "Pour qui est fait ce produit ?" (persona)
  • Tableau spécifications techniques (HTML table)
  • Section "Dans votre colis" (contenu exact)
  • Section "Notre engagement [NOM_MARQUE]" (livraison, garantie,
    SAV FR, essai 30j)
  • FAQ 5 questions avec réponses rassurantes
  • Bloc "Pourquoi nous font-ils confiance ?" témoignages courts
  • Note légale CE + conformité
- **Variantes** : coloris/tailles avec SKU structurés (ex : ABC-RGE-L)
- **Prix** + Prix comparatif barré (ancrage psycho)
- **Meta title** 60 car. avec KW + brand + USP
- **Meta description** 155 car. avec bénéfice + CTA + emoji discret
- **Tags** 15+ pour SEO interne + filtres + upsell
- **Image Alt** descriptif riche (mot-clé + contexte)

Livrable : shopify_products_import.csv + preview_product_exemple.html
```

## 🧠 PROMPT 16 — Stack apps Shopify optimale drop-shipping

```
Installe et configure ces apps Shopify (procédures exactes) :

**Essentielles (gratuit ou low cost)**
1. **DSers** — sync AliExpress automatique, fulfillment 1-click
2. **Judge.me** — avis produits + photos + sync Google Shopping
3. **Alma** — paiement 3x/4x sans frais FR (conversion +30%)
4. **Klaviyo** — email + SMS flows (voir prompt 35)
5. **Shopify Flow** natif — automatisations règles (tag VIP, alertes)

**Phase scale**
6. **Loox** — complément Judge.me avec photos aspirationnelles
7. **ReConvert** — upsell post-achat page remerciement
8. **Zipify OCU** — one-click-upsell pre-checkout
9. **Gorgias** — helpdesk tout-en-un (>20 tickets/j)
10. **Langify** — traductions DE/ES/IT pour UE expansion

**Shopping feeds**
11. **Google & YouTube Channel** — sync produits → Merchant Center
12. **Meta Channel** — catalog Facebook/Instagram Shop

Pour chaque app :
- Plan recommandé + coût mensuel
- Étapes installation
- Paramétrage exact (champs, flux, triggers)
- Intégration avec le front React custom si applicable
- KPI à surveiller

Livrable : shopify_apps_stack.md
```

---

# PHASE F — FRONT REACT HEADLESS (SEO + CONVERSION)

## 🧠 PROMPT 17 — Scaffold React + architecture headless

```
Crée l'app frontend React 18 headless connectée à Shopify.

**Stack technique** :
- Vite + React 18 + TypeScript strict
- React Router v7 (data router) + SSR light via vite-ssg OU Next.js 15
  App Router (si choisi, structure différente — me recommander le + SEO)
- TailwindCSS + shadcn/ui + Framer Motion + Lucide icons
- GraphQL client : graphql-request (léger) + @shopify/hydrogen-react types
- Forms : react-hook-form + zod validation
- State : Zustand pour cart + auth
- SEO : react-helmet-async + next-seo (si Next)

**Architecture /app/frontend/src/** :
/pages ou /app (routes)
  Home, Collection/[handle], Product/[handle], Blog, Blog/[slug],
  About, Contact, FAQ, Search, Legal/*, Admin/Dashboard

/components
  /layout (Header, AnnouncementBar, Footer, StickyCallout, Newsletter)
  /ui (shadcn)
  /product (Gallery, BuyBox, Options, Reviews, FAQ, CrossSell)
  /blocks (Hero, Benefits, Testimonials, TrustBadges, PressLogos,
           ComparisonTable, FAQAccordion, CTA, GuaranteeBlock, Story)
  /chat (ChatWidget)
  /a11y (AccessibilityPanel, ContrastToggle, FontSizeToggle)

/lib
  shopify.ts (GraphQL queries + mutations)
  analytics.ts (GA4 + Meta + TikTok + server-side)
  schemas.ts (JSON-LD generators)
  seo.ts (meta helpers)
  i18n.ts (FR par défaut, EN fallback, structure DE/ES)

/hooks (useCart, useProduct, useBlog, useReviews, useA11y)

/styles (tokens.css, globals.css)

**Exigences critiques non-négociables** :
- **Accessibilité AAA** : police base 18px, boutons ≥56px hauteur,
  contrastes WCAG AAA, focus ring visible gras, navigation clavier
  totale, aria-labels partout, skip-to-content
- **Perfs** : Lighthouse 95+ mobile sur tous les core, images WebP/AVIF
  lazy + blur placeholder, code-split par route, preload fonts, preconnect
- **SEO** : SSG/ISR sur toutes les pages publiques, sitemap dynamique,
  robots.txt, hreflang, canonical, schema partout (voir phase G)
- **Tracking** : events envoyés côté client + server-side (voir prompt 47)
- **Dark mode** : PAS AU LANCEMENT (senior = clair)

Livrable : scaffold complet + README install + .env.example + package.json
```

## 🧠 PROMPT 18 — Homepage conversion-first + hero vidéo

```
Code la HOMEPAGE de [NOM_MARQUE] — objectif : 5%+ des visiteurs
ajoutent au panier en 90 secondes.

Sections (1 composant par bloc avec data-testid unique) :

1. **AnnouncementBar** — "🛡️ Livraison OFFERTE en France | Conseil téléphone :
   01 XX XX XX XX" (texte défilant si plusieurs msgs)

2. **Header** sticky : logo + nav (5 items max) + search + account + cart
   (compteur animé) + bouton "Me faire rappeler" + accessibility panel

3. **Hero**
   - Vidéo background MP4 loop 10s compressée <2Mo (famille senior
     chaleureuse, lumière naturelle)
   - Overlay dégradé sombre bas → lisibilité
   - H1 émotionnel 10-12 mots ("Retrouver votre confort. Préserver votre autonomie.")
   - Sous-titre bénéfice (15-20 mots)
   - 2 CTA : primaire "Découvrir nos solutions" / secondaire
     "Être rappelé gratuitement"
   - Bandeau réassurance 4 icônes (Livraison incluse / Essai 30j /
     Garantie 2 ans / Conseil FR 7j/7)

4. **Section "Pour qui ?"** — 3 cards persona (Sérénité à domicile /
   Convalescence active / Accompagnement d'un proche) — image +
   titre + 2 phrases + CTA

5. **Produits phares** — carousel 6 produits + badges (Bestseller,
   Nouveau, -20%)

6. **Section social proof** — 4 témoignages vidéo (modal play) +
   note Trustpilot 4.8/5 + 6 logos presse ("Vu dans Notre Temps…")

7. **Section "Nos engagements"** — 4 piliers avec illustrations custom
   (SAV humain, Livraison soignée, Essai 30j, Choix ergothérapeute)

8. **Tableau comparatif** "Pourquoi [MARQUE] vs grande surface ?" —
   Prix, Accompagnement, Conseil, Retour, Installation, SAV

9. **Blog highlights** — 3 articles conseils (vers cluster SEO)

10. **Section fondateur** — photo + 100 mots histoire + signature

11. **FAQ accordéon** — 6 questions essentielles (livraison, SAV, retour…)

12. **Newsletter** avec **LEAD MAGNET** obligatoire : "Guide gratuit :
    10 équipements indispensables pour préserver son autonomie à domicile"
    (PDF 20 pages à prod par IA)

13. **Footer** riche 5 colonnes + Trustpilot widget + tous moyens
    paiement + accessibilité + certifs + tél GROS en footer mobile

**Animations** : fade-up staggered au scroll (Framer Motion), hover 3D
discret sur produits, transitions 250ms ease-out.

**PAS d'emoji** dans l'UI, iconographie Lucide 1.5 stroke.
**PAS de fond violet/pink AI-slop**.
**Photos réalistes** via Unsplash collections curated seniors (fournir URLs).

Livrable : Home.tsx + tous composants + screenshot de conception visuelle.
```

## 🧠 PROMPT 19 — Collection page SEO+UX optimisée

```
Code la page /collections/[handle] avec une structure SEO + conversion
optimale.

**Header collection** :
- Breadcrumb + schema BreadcrumbList
- H1 unique optimisé mot-clé primaire
- Intro 250 mots SEO pleinement visible (pas caché derrière "lire plus"
  au-dessus du fold — Google n'aime pas)
- Bandeau USP 3 items

**Sidebar filtres** (drawer mobile) :
Filtres fonctionnels (pas juste cosmétiques) :
- Prix (range slider)
- Options spécifiques produit (dynamic from Shopify tags)
- Disponibilité
- Note minimum étoiles
- Tri (pertinence, prix ↑, prix ↓, nouveautés, meilleures ventes, note)

**Grille produits** 3 cols desktop / 2 cols tablet / 1 col mobile
- ProductCard : image (hover = vidéo ou 2e photo), badge stock/offre,
  titre 2 lignes, note étoiles + count, prix + comparatif barré,
  mensualité Alma affichée, CTA "Voir"
- Lazy-load + pagination cliquable (PAS infinite scroll pur car mauvais
  SEO)
- URLs canoniques /collections/[handle]?page=2 + rel prev/next

**Bloc milieu de grille** (après 9 produits) : "Besoin de conseil ?
Appelez-nous" avec photo conseiller + formulaire rappel

**Section conseil SEO bas de page** (600 mots unique par collection) :
- H2 "Comment choisir votre [produit] ?"
- 4-5 paragraphes experts
- Liens internes vers articles blog pilier et satellite

**FAQ SEO bas** (6 Q/R, schema FAQPage JSON-LD)

**Cross-collection** : "Vous pourriez aussi aimer" (3 autres collections)

SEO technique :
- Meta title/description dynamiques
- Schema CollectionPage + ItemList + BreadcrumbList
- Canonical propre
- hreflang

Livrable : Collection.tsx + CollectionSEO.tsx + schemas prêts.
```

## 🧠 PROMPT 20 — Fiche produit (LA page cruciale)

```
Code /products/[handle] — page la plus importante, viser 5-8% de conversion.

**Layout 2 colonnes desktop / stack mobile** :

**Colonne gauche — Galerie** :
- 6-8 images HD + 2 vidéos intégrées
- Miniatures + zoom hover + full-screen modal
- Swipe mobile natif
- Badge "Démo vidéo disponible"

**Colonne droite — BuyBox (sticky desktop)** :
1. Fil d'ariane + H1
2. Étoiles Judge.me (cliquable → scroll to reviews) + count
3. Prix + comparatif barré + % économie + **mensualité Alma calculée
   dynamiquement** (ex : "ou 3× 263€ sans frais")
4. Sélecteurs variantes (coloris : swatches visuels 48px, taille : boutons)
5. Compteur stock temps réel ("En stock — expédition sous 24h")
6. **Bouton "AJOUTER AU PANIER"** XXL contraste AAA, hauteur 64px
7. Moyens paiement (logos CB, PayPal, Alma, Apple Pay)
8. Bloc réassurance 4 lignes avec icônes :
   - 🚚 Livraison offerte (France) en 5-10 jours
   - 🔄 Essai 30 jours satisfait ou remboursé
   - 🛡️ Garantie 2 ans fabricant
   - 📞 Conseil téléphonique 7j/7
9. **Bloc conseiller personnalisé** : photo Sophie + "Une question ?
   01 XX XX XX XX" + "Chatter avec Sophie"
10. **Simulateur livraison** : input code postal → date livraison
    exacte (via backend qui calcule selon transporteur + jours ouvrés)

**Dans le fold bas / sections longues** :
11. **Description longue 800 mots SEO** (storytelling + bénéfices +
    specs + cas d'usage) — H2/H3 structurés, **CE TEXTE EST TA PAGE
    SEO #1 pour ce produit**
12. **Vidéo immersion** "Chez Jeanne, 74 ans" 90s — usage réel client
13. **Comparatif avec 2 produits similaires** du site (upsell/downsell
    honnête)
14. **Spécifications techniques** (tableau)
15. **Contenu du colis** (avec photo unboxing)
16. **Notice PDF téléchargeable** + garantie + certificat CE
17. **Q&R produit communautaires** (formulaire ask a question + réponses
    précédentes)
18. **Avis clients Judge.me** intégrés + tri + photos + réponses marque
19. **FAQ produit** (10+ questions, schema FAQPage)
20. **Cross-sell "Souvent acheté ensemble"** (4 accessoires avec bundle
    -5% si panier >100€)
21. **Bloc social** "+2 347 familles équipées ce mois-ci"
22. **CTA final sticky mobile** "Ajouter au panier" barre basse
    toujours visible

**Schema.org Product complet** :
- name, description, image (array), sku, mpn, brand, gtin13, offers
  (price, priceCurrency, availability, url, itemCondition, shippingDetails,
  priceValidUntil), aggregateRating (ratingValue, reviewCount), review
  (array Person review), category
- FAQPage séparé pour la FAQ
- BreadcrumbList

**Micro-interactions** :
- Ajout panier → slide drawer + toast + animation cart count
- Exit-intent → modal "50€ de remise sur votre 1ère commande contre
  votre email" (1 fois par session)
- Scroll 60% → notif bas-gauche "Emma de Nantes vient de commander"
  (VRAI — basé sur webhooks orders/paid anonymisé)

**Accessibilité** : ALT images riches, aria-live stock, focus total clavier.

Livrable : Product.tsx + BuyBox.tsx + Gallery.tsx + CrossSell.tsx +
ReviewsModule.tsx + ProductSchema.tsx
```

## 🧠 PROMPT 21 — Cart drawer + checkout redirect Shopify

```
Construis le CartDrawer (slide-in right) :

- Liste produits : image, titre, options, qty +/-, prix, remove
- **Upsell 1 produit** recommandé (algorithme : produit top même
  collection)
- **Barre progressive livraison gratuite** ("Plus que 23€ pour la
  livraison offerte !")
- **Widget Alma** 3x calculé sur total
- Sous-total + total (livraison estimée)
- Code promo (avec validation Shopify Storefront API)
- **Bouton "Passer commande →"** qui redirige checkout.shopify.com
  via `checkoutCreate` mutation avec line items + customer email
  pré-rempli si connu
- Sticky footer mention "Paiement sécurisé SSL + 3D Secure"

**Persistance** : Zustand + localStorage + sync Storefront API
(reprise panier multi-devices via email).

**Tracking** : events add_to_cart, remove_from_cart, begin_checkout
(GA4 + Meta + server-side via backend proxy prompt 47).

Livrable : CartDrawer.tsx + hooks/useCart.ts + lib/shopify/cart.ts
```

## 🧠 PROMPT 22 — Blog + article template haute qualité SEO

```
Module BLOG complet :

**/blog** (listing)
- Grille articles (3 cols) avec catégories filter (Conseils, Santé,
  Témoignages, Guides d'achat, Actualité)
- Recherche full-text
- Sidebar : articles les + lus, newsletter inline, CTA produits
- Pagination

**/blog/[slug]** (article)
- Breadcrumb + schema
- H1 unique
- Meta auteur (photo + bio + diplôme) + date + temps lecture estimé
- **Table des matières sticky** (sidebar desktop, accordéon mobile)
- Contenu riche long format 2500+ mots :
  • H2/H3 hiérarchie claire
  • Paragraphes courts 3-4 phrases
  • Images landscape + portrait mix, toutes avec alt SEO
  • Vidéos YouTube intégrées (lite embed pour perf)
  • Callouts (info / warning / tip) distincts visuellement
  • Listes + tableaux comparatifs nombreux
  • Citations d'experts (ergothérapeute, gériatre)
  • Encadrés FAQ au milieu
  • **Liens internes contextuels** : 4-6 liens vers produits + 4-6
    vers autres articles (maillage cocon)
  • 2-3 liens externes haute autorité (INSEE, CNSA, AMELI, HAS)
  • **CTA produit natif** milieu + fin de contenu (pas banner intrusif —
    bloc intégré à l'écriture)
- **Schema Article + Author + Publisher** JSON-LD
- Bloc "Auteur" bas avec photo + bio crédible + LinkedIn
- 3 articles connexes + pagination rel prev/next cluster
- **Partage social** (natif Web Share API, pas de widgets tracker)
- Newsletter inline bas article

Source contenu : Shopify Blog API OU MDX + gitCMS (recommandation
argumentée : Shopify pour simplicité non-tech, MDX+Contentlayer pour
contrôle ultime SEO).

Livrable : /app/frontend/src/pages/Blog* + hooks/useBlog.ts
```

## 🧠 PROMPT 23 — Pages statiques (About, Contact, FAQ, Legal, Accessibilité)

```
Code les pages :

1. **/a-propos** — long storytelling (1000 mots), histoire fondateur,
   équipe (photos + rôles), valeurs, engagements mesurables, vidéo
   manifesto, chiffres clés (X clients équipés, Y avis 4.9/5), section
   presse

2. **/contact** — formulaire (nom, email, tél, motif dropdown, message)
   + alternatives (téléphone gros + chat + WhatsApp) + horaires + carte
   (si adresse physique) + FAQ ancre + bloc "Nous répondons en moins de 2h"

3. **/faq** — 50 questions par catégories (Livraison / Paiement /
   Produit / Retour / SAV / Compte / Fidélité) avec recherche instantanée
   + schema FAQPage sur toute la page (une FAQPage avec le max de mainEntity)

4. **Pages légales** (6 pages du prompt 13) — typographie lisible,
   table des matières, ancre par section

5. **/accessibilite** — déclaration RGAA + toggle panel
   (taille police +/-, contraste élevé, curseur XXL, interligne large,
   sans animations pour personnes sensibles) persistant en cookie

Bouton flottant bas-droit "Accessibilité" ouvrant le panel depuis toutes
les pages.

Livrables : 10 pages React + persistant A11y context.
```

## 🧠 PROMPT 24 — Recherche interne + suggestions

```
Composant Search avec :
- Input dans header + Cmd+K shortcut
- Modal plein écran avec résultats instantanés (300ms debounce)
- Suggestions tapant : produits (top match), collections, articles blog,
  FAQ
- Chaque résultat : image + titre + prix si produit + preview
- Historique de recherche (localStorage)
- "Recherches populaires" quand vide
- Source : Shopify predictive search API (fallback) + optionnel Algolia
  (phase scale si catalogue > 200 produits)
- Tracking search events (mots-clés vides = gold pour savoir ce qui manque
  au catalogue)

Livrable : SearchModal.tsx + hooks/useSearch.ts
```

---

# PHASE G — SEO TECHNIQUE DE HAUT NIVEAU

## 🧠 PROMPT 25 — Keyword research avancé + clusters thématiques

```
Réalise un AUDIT + KEYWORD RESEARCH poussé pour [NICHE] en FR, objectif
top 3 Google sur 20 KW prioritaires dans 6 mois.

Méthodologie demandée :

1. **Seed keywords** (10 termes racine)
2. **Expansion** : combiner avec modificateurs achat (meilleur, prix,
   avis, comparatif, pas cher, 2026, pour senior, pour mamie, cadeau),
   techniques (électrique, pliable, sans fil, ergonomique), et questions
   (comment choisir, quel, pourquoi)
3. **Sources** à consulter : Google Keyword Planner, Ahrefs, SemRush,
   Ubersuggest, Also Asked, AnswerThePublic, Google Suggest, People
   Also Ask, YouTube Suggest, Amazon Suggest, Reddit, Quora
4. **Scraping SERP** des 10 premiers résultats sur chaque KW pour
   identifier topical authority gap

Livrables :

**A. Master keyword sheet CSV** (400+ mots-clés) :
Colonnes : KW | Volume FR /mois | CPC | KD % | Intent
(info/commercial/transactional/nav) | Cluster | Pilier assigné |
Priorité 1/2/3 | Page cible URL | Status

**B. 12 clusters thématiques** regroupant chacun :
- 1 page pilier (2500+ mots, cible KW ultra head)
- 6-12 articles satellites (longue-traîne)
- 1-2 landing commerciales (collection + produit)
- 3-6 FAQ questions

**C. Topical authority map** — graphe visuel des relations entre pages
(quelle page link vers quelle page) en format .mermaid

**D. 20 KW prioritaires** — Phase 1 à trancher :
Critères : volume ≥ 500, KD ≤ 35, intent commercial/transactional,
produit au catalogue. Avec plan d'attaque page par page.

Livrables : keywords_master.csv + clusters_map.md + topical_graph.mermaid
```

## 🧠 PROMPT 26 — 15 articles piliers (3000 mots chacun, niveau expert)

```
Rédige les 15 premiers ARTICLES PILIERS du blog, qualité "skyscraper"
(objectif dépasser les 10 premiers résultats Google actuels en
profondeur + fraîcheur 2026).

Pour chaque article :

- **Titre SEO** 60 car. incluant année 2026 si relevant (boost CTR SERP)
- **Meta description** 155 car. value-packed + CTA
- **URL slug** optimisé
- **Structure obligatoire** :
  • Introduction hook (pain point + promesse + table matières)
  • Table des matières cliquable
  • 7-10 sections H2 structurées logiquement
  • Dans chaque section : H3 sous-découpe, paragraphes courts, 1-2
    visuels décrits
  • 2 tableaux comparatifs minimum (très apprécié SEO + lisibilité)
  • 1 FAQ en fin (5+ questions) → schema FAQPage
  • Conclusion actionnable + récap bullet points + CTA
  • Bloc auteur expert
- **Entités nommées** : citer marques concurrentes, institutions
  (CNSA, AMELI, HAS), pathologies (arthrose, arthrite — tangentielles),
  textes de loi si pertinents
- **Mots-clés LSI** 20+ naturellement intégrés
- **Data primary** : citer statistiques INSEE/Silver Eco (sourcer)
- **Interlinking** :
  • 5-7 liens vers articles satellites du même cluster
  • 2-3 liens vers produits/collections
  • 2-3 liens externes haute autorité (.gouv.fr, études, associations)
  • 1 lien vers article d'un AUTRE cluster (pour topical layering)
- **E-E-A-T** (Experience/Expertise/Authority/Trust) :
  • Signé par "Sophie M., ergothérapeute DE 10 ans d'expérience"
  • Date publication + dernière mise à jour
  • Bloc méthodologie transparent (comment on a sélectionné, testé…)
  • Schema Author + Publisher

Liste des 15 articles piliers à livrer (clusters 1-3) :
[à compléter selon prompt 25 résultat, exemples niche senior :]
1. "Canne de marche pliable : guide d'achat 2026 (comparatif 12 modèles)"
2. "Comment choisir une canne pour personne âgée : 7 critères essentiels"
3. "Rehausseur WC senior : guide complet (modèles, installation, aides)"
4. "Siège de douche pour senior : quel modèle pour quel besoin ?"
5. "Barre d'appui baignoire : installer sans percer (guide 2026)"
6. …

Livrable : 15 fichiers .md prêts import Shopify Blog
```

## 🧠 PROMPT 27 — 30 articles satellites + maillage interne intelligent

```
Rédige 30 ARTICLES SATELLITES longue-traîne (1000-1500 mots chacun),
reliés aux articles piliers via un maillage cocon sémantique.

Pour chaque satellite :
- Réponse ultra-focalisée à UNE intention précise longue-traîne
- Lien vers le pilier du cluster (2 liens minimum texte ancre varié)
- Lien vers 2 autres satellites voisins
- Lien vers 1-2 fiches produit contextuelles
- Schema Article + FAQPage si applicable
- Format : intro courte + sections H2 ciblées + FAQ fin

Exemples de sujets niche senior :
- "Canne de marche réglable en hauteur : pour qui ?"
- "Canne 4 pieds ou 1 pied : que choisir pour plus de stabilité ?"
- "Comment régler la hauteur d'une canne correctement ?"
- "Cadeau utile pour grand-mère de 80 ans : 15 idées qui font plaisir"
- "Peut-on prendre la voiture avec une canne pliable ?"
- "Accessoires pour canne de marche : embout, lanière, clochette"
- "Où acheter une canne de marche élégante en France ?"

→ Chaque satellite doit répondre PARFAITEMENT à sa requête, rien de
plus, rien de moins (principe d'intent match).

Livrable : 30 fichiers .md + internal_linking_map.xlsx (grille
LINK FROM × LINK TO avec ancres variées)
```

## 🧠 PROMPT 28 — Schemas JSON-LD exhaustifs + SEO technique

```
Implémente dans /app/frontend/src/lib/schemas.ts toutes les fonctions
générant du JSON-LD propre (une par type de page), injecté via
react-helmet-async.

Schemas à produire :

**Globaux (dans layout)**
- Organization (logo, url, sameAs socials, contactPoint tel/email)
- WebSite avec SearchAction (sitelinks searchbox dans SERP)

**Pages spécifiques**
- Home : WebPage + Organization
- Collection : CollectionPage + BreadcrumbList + ItemList (products)
- Product : Product complet (GTIN, MPN, brand, offers array, shipping
  details, merchant return policy, aggregateRating, review array max 5,
  additionalProperty pour specs) + BreadcrumbList
- Article blog : Article + Author(Person) + Publisher(Organization)
  + BreadcrumbList + FAQPage si présent
- FAQ globale : FAQPage avec 50+ mainEntity
- Contact/About : AboutPage / ContactPage + LocalBusiness si adresse
- Videos : VideoObject (contentUrl, thumbnail, uploadDate, duration)

Tests à automatiser :
- Validation Schema.org validator
- Rich Results Test Google
- Lighthouse SEO audit

**Autres optimisations SEO technique obligatoires** :
- sitemap.xml dynamique généré au build (inclut hreflang,
  lastmod, priority)
- robots.txt avec user-agents spécifiques (Googlebot, Bingbot,
  GPTBot, CCBot, Claude-Web, Perplexity-Bot, ChatGPT-User, AppleBot)
- Canonical sur chaque page (absolute URL)
- hreflang fr-FR par défaut + fr-BE, fr-CH, fr-LU quand expansion
- Preload fonts WOFF2 (max 2 poids/variables)
- Preconnect cdn.shopify.com, fonts.gstatic.com, cdn.judge.me
- Critical CSS inline pour above-the-fold
- Images WebP+AVIF avec srcset responsive 320/640/960/1280/1920
- Lazy loading natif + decoding=async
- Priority hints (fetchpriority="high" hero image)
- Web Vitals target : LCP <2.2s, INP <200ms, CLS <0.05
- Server push HTTP/2 ou Early Hints 103
- Cache-Control long sur assets statiques (1 an) avec hash

Livrable : /app/frontend/src/lib/schemas.ts + public/robots.txt +
vite-plugin-sitemap config + perfs_audit.md
```

## 🧠 PROMPT 29 — Stratégie netlinking FR 90 jours

```
Construis la stratégie NETLINKING :

**Objectif 90 jours** : 20-30 backlinks DR40+ ciblés.

**A. 30 sites FR prospects identifiés** (DR, thématique, type de lien visé) :
1. Blogs seniors (Notre Temps, Senior Actu, Les Enjoyeurs, Silver Planet)
2. Blogs aidants (Proche Aidant, Aidant.tv, Papa-Positive)
3. Associations (France Alzheimer, OldUp, Les Petits Frères des Pauvres)
4. Presse locale/régionale (rubriques santé, bien vieillir)
5. Annuaires qualitatifs (HOP!, Services à la personne gouv, Pro du grand âge)
6. Forums actifs (Caducée, Doctissimo sous-forums)
7. Partenaires complémentaires (podologues, ergos, SSIAD, téléassistance —
   échange de liens BtoB)

Pour chaque cible :
- URL contact + formulaire
- Nom rédac-chef si possible (LinkedIn)
- Pitch angle
- Template email personnalisable

**B. 4 tactiques d'acquisition** :
1. **Guest posts experts** (15 pitchs 500 mots "je vous propose un
   article gratuit signé par notre ergo diplômée sur [sujet])
2. **Digital PR / étude propriétaire** : commander un micro-sondage
   YouGov ou Opinea (2000-3000€) sur "Le top 10 des peurs des seniors
   à domicile 2026" → communiqué de presse → reprise presse naturelle
3. **Infographies shareables** : 5 infographies data-driven (+schema
   ImageObject) — envoi ciblé aux médias
4. **Partenariats associatifs** : échange visibilité (article invité +
   kit produits donné à association → article remerciement backlink)

**C. Calendrier 90 jours** semaine par semaine

**D. Toxic links monitoring** : audit mensuel Ahrefs/SEMrush, disavow
trimestriel si nécessaire

Livrable : backlinks_plan.md + 15 templates pitch emails + tracking_sheet.xlsx
```

---

# PHASE H — AEO / GEO (RÉFÉRENCEMENT DANS LES IA GÉNÉRATIVES)

> **C'est l'axe différenciant en 2026**. Les IA (ChatGPT, Perplexity,
> Claude, Gemini) captent 15-25% des recherches produits en France désormais.
> Apparaître dans leurs réponses = ventes directes + trafic bonus.

## 🧠 PROMPT 30 — Fondations AEO (Answer Engine Optimization)

```
Mon site doit être RECOMMANDÉ par ChatGPT (search), Perplexity, Gemini,
Claude et Bing Copilot quand un utilisateur demande "meilleur fauteuil
releveur 2026" ou "comparatif cannes pliables seniors".

Implémente les fondations AEO 2026 :

**1. Fichier `/llms.txt`** à la racine (standard proposé par Answer.AI,
adopté par Perplexity, Anthropic, Mistral) :

/app/frontend/public/llms.txt avec :
- Description de la marque en 3 phrases claires
- Liste curated des URLs les plus importantes (home, top collections,
  top articles piliers, FAQ, about, contact) chacune avec description
  1 phrase factuelle
- Bloc "Optional" listant politiques (retour, livraison, garantie)
- Version FR pour llms.txt + EN pour llms-en.txt

**2. Fichier `/llms-full.txt`** — version complète condensée de tout le
contenu du site en markdown optimisé LLM (génération automatique au
build via script Node).

**3. robots.txt** — explicitement AUTORISER les crawlers IA :
  User-agent: GPTBot (OpenAI)
  User-agent: ChatGPT-User
  User-agent: OAI-SearchBot
  User-agent: PerplexityBot
  User-agent: ClaudeBot
  User-agent: Claude-Web
  User-agent: anthropic-ai
  User-agent: Google-Extended (pour Gemini/Bard)
  User-agent: Bingbot (Copilot passe par là)
  User-agent: Applebot-Extended
  User-agent: Meta-ExternalAgent
  Allow: /

  ⚠️ Note : bloquer CCBot (Common Crawl) est un choix si tu ne veux
  pas entraîner de futurs modèles — à discuter (trade-off visibilité).

**4. Indexation Bing** obligatoire (ChatGPT Search + Copilot + DuckDuckGo
passent par Bing) :
- Bing Webmaster Tools signup + soumission sitemap
- Indexation IndexNow API push temps réel à chaque update contenu

**5. Schema.org maximaliste** (déjà prompt 28) — les IA adorent les
structured data pour extraire faits

Livrable : /public/llms.txt + /public/llms-full.txt (script généré) +
/public/robots.txt + backend script IndexNow auto-push
```

## 🧠 PROMPT 31 — Content AEO-optimisé (réponses extractables)

```
Adapte le style de contenu pour maximiser l'EXTRACTION par les IA :

**1. Format "Question → Réponse directe"** dans tous les articles :
- Chaque H2 peut commencer par une question
- Juste sous le H2 : réponse directe en 1-2 phrases (les IA citent
  ces phrases)
- Puis développement long pour SEO classique

**2. Listes + tableaux partout** : les IA extraient en priorité les
listes numérotées et tableaux comparatifs.

**3. Statistiques citables** : chaque article = 3-5 chiffres datés et
sourcés. Les IA aiment citer des faits vérifiables.

**4. Definitions encadrées** : encadré "Qu'est-ce que X ?" sur chaque
concept clé — extraction facile.

**5. Bloc "Réponse rapide"** en début d'article — 60 mots répondant à
l'intention principale. Les moteurs IA citent souvent ces résumés.

**6. Author E-E-A-T maximisé** :
- Bio auteur détaillée avec diplôme, années d'expérience, LinkedIn,
  affiliations professionnelles
- Schema Author complet (jobTitle, worksFor, alumniOf, knowsAbout[],
  url LinkedIn)
- Page /auteurs/[slug] avec bio complète et tous les articles signés

**7. Fraîcheur** : dates publication + dateModified visibles. IA adorent
le "2026", "mise à jour récente".

**8. Fact sheets produits** : page produit avec bloc "Faits en bref"
liste : poids, dimension, origine, garantie, certifications. Extraction
parfaite pour IA comparison queries.

**9. Mentions presse** : page /presse listant chaque mention citée
(URL, titre article, date). Les IA font de la vérification d'autorité.

**10. Wiki-style pour pages piliers** : structure encyclopédique
(définition, histoire, types, critères, utilisation) — Wikipedia is the
#1 source citée par les IA, mimer sa structure booste l'extraction.

Adapte les 15 articles piliers (prompt 26) à cette structure AEO.
Livrable : content_aeo_guidelines.md + articles piliers V2 adaptés.
```

## 🧠 PROMPT 32 — Présence hors-site pour AEO

```
Les IA **ne citent pas que ton site** — elles citent des sources
tierces qui te mentionnent. Stratégie d'ubiquité :

**1. Wikipedia / Wikidata** :
- Créer une entité Wikidata pour la marque (statut prudent : critères
  notoriété) et pour produits-catégorie dont on est expert
- Citer ta marque dans des articles Wikipedia pertinents (avec source
  fiable obligatoire → retour à digital PR prompt 29)

**2. Reddit / Forums** (trustés par LLM training) :
- Participer authentiquement à r/france, r/AideADomicile,
  r/GrandsParents, r/ParentingFr, forums Aufeminin, Doctissimo,
  Caducée, Forum Retraites
- Ton value-first, pas spammy ; signature discrète site
- Réponses longues et sourcées → citées par Perplexity

**3. YouTube** : créer 10 vidéos tutoriels courts ("Comment choisir...",
"Unboxing...", "Démo canne pliable") — Google/Gemini indexent les
transcripts et citent.

**4. Quora / ask.fm / Reddit AMAs** avec expert ergothérapeute — crée
des Q/A haute autorité citées par IA.

**5. GitHub "Awesome list"** ou data publics — si possible (ex : dataset
open de produits seniors) pour citation par LLM via fine-tune.

**6. Wiki-médias sectoriels** : Gérontopedia, Fairpedia, Agorasanté —
s'assurer que la marque est mentionnée dans les articles pertinents.

**7. Structured data marketplace** : Google Merchant Center avec infos
riches, Bing Merchant, Meta Commerce → les IA shopping les consultent.

**8. Interviews podcasts** du fondateur sur podcasts bien-vieillir (4-5
par an) — transcripts indexés.

**9. Communiqués de presse** avec schema.org NewsArticle sur sites
autorité (PRWeb, PRNewswire France, Presse-citron, Happyhours pour la FR).

**10. Tester régulièrement** :
- Demander à ChatGPT, Perplexity, Claude, Gemini "Quelles sont les
  meilleures boutiques en ligne pour [produit] en France ?"
- Tracker sur 30 jours l'évolution des mentions
- Outils de tracking AEO : Profound, Peec AI, Evertune, Otterly.AI

Livrable : aeo_offsite_strategy.md + monitoring_sheet.xlsx
```

---

# PHASE I — CONVERSION + SOCIAL PROOF

## 🧠 PROMPT 33 — CRO toolkit complet

```
Implémente le Conversion Rate Optimization toolkit :

1. **Exit-intent popup** desktop + scroll-up mobile : "Obtenez votre
   guide gratuit [NICHE]" contre email (lead magnet PDF). 1 fois/session.

2. **Sticky CTA bar mobile** : "Ajouter au panier" + "Appeler conseiller"

3. **Sticky conseiller widget** bas-droit avec photo + prénom + bouton
   "Me rappeler gratuitement" (form) + "Chatter" (chatbot prompt 37)

4. **Barre progressive livraison gratuite** (cart)

5. **Countdown expédition** ("Commandez dans 2h14 pour expédier
   aujourd'hui") basé horloge FR + cutoff 14h (authentique uniquement —
   pas de fake timer)

6. **Free shipping threshold optimizer** : calcul scientifique du seuil
   idéal (AOV actuel × 1,15 typiquement) + update automatique.

7. **Formulaire devis** pour commandes > 500€ (B2B, EHPAD, collectivités)

8. **Live chat** : Crisp free tier ou Tidio avec pré-qualification
   automatique (3 questions avant d'être routé au chatbot)

9. **Microsurvey** post-scroll 45s sur page produit : "Qu'est-ce qui
   vous retient ?" (5 choix + "autre"). Feed data product team.

10. **Test A/B infra** : PostHog feature flags OU Shopify Shogun /
    GemPages pour tester variantes landing sans code.

Plan de 20 tests A/B priorisés sur 6 mois (avec hypothèses chiffrées).

Livrable : CRO toolkit intégré + ab_test_roadmap.md
```

## 🧠 PROMPT 34 — Social proof multicouche (anti-AI slop)

```
Système de social proof authentique :

1. **Judge.me** intégré — avis produit + photos + réponses marque
2. **Trustpilot** widget homepage + footer (score réel)
3. **Live social proof** : notifications discrètes "Emma de Nantes a
   commandé une canne pliante il y a 12 min" bas-gauche 45s
   → VRAI via webhook Shopify orders/paid (anonymisé prénom + ville)
   → pas de données fictives, RGPD-compatible (affichage agrégé)
4. **Vu dans la presse** : 6 logos cliquables ouvrent modal avec article
5. **Partenaires** : 4 logos (associations, experts)
6. **Compteur "+ X familles équipées"** animé au scroll (basé data réelle
   Shopify orders count — pas inflaté)
7. **Note globale site** (agrégation Judge.me + Trustpilot)
8. **Vidéos témoignages** 4 clients réels (tourner soi-même ou
   commander UGC sur Bridge / Uprise France / Influee ~80€/vidéo)
9. **Case studies** longs formats sur blog : "Comment Jeanne a retrouvé
   sa mobilité" — 1 par mois
10. **Mur d'Instagram** (embed feed) montrant photos clients partagées
    (hashtag de marque)

Exigences anti-fake :
- Pas de génération IA d'avis (illégal + détectable)
- Pas de testimonials achetés sur Fiverr (destruction trust si découvert)
- Modération stricte : répondre à CHAQUE avis 1★-3★ publiquement avec
  empathie + solution

Livrable : social_proof_stack.md + composants React + workflow modération
```

## 🧠 PROMPT 35 — Klaviyo flows email + SMS (copywriting inclus)

```
Configure 7 flows Klaviyo avec COPYWRITING COMPLET ton de marque
[NOM_MARQUE] (vouvoiement, chaleureux, jamais infantilisant).

**FLOW 1 — Welcome series** (inscription newsletter, 4 touchpoints)
- Email 1 (instant) : bienvenue + guide PDF lead magnet + histoire marque
- Email 2 (J+2) : nos best-sellers (4 produits) + témoignage vidéo
- Email 3 (J+4) : offre -5% bienvenue code BIENVENUE5 exp 7j + urgency
- Email 4 (J+10) : contenu valeur "Nos 10 conseils pour X" (blog) +
  invitation à nous suivre Insta/Fb

**FLOW 2 — Abandon panier** (checkout_started sans purchase, 4 touches)
- SMS (2h) : "Votre article vous attend 🛒 [lien]"
- Email (4h) : visuel cart + réassurance + témoignage
- Email (24h) : -50€ si panier > 200€, -20€ si 100-200€
- Email (72h) : dernière chance deadline + FAQ produit

**FLOW 3 — Abandon navigation** (viewed_product sans add_to_cart, 1 touche)
- Email J+1 : "Cet article a retenu votre attention ?" + 4 avis +
  comparaison

**FLOW 4 — Post-achat** (order_placed)
- Email instant : confirmation + prochaines étapes clairs (livraison,
  installation)
- Email J+3 : "Votre colis arrive bientôt" + notice PDF + vidéo
  tutoriel usage
- Email J+7 : "Tout se passe bien ?" + demande avis Judge.me + produits
  complémentaires
- Email J+30 : entretien + accessoires + programme fidélité

**FLOW 5 — Winback** (customer_inactive 60j)
- Email 1 : "Vous nous avez manqué" + sondage (pourquoi)
- Email 2 (J+7) : -15% tout le site 48h
- Email 3 (J+14) : dernière tentative + bye message digne (unsub propre)

**FLOW 6 — Review request** (order delivered + 14j)
- Email demande avis Judge.me + Google
- Relance J+21 si pas répondu

**FLOW 7 — VIP** (LTV > 500€)
- Email accès "Cercle VIP" : avant-premières, remises perso, conseiller
  dédié

Segmentations clés :
- Prospect senior / Prospect aidant
- VIP / Fidèle / Occasionnel / Inactif
- Acheteurs catégorie X (pour cross-sell)

Pour chaque email : objet + preheader + copy body + CTA + visuel décrit
+ timing d'envoi optimal.

Livrable : klaviyo_flows.md (50+ pages) + templates_import.json
```

---

# PHASE J — PAIEMENT HAUTE CONVERSION

## 🧠 PROMPT 36 — Stack paiement FR optimale dropshipping

```
Configure le stack paiement complet :

**1. Shopify Payments** (Stripe sous-jacent)
- CB (Visa, Mastercard, Amex — Amex optionnel car frais élevés)
- Apple Pay, Google Pay
- 3D Secure v2 automatique dès 150€ (conformité PSD2)
- Descripteur bancaire clair = nom marque ("PAYPRO NOMMARQUE")

**2. PayPal Business**
- Express Checkout
- "Paiement en 4x sans frais" PayPal (30-2000€, automatique)
- Compte Business Pro (pas Standard — plus de features)

**3. Alma** (critique FR high-ticket)
- 3x et 4x sans frais jusqu'à 3000€ (pris en charge vendeur ~2,5%)
- 10x / 12x avec frais client possible
- Integration Shopify native + widget page produit + cart
- Déclenche +25 à +40% de conversion sur panier > 300€

**4. Virement bancaire** (B2B + grandes commandes)
- Manual — activé sur demande
- Délai validation commande 24-48h après réception
- Pour EHPAD, collectivités, entreprises

**5. Anti-fraude**
- Shopify Fraud Analysis activé
- Règle custom : review manuelle si order > 1500€ OU first order + email
  disposable detected OU billing ≠ shipping country
- Chargeback dispute kit (captures preuves tracking, IP, signature
  livraison si dispo)

**6. Facturation automatique**
- App Sufio ou Shopify Order Printer Pro
- Numéro de facture séquentiel inaltérable (obligation FR)
- PDF conformes : raison sociale, SIRET, TVA intracom, RCS, coordonnées
  client, détail TVA ventilée
- Envoi auto à chaque order paid

**7. Conformité DSP2** : 3DS challenge fluide, authentication strong
customer, tokenization

Livrable : payments_setup.md + conformity_checklist.md
```

---

# PHASE K — SERVICE CLIENT AUTOMATISÉ

## 🧠 PROMPT 37 — Chatbot GPT multi-canal avec RAG

```
Construis un chatbot IA intégré :

**Stack** :
- Backend FastAPI /api/chat (streaming SSE)
- LLM : GPT-4o-mini ou Claude Haiku 4.5 via Emergent LLM Key
- RAG vector store (Chroma/Qdrant) sur :
  - Catalogue produits (fetch Shopify Admin API quotidien + update webhook)
  - FAQ 50 questions
  - Politiques (CGV, retour, livraison)
  - Articles blog (chunking 500 tokens)
  - Base "aides financement" (contextuel senior)
- Session memory (last 10 messages) par cookie/localStorage
- RGPD : opt-in explicite, purge conversations 90j, export/delete rights

**Frontend** :
- Widget bouton flottant bas-droit
- Ouvre modal chat élégant
- Typography accessibility-ready (18px)
- Suggested prompts initiaux ("Quel produit pour... ?", "Où en est ma
  commande ?", "Comment retourner ?", "Parler à un humain")
- Indicateur typing + streaming réponse

**Capacités** :
- Qualification besoin (5 questions max)
- Recommandation produit avec lien + image
- Explication politiques (livraison, retour, garantie)
- Suivi commande : lecture live Shopify via session email + order number
  (sécurisé)
- Escalade humaine (détection sentiment frustration OR hors périmètre)
  → transfère vers Gorgias avec contexte complet de la conversation

**Canaux (phase 2)** :
- WhatsApp Business (Twilio WhatsApp API ou 360dialog)
- Messenger + Instagram DM (via Gorgias ou directe Meta)
- Email auto-reply sur support@[DOMAINE] (GPT pré-remplit la réponse
  qu'un humain valide/envoie)

**Ton** :
- Vouvoiement obligatoire
- Phrases courtes < 20 mots
- Empathique, patient, jamais condescendant
- Toujours offrir alternative humaine : "Préférez-vous qu'un conseiller
  vous rappelle ?"
- Interdictions : "bonjour ma petite dame", "c'est facile", "voyons",
  tout jugement

**Dashboard admin** :
- Conversations récentes
- KPIs : volume, taux d'escalade, satisfaction (thumbs up/down post-chat)
- Topics émergents (clustering NLP)
- Conversations à review (sentiment très négatif)

Livrable : backend + frontend Chat.tsx + system_prompt.md + RAG pipeline
(ingestion + retrieval) + dashboard admin
```

## 🧠 PROMPT 38 — Helpdesk centralisé + macros

```
Setup Gorgias (ou Front, ou Freshdesk — je recommande Gorgias car spécialisé
e-commerce Shopify) :

**Centralisation canaux** :
- support@[DOMAINE].fr
- Chat site (hand-off depuis chatbot prompt 37)
- WhatsApp Business (via Twilio ou WATI ~20€/mois)
- Messenger + Instagram DM
- Téléphone (via Aircall integration, transcription auto)

**Configuration** :
1. Règles auto-tag par motif (ML Gorgias) :
   livraison / SAV / avant-vente / paiement / facture / retour /
   garantie / compte / autre
2. Priorités auto : P1 (VIP / réclamation forte), P2 (avant-vente),
   P3 (info)
3. SLA : 1ère réponse < 2h en journée (9h-19h LS), < 24h hors
4. Intégration Shopify : fiche client visible dans la conversation
   (commandes, AOV, tags)
5. Macros pré-écrites (30) pour réponses standards
6. Auto-close tickets après 5 jours inactifs + relance CSAT (thumbs survey)
7. Escalade manager si tag "réclamation" ou CSAT 1-2/5

**Macros exemples** (rédiger complètement en ton marque) :
- Demande statut commande
- Retard livraison reconnu
- Procédure retour
- Produit défectueux reçu
- Changement d'adresse
- Demande facture
- Annulation commande
- Question éligibilité produit
- …30 total

**Dashboard KPI quotidien** :
- Volume tickets / agent
- Délai première réponse
- CSAT
- FCR (first contact resolution)
- Motifs top 5 (input pour FAQ/produit)

Livrable : gorgias_config.md + 30_macros.md + workflow_escalation.md
```

## 🧠 PROMPT 39 — Téléphonie FR + script vente senior

```
Setup téléphonie pro :

**1. Numéro FR fixe virtuel**
- Aircall (30€/mois) OU Ringover (20€/mois) OU Onoff Business (moins cher)
- Numéro 01 Paris OU 09 dédié (jamais de 06 pro)
- Enregistrement conversations (annonce RGPD obligatoire)

**2. Menu vocal humain court et chaleureux** :
"Bonjour, bienvenue chez [NOM]. Pour le suivi de votre commande,
tapez 1. Pour un conseil avant achat, tapez 2. Pour toute autre
demande, restez en ligne. Nous décrochons en moins d'une minute."

**3. Horaires** 9h-19h L-S (samedi critique pour seniors retraités
qui ont le temps) + renvoi répondeur avec promesse rappel < 2h (SLA)

**4. Intégration Shopify** : au décroché, pop fiche client Aircall
(nom, dernière commande, historique support)

**5. Logging** : tous les appels → Shopify customer notes via Aircall
integration + Gorgias (transcription)

**6. SCRIPTS** (livrer en 3 fichiers) :

A. **Script vente entrante** en 10 étapes :
- Accueil personnalisé (prénom si connu via CRM)
- Écoute active (laisser parler 2 min)
- Reformulation besoin
- Diagnostic par 3-5 questions (morphologie, usage, contraintes)
- Recommandation 2 produits (pas plus — paralysie choix)
- Traitement objection prix (valeur, paiement 3x, garantie)
- Traitement objection livraison/délai
- Closing doux (proposer commande ou "je vous renvoie le lien par SMS")
- Upsell léger si contexte
- Remerciement + rappel coordonnées

B. **Script SAV/litige** :
- Empathie (valider l'émotion avant de résoudre)
- Diagnostic clair
- Solution proposée (3 options si possible)
- Engagement délai concret
- Suivi automatique 48h après

C. **Script rappel lead** (formulaire "être rappelé") :
- Présentation + contexte ("vous avez demandé à être rappelé")
- Script vente entrante ensuite

Livrable : telephony_setup.md + 3 scripts complets + objections_book.md
```

---

# PHASE L — LOGISTIQUE DROPSHIP + TRACKING

## 🧠 PROMPT 40 — Chaîne logistique drop optimale

```
Définis la chaîne logistique drop-shipping :

**Phase 1 (lancement 0-10 cmd/j)** :
- Dropship direct depuis entrepôt EU (CJ EU, BigBuy, Matterhorn)
- Délai promis client : 5-10j FR, 7-14j UE (honnête ≠ "24h" faux)
- Packaging : expédition en packaging fournisseur (accepter)
  → NÉGOCIER : "ship without brand on box" pour éviter promotion
    fournisseur
- Insert carte remerciement perso (négo OEM niveau 1 avec fournisseur
  pour inclure ta carte PDF → impression locale + envoi stock tampon)

**Phase 2 (10-50 cmd/j)** :
- Stocker 20 unités top produits chez un 3PL EU (Byrd, Logsta, Eubrik,
  Salesupply)
- Expédition propre avec packaging brandé
- Délai client 2-4j (x2 conversion)

**Phase 3 (50+ cmd/j)** :
- Stock EU commandé en marque privée (prompt 11)
- 3PL premium (Byrd multi-pays, Shipmonk EU)
- Retours gérés par 3PL (portail client automatique)

**Transporteurs à négocier** (comptes pro volume) :
- Colissimo (petits colis ≤30kg)
- Chronopost (express premium)
- DPD Predict (créneaux 1h) — excellent pour seniors
- Mondial Relay (points relais économiques)
- UPS Standard EU
- GLS (rapport qualité/prix bon EU)
- Dachser, Geodis Calberson (palettes 50-500kg pour high-ticket)

Tarifs cibles négociables à 50 envois/mois : -15 à -25% vs tarif carte.

**Politique livraison affichée** (transparence totale) :
- Délai préparation 24-48h (expédié depuis EU)
- Délai transport estimé réaliste par transporteur
- Numéro de suivi envoyé sous 48h
- Signature requise si > 300€
- Refus de livraison = re-expédition frais client

**Process colis perdu / endommagé** :
- Réclamation ouverte transporteur immédiatement (J+8 sans scan)
- Client : soit renvoi gratuit immédiat (expérience), soit attend
  indemnisation — décider par valeur / LTV
- Documentation preuves (photos avant expé si stock propre)

Livrable : logistics_playbook.md + suppliers_SLAs.xlsx
```

## 🧠 PROMPT 41 — Module tracking client + notifications

```
Développe le module de tracking post-achat :

**Backend** :
- Webhook Shopify `orders/fulfilled` → stock numéro tracking + carrier
- Intégration AfterShip API (gratuit <100/mois) OU Track123 pour polling
  transporteurs multi-opérateurs
- Webhook AfterShip sur updates → update DB + trigger notifications

**Frontend** :
- Page /suivi-commande avec input (email + n° commande OU lien magique
  envoyé par email)
- Timeline visuelle 7 étapes custom :
  1. Commande reçue ✓
  2. Paiement validé ✓
  3. Préparation en cours ⏳
  4. Expédié depuis l'entrepôt
  5. En transit
  6. En tournée de livraison (aujourd'hui)
  7. Livré
  (si retour : 8. Retour initié / 9. Retour reçu / 10. Remboursement)
- Estimation livraison exacte (date) mise à jour dynamiquement
- Photos transporteur (si dispo via API Colissimo preuve livraison)

**Notifications automatiques** (email + SMS optionnel) :
- Confirmation commande (instant)
- Expédition (dès n° tracking)
- Sortie en tournée (jour J)
- Livré (confirmation)
- Exceptions :
  - Retard > 2j vs ETA → proactif "nous avons alerté le transporteur"
  - Adresse refusée → relance infos
  - Colis en souffrance point relais → reminder

**Anti-"où est mon colis ?"** : -60% de tickets SAV si tracking clair.

Livrable : /api/tracking/* endpoints + /suivi-commande.tsx + Klaviyo
transactional templates
```

## 🧠 PROMPT 42 — Portail retours + automatisation SAV

```
Portail retours client-friendly :

**Page /sav** :
1. Self-service :
   - Suivi commande (prompt 41)
   - Demander un retour (formulaire : commande, produit, motif dropdown,
     photos upload, demande : remboursement / échange / avoir)
   - Télécharger notice PDF / vidéo tutoriel
   - FAQ interactive avec recherche
   - Prendre RDV téléphone (Calendly embed)

**Backend automation** :
- Génération ticket Gorgias auto avec tag + priorité
- Si motif "changement d'avis" (14j rétractation) :
  → Étiquette retour prépayée générée automatiquement (Sendcloud,
    ShippyPro, Shopify Returns natif) + email avec instructions
  → Remboursement auto déclenché dès réception scan retour au 3PL
- Si motif "produit défectueux" :
  → Déclenche remboursement sans retour si < 80€ valeur (coût retour
    > valeur)
  → Au-dessus : étiquette retour + remplacement envoyé en parallèle
    (expérience wow)
- Si motif "je veux autre chose" :
  → Proposition échange automatique (email avec catalogue reco)

**Dashboard admin SAV** :
- Délai résolution moyen
- Taux retour par produit (détection produit défaillant)
- Coût SAV mensuel
- Motifs top 5 (input pour amélioration fiche/sourcing)

Livrable : /app/frontend/src/pages/Sav.tsx + backend automation +
Gorgias workflows + sav_dashboard.tsx
```

---

# PHASE M — ACQUISITION GOOGLE ADS (30€/J)

## 🧠 PROMPT 43 — Architecture Google Ads 30€/jour rentable

```
Budget 30€/jour = 900€/mois. Priorité : générer 1ère vente en < 30j
puis tuner le ROAS.

**Structure compte Google Ads** :

**1. Google Merchant Center setup**
- Flow produits Shopify (app Google & YouTube Channel)
- Obligations : GTIN ou MPN par produit, images ≥ 800×800, titres <150 car.
  optimisés (KW + brand + attribut), descriptions ≥ 250 car., catégorie
  Google précise
- Pièces supplémentaires : availability auto, shipping_rate rule FR,
  tax handling, promotions (si soldes/codes)
- Disapprovals à fixer en priorité (politique → politique produits
  approuvés)

**2. Répartition budget 30€/j** :

| Campagne | Type | % budget | €/j | Cible |
|---|---|---|---|---|
| 1 - Shopping Standard | Shopping priority HIGH | 40% | 12€ | Conv direct top KW |
| 2 - Performance Max | PMax | 20% | 6€ | Découverte + YouTube/Display |
| 3 - Search "haute intention" | Search | 30% | 9€ | Closer chauds |
| 4 - Remarketing | Display (RLSA) | 10% | 3€ | Panier + visiteurs |

> **Note stratégique** : commencer par Shopping Standard (pas PMax pur)
> car à 30€/j PMax n'a pas assez de data pour optimiser les bons signaux.
> Shopping Standard donne le CONTROL sur quels produits pushes.

**3. Campagne 1 — Shopping Standard** :
- Groupes par marge (subdivise produits par tag margin_high/mid/low)
- Bidding : Manual CPC au début (max CPC 0,80€ sur produits mid-ticket,
  1,50€ sur high-ticket), passage à Maximize conversions après
  30 conversions
- Audience signals : customer_list, visiteurs 30j, lookalike
- Exclure mobile si perfs mauvaises après 2 semaines (seniors achètent
  souvent sur ordinateur)

**4. Campagne 2 — PMax Retail** :
- Tous produits marge>70%
- Assets : 15 images lifestyle + 5 logos + vidéo 15s + 5 headlines +
  5 descriptions + audience signals
- Cible ROAS : 3.5 au début (permet apprentissage)

**5. Campagne 3 — Search (exact + phrase match)** :
- 4 groupes d'annonces par intention :
  • AG "Nom produit + variations" (exact)
  • AG "Meilleur / Avis + produit" (commercial)
  • AG "Concurrent" (ex : "tousergo avis", "sernup prix") — contestable mais efficace
  • AG "Acheter + produit" (transactional exact)
- 3 RSA par AG (headlines du prompt 44)
- Extensions : sitelinks (5), callouts (6), structured snippets (3),
  price extensions, lead form (rappel)
- Mots-clés négatifs initiaux : gratuit, occasion, leboncoin, location,
  définition, emploi, stage, bricolage, kijiji, solution d'urgence
- Conversions : purchase (priorité) + lead_submit + phone_click secondaires

**6. Campagne 4 — Remarketing Display** :
- Audiences Shopify : all visitors 30j / product viewers 30j /
  cart abandoners 14j
- Bannières responsive display + 6 visuels produit top
- Cap fréquence 3/jour/user (pas harceler)

**7. Tracking & conversions** (prompt 47 pour server-side) :
- Enhanced Conversions activées
- Value-based bidding après 50 conversions
- Conversion path modeling

Règles d'or :
- Aucune décision avant 3000€ dépensés OU 50 conversions
- Jamais couper une campagne en phase d'apprentissage (7j min)
- Tester 1 variable à la fois

Livrable : google_ads_structure.md + naming_convention.md + merchant_feed.md
```

## 🧠 PROMPT 44 — 100 headlines + 30 RSA optimisés

```
Rédige 100 HEADLINES (≤30 car.) + 50 DESCRIPTIONS (≤90 car.) + 20
SITELINKS + 10 CALLOUTS + 5 STRUCTURED SNIPPETS pour le compte Google
Ads [NOM_MARQUE] niche [NICHE].

Classement headlines en 5 familles :

**A. Produit+KW** (20 headlines) — "Canne Pliante Ultra Légère 279g",
"Fauteuil Releveur 2 Moteurs Tissu", etc.

**B. USP Marque** (20) — "Livraison Offerte en France", "Essai 30
Jours", "Conseil 7j/7", "Garantie 2 Ans", "Marque Française", etc.

**C. Bénéfice émotionnel** (20) — "Plus d'Autonomie à Domicile",
"Retrouvez Votre Confort", "Sérénité au Quotidien", "Rester Indépendant
Simplement", etc.

**D. Prix/Finance** (20) — "Dès 29€ Livraison Offerte", "Payez en 3x
Sans Frais", "Devis Gratuit", "-20% Ce Week-end", "Meilleur Prix
Garanti 30j", etc.

**E. Social Proof** (20) — "+2 000 Familles Équipées", "Note 4,8/5
sur Avis Vérifiés", "Recommandé par les Ergothérapeutes", etc.

→ Puis assemblage en 30 RSA (Responsive Search Ads) avec pinning stratégique
position 1 = famille B ou C (marque/bénéfice), position 2 = A (KW),
position 3 = D ou E (trust).

Sitelinks avec url + description 2 lignes ("Guide d'achat gratuit",
"Avis clients", "Livraison & retours", "Paiement 3x", "Nous contacter").

Callouts (25 car.) : "Livraison offerte", "Essai 30 jours", "SAV France",
"Paiement 3x", "Garantie 2 ans", "Conseiller dédié".

Structured snippets : Types (Pliante, Télescopique, Réglable…),
Brands, Features, Models.

Livrable : google_ads_copy.csv
```

## 🧠 PROMPT 45 — Landing pages ads (versions pub haute conversion)

```
Crée 5 LANDING PAGES dédiées campagnes Google Ads (différentes des
pages produit standard — ultra-focused CRO, pas de navigation) :

1. /lp/[KW-principal-1]
2. /lp/[KW-principal-2]
3. /lp/[KW-principal-3]
4. /lp/[KW-principal-4]
5. /lp/devis-gratuit (lead gen universal)

**Structure LP** :
- Header épuré : logo seul + numéro téléphone à droite (pas de nav !)
- Hero match exact au mot-clé (SKAG friendly) :
  H1 = "Le meilleur [produit] pour [situation]"
  Sous-titre = bénéfice clé
  Vidéo démo 30s (auto-play muted + controls)
  CTA primaire visible au fold
- Bandeau 4 réassurances icônes
- 3 produits pré-sélectionnés avec comparateur simplifié (prix,
  caractéristiques, CTA)
- Bloc "Comment ça marche ?" 3 étapes
- Bloc témoignages 3 avis clients réels + vidéo
- Bloc FAQ 6 questions
- CTA final + formulaire inline "Me faire rappeler gratuitement"
  (nom, tel, horaire souhaité) → envoie lead à Gorgias + SMS alerte
  + Google Ads conversion event
- Footer minimal : logo + mentions + téléphone

**Performance** : LP < 1.5s LCP, Lighthouse 99, mobile first.

**Tracking conversions** :
- GA4 event lead_submit / purchase
- Google Ads conversion upload avec valeur
- Meta CAPI event (retargeting futur)

**A/B tests prévus** : hero variant A (bénéfice) vs B (peur), CTA
color, prix showing vs hiding, etc.

Livrable : 5 fichiers LP React + tracking gtag.ts integration
```

## 🧠 PROMPT 46 — Plan d'optimisation ads 30-90j

```
Plan d'optimisation campagnes sur 90 jours pour ads 30€/j :

**Jours 1-14 — Phase d'apprentissage (ne rien couper)**
- Laisser tourner toutes les campagnes (sauf catastrophe)
- Monitoring quotidien basique (dépense, impressions, clics, CPC)
- Aucun ajustement budget/cible avant 7j
- Accumuler min 20 conversions pour décisions statistiques

**Jours 15-30 — Premier tuning**
- Analyse Search Terms → négatifs (viser -15% dépense inutile)
- Pause produits Shopping avec CTR <0,5% ET impressions >500
- Ajout audiences signals supplémentaires (custom intent, in-market)
- Première RSA headlines A/B
- Ajustement tranches horaires (ex : couper 23h-6h si pas conv)
- Activer RLSA (remarketing search)

**Jours 31-60 — Scale ce qui marche**
- Campagnes >ROAS 3 : budget +20% par semaine
- Shopping : segmentation par produit → "best sellers" en campaign
  priority HIGH, reste en MEDIUM
- Création d'annonces DSA (dynamic) pour catcher longue traîne
- Début de Meta Ads (prompt bonus) si Google ROAS stable à 3+

**Jours 61-90 — Maturation**
- Value-based bidding activé (max conversion value avec tROAS)
- Expansion vers UE (DE, ES, IT, BE) progressive
- Test YouTube Ads (skippable démo 30s, CPM bas) cohorte seniors
- Automation rules (alerts CPA >2x cible, budget pacing)
- Retargeting avancé par segment (abandon cart, product category viewer)

**Scripts Google Ads à déployer** :
- Script alerte spend inattendu (+30% jour)
- Script low-CTR ads auto-pause
- Script 404 detection (URL produit désactivée → pause annonce)
- Weekly report email automatique

**Reporting hebdomadaire** (Looker Studio template fourni) :
- Dépense, conversions, CPA, ROAS par campagne
- Top 10 mots-clés performants et 10 mauvais
- Évolution CR semaine/semaine
- Décisions prises, hypothèses pour S+1

Livrable : ads_optimization_playbook.md + scripts.js + weekly_report_template.md
```

---

# PHASE N — ANALYTICS & TRACKING

## 🧠 PROMPT 47 — GA4 + CAPI + server-side tracking

```
Implémente la mesure AVANCÉE (perte signal iOS14 / Consent Mode v2) :

**1. Google Tag Manager** (Web + Server containers)
- Web GTM : events client-side GA4 + Google Ads (enhanced conversions
  avec email hash SHA-256)
- Server GTM : relai vers GA4 + Google Ads API + Meta CAPI + TikTok
  Events API + Pinterest

**2. GA4 events ecommerce complets** :
- view_item_list, view_item, select_item, view_promotion, select_promotion
- add_to_cart, remove_from_cart, view_cart
- begin_checkout, add_shipping_info, add_payment_info
- purchase (value, currency, tax, shipping, items[])
- refund
- sign_up, login, generate_lead
- search (query)
- Custom events : phone_click, whatsapp_click, form_submit_lead,
  newsletter_signup, exit_intent_shown, chat_opened

**3. Consent Mode v2** (obligatoire UE 2024+)
- Bannière CNIL compliant (Cookiebot / Axeptio / Didomi)
- Signaux ad_storage, analytics_storage, ad_user_data, ad_personalization
- Tag Manager conditionnel sur consent

**4. Enhanced Conversions Google Ads**
- Données hash (email, phone, name, address) envoyés côté client
- + Offline upload conversions via backend pour orders long cycle

**5. Meta CAPI** (pour phase Meta Ads)
- Backend FastAPI endpoint /api/tracking/meta qui reçoit order webhook
  Shopify + emit event PurchaseserverSide avec event_id dédoublonné
  côté pixel
- Stape.io ou Rudderstack pour simplifier (alt : implémentation native)

**6. Shopify Pixel custom**
- Web pixel extension Shopify (manifest v3) pour capturer tous les events
  checkout (sinon perdus en headless)

**7. Backend FastAPI /app/backend/routes/analytics.py** :
- POST webhook Shopify orders/paid → push GA4 Measurement Protocol
  + Google Ads offline conversion + Meta CAPI + TikTok + server log
- Anti-tampering hash verification
- Event_id standard pour dédoublonner client vs server

**8. Tests obligatoires avant go-live** :
- GA4 DebugView : tous les events trigger corrects
- Google Tag Assistant : tags fire
- Meta Test Events : deduplication server-side check
- Search Console : données connectées à GA4

Livrable : /app/backend/routes/analytics.py + GTM container JSON
importable + /app/frontend/src/lib/analytics.ts + testing_checklist.md
```

---

# PHASE O — DUPLICATION FRAMEWORK

## 🧠 PROMPT 48 — Audit & monitoring SEO continu

```
Dashboard de monitoring SEO mensuel :

**Outils connectés** :
- Google Search Console (principal)
- Google Analytics 4
- Bing Webmaster Tools (AEO !)
- Ahrefs Webmaster Tools (gratuit : backlinks, top pages)
- PageSpeed Insights (Core Web Vitals)
- Screaming Frog (audit technique mensuel 500 URLs gratuit)

**Dashboard Looker Studio** 5 onglets :
- Overview : impressions, clics, CTR, positions moyenne
- Top pages : trafic SEO par page, évolution
- Top mots-clés : opportunités top 4-20 à booster vers top 3
- Backlinks : nouveaux, perdus, DR
- Technical health : indexation, core web vitals, erreurs 404,
  crawl budget

**Rituels SEO mensuels** :
- Audit technique Screaming Frog → fixer nouvelles issues
- Création 4 articles blog (2 piliers + 2 satellites)
- Relance 10 prospects netlinking
- Update 5 articles anciens (fraîcheur content)
- Monitoring positions top 30 KW (outil type SERPRobot 20€/mois)

**Alertes automatiques** :
- Baisse trafic > 20% semaine/semaine
- Pages désindexées soudaines
- Core Web Vitals passées en "Poor"
- Backlink toxique détecté (spam score > 80)

Livrable : seo_monitoring_stack.md + Looker template URL +
rituals_calendar.md
```

## 🧠 PROMPT 49 — Refactor en TEMPLATE multi-niches

```
Refactore le projet front+back pour devenir un TEMPLATE réutilisable
lançant une nouvelle niche en < 5 jours.

**Centralisation config** :
Fichier unique `/config/brand.config.ts` contenant :
- Brand : name, tagline, manifesto, storyteller bio
- Visual : colors (CSS vars), fonts (Google imports), logos URLs
- Products : catégories schema, hero products, USPs
- Legal : entité, SIRET, adresse, DPO contact
- Integrations : Shopify domain, Klaviyo list ID, GA4 ID, Meta Pixel…
- Copy : 20 textes fréquents (hero headline, bénéfices, reassurance…)
- i18n : langues actives, default locale

**Extraire composants niche-spécifiques** dans `/features/` optionnels :
- Senior : AccessibilityPanel, LargeText, SimulatorAPA (désactivable)
- Kids : GamificationBadge, ParentalControl
- Pro : QuoteBuilder, B2BPricing

**CLI `npm run create-brand`** (node script) :
- Prompt interactif : nom, niche, couleurs, fonts, domaine
- Génère /config/brand.config.ts
- Clone .env.example → .env à remplir
- Crée repo Git
- Deploy trigger Vercel/Emergent

**Documentation duplicable** :
- `/docs/duplication_sop.md` — workflow 20 étapes de niche validée à
  go-live
- `/docs/niche_checklist.md` — check-list produits : est-ce duplicable
  sur ma niche ?

Livrable : template complet + CLI + docs
```

## 🧠 PROMPT 50 — SOPs opérationnels + org scalable

```
Documente tous les SOPs pour faire tourner la marque + dupliquer :

**SOPs opérationnels** (Notion/GitBook) :
1. Sourcing produit (10 étapes validation fournisseur)
2. Rédaction fiche produit SEO+CRO (check-list 30 points)
3. Publication article blog (brief → rédac → SEO → pub → diffusion)
4. Gestion ticket SAV (arbres décision : remboursement, retour,
   échange, geste commercial)
5. Lancement campagne ads (brief créatif → prod → test → scale)
6. Revue hebdomadaire perf (agenda, data, décisions)
7. Moderation avis (quoi répondre à 1-2-3-4-5★)
8. Onboarding nouveau produit (7 jours de la découverte à live)
9. Gestion rupture stock fournisseur
10. Ouverture nouvelle niche (playbook 30j)

**Organigramme cible Mois 6** :
- Fondateur (toi) : stratégie, deal fournisseurs, finances
- VA FR SAV freelance (15h/semaine, 300€/mois)
- Media buyer freelance (5h/semaine, 500€/mois)
- Rédacteur SEO freelance (6 articles/mois, 600€)
- Graphiste/UGC freelance (à la mission, budget 300€/mois)
- Comptable (100€/mois)

Total charges op : ~1800€/mois = CA nécessaire 10-15k€ pour viable.

**3 scénarios de budget** mensuels (CA 10k / 30k / 100k) avec
réallocation ads + team + stock.

Livrable : sops_notion_export.md + org_chart.md + budgets_scenarios.xlsx
```

---

# 🎯 CHECKLIST DE LANCEMENT (avant 1ères pubs)

- [ ] Niche validée + 5 produits prioritaires sourcés + échantillons testés
- [ ] Marque : nom + domaine + INPI dépôt + logo + brand book
- [ ] Structure juridique créée (micro ou SASU) + IOSS numéro si drop Chine
- [ ] Shopify backend configuré + 20 produits en ligne
- [ ] Front React déployé + Lighthouse 95+ sur toutes pages
- [ ] Schema.org + llms.txt + robots.txt + sitemap OK (AEO ready)
- [ ] 15 articles piliers + 30 satellites publiés (plan 90j)
- [ ] CGV + mentions + RGPD + cookies intégrés
- [ ] Paiements testés (CB, PayPal, Alma) — 1 commande test réussie
- [ ] Klaviyo 7 flows activés
- [ ] Chatbot + Gorgias + téléphone FR opérationnels
- [ ] Tracking GA4 + CAPI + Enhanced conv testés en DebugView
- [ ] Google Merchant Center validé + feed approuvé 100% produits
- [ ] Google Ads 4 campagnes setup (en pause)
- [ ] Bing Webmaster + IndexNow configurés (AEO)
- [ ] 3 témoignages pré-lancement (beta testeurs proches)
- [ ] Stock tampon EU ou 3PL validé
- [ ] Assurance RC Pro + RC Produit souscrite

Puis : **activer Google Ads** et suivre le plan prompt 46.

---

# 🗓️ CALENDRIER RÉALISTE 60 JOURS → 1ÈRE VENTE

| Semaine | Actions principales | Prompts à exécuter |
|---|---|---|
| S1 | Étude marché + produits + concurrents | 1, 2, 3, 4 |
| S2 | Marque (nom + brand book + voix) | 5, 6, 7 |
| S2-3 | Sourcing + échantillons commandés | 8, 9, 10 |
| S3 | Juridique + structure | 12, 13 |
| S3 | Shopify backend + 20 produits | 14, 15, 16 |
| S4-5 | Front React (home, collection, produit, cart, blog, pages) | 17-24 |
| S4-5 | SEO recherche + 15 piliers + schemas + llms.txt | 25, 26, 28, 30, 31 |
| S5-6 | AEO + contenu satellite | 27, 32 |
| S5-6 | Conversion + social proof + Klaviyo | 33, 34, 35 |
| S6 | Paiements + service client | 36, 37, 38, 39 |
| S6-7 | Logistique + tracking + SAV | 40, 41, 42 |
| S7 | Google Ads structure + copy + LP + tracking | 43, 44, 45, 47 |
| S7 | Go-live ads 🚀 | — |
| S7-9 | Monitoring + optim + 1ère VENTE attendue | 46 |
| S9+ | Netlinking + AEO offsite + monitoring | 29, 32, 48 |
| Mois 3+ | Duplication framework + SOPs | 49, 50 |

---

# 💡 10 COMMANDEMENTS HIGH-PERFORMANCE

1. **Ne coupez JAMAIS une campagne ads avant 50 conv / 3000€ spend**.
   Vous détruirez le learning.

2. **La première vente dropship prend 20-45j avec 30€/j en mid-ticket**.
   C'est statistique, pas personnel.

3. **Priorité absolue : confiance** sur ce secteur. Un senior achète
   d'abord chez des humains, ensuite chez une marque, enfin par le prix.

4. **Documentez CHAQUE appel SAV** (transcription + notes). La mine d'or
   pour améliorer fiches, produits, sourcing.

5. **Répondez personnellement aux 100 premiers emails SAV**. Vous
   apprendrez plus en 2 semaines qu'en 6 mois d'analytics.

6. **Stock tampon** sur 3-5 produits top dès que les ventes dépassent
   20/mois. L'expérience de livraison rapide multiplie le LTV.

7. **AEO = edge 2026-2028**. Les marques qui structurent leur contenu
   pour les IA génératives prendront 6-12 mois d'avance sur les autres.

8. **Budget "casse" réserve** 1500-2500€ sur les 3 premiers mois : retours,
   produits défectueux, tests fournisseurs décevants. C'est normal.

9. **Ne clonez pas trop tôt**. Validez 1 niche à 10k€/mois AVANT de
   dupliquer. Le risque #1 est de diluer l'attention sur 3 stores zombie.

10. **Gardez une obsession qualité produit**. Le dropship mauvais tue
    une marque en 3 mois (avis 1★ + chargebacks + bad press).

---

# 📎 RESSOURCES EXTERNES CLÉS

**E-commerce FR** :
- FEVAD (fédération e-commerce) — https://fevad.com
- DGCCRF (contrôle conformité) — https://economie.gouv.fr/dgccrf
- Shopify Academy — https://shopify.com/academy

**Juridique drop** :
- Guichet entreprises — https://formalites.entreprises.gouv.fr
- TVA OSS/IOSS — https://impots.gouv.fr (espace pro)
- RGPD — https://cnil.fr

**Marketing & SEO** :
- Ahrefs blog — https://ahrefs.com/blog
- Backlinko — https://backlinko.com
- Google Skillshop (certifs Ads gratuits) — https://skillshop.withgoogle.com
- Search Engine Journal AEO — https://searchenginejournal.com/category/seo/aeo

**Senior market FR** :
- Silver Eco — https://silvereco.fr
- Silver Alliance — https://silveralliance.com
- INSEE démographie — https://insee.fr

**AEO monitoring** :
- Profound — https://tryprofound.com
- Peec AI — https://peec.ai
- Otterly.AI — https://otterly.ai

---

> ✅ **Ce document est votre roadmap complète.**
>
> À chaque nouvelle session Emergent : ouvrez ce fichier, collez le
> prompt suivant, intégrez le livrable dans votre projet, passez au
> suivant. En séquence, en 45-60 jours vous êtes prêt à encaisser.
>
> Bon lancement 🌿
