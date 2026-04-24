# Guide Google Ads — Campagne manuelle pour Projet Fauteuil releveur

> Export généré pour **both** · pays cible **FR**  
> 5 campagnes · 5 groupes d'annonces · 100 mots-clés · ~75 headlines · ~20 descriptions

## 🚀 En 10 minutes, tu crées ta campagne manuellement

### Étape 1 — Installe Google Ads Editor

Télécharge [Google Ads Editor](https://ads.google.com/home/tools/ads-editor/) (gratuit, Mac/Windows).
Connecte-toi avec le compte Google Ads lié à ton entreprise.

### Étape 2 — Importe le CSV des mots-clés

1. **Compte → Comptes → Importer depuis un fichier**
2. Sélectionne `keywords.csv` (téléchargé depuis Altiaro)
3. Valide la correspondance des colonnes : Campaign, Ad group, Keyword, Match type, Max CPC — tout doit mapper automatiquement.
4. Clique **Étape suivante** → **Appliquer**. Les 5 campagnes et leurs groupes d'annonces sont créés d'un coup.

### Étape 3 — Importe le CSV des annonces RSA

1. Répète **Importer depuis un fichier** avec `ads.csv`.
2. Google Ads Editor reconnaît les colonnes Headline 1-15 et Description 1-4.
3. Les **Responsive Search Ads** sont créés dans chacun des 5 groupes. Pas besoin de les retaper.

### Étape 4 — Paramètres de campagne

Pour chaque campagne nouvellement importée :

- **Pays ciblé** : 🇫🇷/🇩🇪/etc. selon la campagne (voir le nom, Altiaro t'a rangé par intent pas par pays ; duplique et ajuste si besoin)
- **Budget quotidien** : démarre à **10 €/jour** par campagne (5×10 = 50 €/jour total)
- **Enchères** : sélectionne **Maximiser les conversions** (même si tes conversions ne sont pas encore trackées ; on active le pixel à l'étape 5)
- **Appareils** : Desktop + Mobile + Tablet (pas d'exclusion pour l'instant)
- **Calendrier** : actif 24/7 (on affinera après 7 jours de données)

### Étape 5 — Active le pixel de conversion dans Altiaro

1. Dans Google Ads : **Outils & paramètres → Mesure → Conversions → Nouvelle action de conversion → Site web**
2. URL : l'URL de ton site Altiaro (ex. `https://toncustom-domain.com`)
3. Catégorie : **Achat**
4. Valeur : **Utiliser des valeurs différentes** (Altiaro envoie la vraie valeur de la commande)
5. Après création, Google affiche le **tag de suivi** :
   - `Identifiant de conversion` (format `AW-XXXXXXXXX`)
   - `Étiquette de conversion` (ex. `abc_defGhi`)
6. Retourne dans Altiaro : **Admin → Site → Google Ads**, colle ces deux valeurs, coche **Activer le pixel**, sauvegarde.
7. Le storefront d'Altiaro injecte automatiquement le `gtag.js` + `gtag('event','conversion',…)` au moment du purchase. Pas de dev à faire.

### Étape 6 — Publie tes campagnes

Dans Google Ads Editor, clique sur **Publier** en haut à droite.
Les campagnes passent en statut **Actif** dans les 5-10 min.
Bon launch 🎯

---

## 📁 Fichiers joints

- `keywords.csv` → format **Google Ads Editor** — headers exacts : Campaign, Ad group, Keyword, Match type, Max CPC
- `ads.csv` → format **Responsive Search Ads** — 15 headlines + 4 descriptions par groupe
- `guide.md` → ce document

## 🛒 Shopping — Feed produits Google Merchant Center

Le site expose un feed XML Merchant conforme :
- URL publique : `/api/sites/d33a5795-7a19-4a03-86a2-ef83ea19db9b/merchant-feed.xml` (si endpoint merchant existant)

Dans Merchant Center : **Produits → Flux → Créer un flux → URL planifiée** et colle l'URL ci-dessus. Une fois les produits approuvés, active la campagne Shopping dans Google Ads (elle utilisera automatiquement ce feed).