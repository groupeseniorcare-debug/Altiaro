"""Altiora platform-level legal pages (platform = Altiora SAS itself,
not a Concepteur's store).

Exposed publicly (no auth) so Google / Mollie / partners can crawl them."""

from datetime import datetime

PLATFORM_COMPANY = {
    # Nom commercial (apparaît dans tout le branding)
    "nom": "Altiora",
    # Informations légales réelles de l'éditeur (entrepreneur individuel)
    "forme_juridique": "Entrepreneur individuel",
    "dirigeant_nom": "Robin Zuchiatti",  # Requis par la LCEN pour un EI
    "siren": "883 803 967",
    "siret": "883 803 967 00016",
    "date_creation": "30/05/2020",
    "rne_inscription": "Inscrit au RNE le 30/05/2020",
    "tva_intra": "FR42883803967",
    "code_naf": "47.82Z",
    "activite": "Commerce de détail et services e-commerce — plateforme SaaS multi-marques",
    "adresse": "4 impasse du Clos Fleuri, 42320 Farnay, France",
    "email": "contact@altiora.com",
    "telephone": "À compléter",
    "directeur_publication": "Robin Zuchiatti",
    "hebergeur_nom": "Emergent Labs",
    "hebergeur_adresse": "Infrastructure Kubernetes — à compléter avec l'adresse de l'hébergeur",
    "site_web": "https://altiora.com",
}


def _today():
    return datetime.utcnow().strftime("%d/%m/%Y")


def render_mentions_legales():
    c = PLATFORM_COMPANY
    return {
        "title": "Mentions légales",
        "updated": _today(),
        "content": f"""
## 1. Éditeur du site

**Altiora** est le nom commercial sous lequel **{c['dirigeant_nom']}**, entrepreneur
individuel, édite et exploite la plateforme accessible à l'adresse {c['site_web']}.

- Forme juridique : {c['forme_juridique']}
- SIREN : **{c['siren']}**
- SIRET (siège) : {c['siret']}
- Inscription : {c['rne_inscription']}
- N° TVA intracommunautaire : {c['tva_intra']}
- Code NAF / APE : {c['code_naf']}
- Siège social : {c['adresse']}
- Directeur de la publication : {c['directeur_publication']}
- E-mail : {c['email']}
- Téléphone : {c['telephone']}

## 2. Hébergement

Le site **{c['site_web']}** est hébergé par :
- {c['hebergeur_nom']}
- {c['hebergeur_adresse']}

## 3. Propriété intellectuelle

L'ensemble du contenu de ce site (textes, logo, images, code, marque « Altiora »)
est la propriété exclusive de {c['dirigeant_nom']} (exerçant sous le nom
commercial Altiora) et est protégé par les lois françaises et internationales
relatives à la propriété intellectuelle.

Toute reproduction, représentation, modification, publication, adaptation totale
ou partielle des éléments du site, quel que soit le moyen ou le procédé utilisé,
est interdite sans autorisation écrite préalable.

## 4. Responsabilité

L'éditeur s'efforce de fournir des informations aussi précises que possible.
Toutefois, il ne pourra être tenu responsable des omissions, inexactitudes ou
carences dans la mise à jour, qu'elles soient de son fait ou du fait de tiers
partenaires qui lui fournissent ces informations.

## 5. Droit applicable

Tout litige en relation avec l'utilisation du site **{c['site_web']}** est soumis
au droit français. Il est fait attribution exclusive de juridiction aux tribunaux
compétents du ressort du siège social de l'éditeur.
""".strip(),
    }


def render_cgu():
    c = PLATFORM_COMPANY
    return {
        "title": "Conditions Générales d'Utilisation",
        "updated": _today(),
        "content": f"""
## Préambule

Les présentes Conditions Générales d'Utilisation (CGU) régissent l'accès et
l'utilisation de la plateforme **Altiora** (ci-après « la Plateforme »), éditée
par {c['dirigeant_nom']} (entrepreneur individuel, SIREN {c['siren']}),
exerçant sous le nom commercial Altiora.

## 1. Définitions

- **Plateforme** : le service en ligne accessible via {c['site_web']}.
- **Utilisateur** : toute personne physique ou morale utilisant la Plateforme.
- **Concepteur** : Utilisateur inscrit exploitant un ou plusieurs sites e-commerce
  via la Plateforme, selon un modèle de partenariat 50/50 sur la marge brute.
- **Éditeur** : {c['dirigeant_nom']} exerçant sous le nom commercial Altiora.
- **Administrateur** : collaborateur de l'Éditeur disposant de droits étendus.

## 2. Inscription et compte

L'inscription à la Plateforme est réservée aux professionnels (entrepreneurs,
sociétés). L'Utilisateur garantit l'exactitude des informations fournies.

## 3. Services proposés

Altiora met à disposition :
- Un moteur d'analyse de niches e-commerce (Silver Economy et autres marchés),
- Un générateur de sites e-commerce par IA,
- Un cockpit de gestion (catalogue, commandes, finance, SEO, publicité),
- Un système de paiement intégré (Mollie),
- Un accompagnement stratégique.

## 4. Obligations des Concepteurs

Le Concepteur s'engage à :
- Respecter les lois françaises et européennes applicables à son activité
  (DGCCRF, RGPD, TVA, droit de la consommation),
- Fournir des produits conformes à la réglementation,
- Ne pas utiliser la Plateforme pour des activités illégales ou contraires aux
  bonnes mœurs,
- Tenir à jour ses informations bancaires (IBAN) pour recevoir ses versements.

## 5. Partage de la marge brute (50/50)

La marge brute hors taxes de chaque commande est partagée à parts égales entre
le Concepteur et l'Éditeur. Les versements sont effectués les 1er et 15 de
chaque mois par virement bancaire (SEPA).

## 6. Propriété intellectuelle

Les contenus générés par le Concepteur (textes, visuels, catalogue) restent sa
propriété. L'Éditeur conserve la propriété de la Plateforme, de la marque
Altiora et de son code source.

## 7. Résiliation

Chaque partie peut résilier l'accès à la Plateforme avec un préavis de 30 jours,
par e-mail à {c['email']}. Les soldes dus sont réglés sous 15 jours.

## 8. Droit applicable

Les présentes CGU sont soumises au droit français. Tout litige relève de la
compétence exclusive des tribunaux du ressort du siège social de l'Éditeur.

## 9. Contact

Pour toute question : **{c['email']}**
""".strip(),
    }


def render_confidentialite():
    c = PLATFORM_COMPANY
    return {
        "title": "Politique de confidentialité",
        "updated": _today(),
        "content": f"""
## 1. Responsable du traitement

**{c['dirigeant_nom']}**, exerçant sous le nom commercial Altiora
(entrepreneur individuel, SIREN {c['siren']}) — {c['adresse']} — {c['email']}.

## 2. Données collectées

Nous collectons les données suivantes :

**Concepteurs :**
- Nom, e-mail, téléphone, raison sociale, SIRET, IBAN, adresse de facturation.
- Historique des sites créés, commandes générées, marges perçues.

**Clients finaux (sites des Concepteurs) :**
- Nom, e-mail, adresse de livraison, téléphone, historique de commandes.

**Données techniques :**
- Logs d'accès, adresse IP, type de navigateur, cookies de session.

## 3. Finalités du traitement

- Exécution du contrat (gestion du compte, exécution des commandes, paiements).
- Obligations légales (facturation, comptabilité, lutte anti-fraude).
- Amélioration du service (anonymisation, statistiques internes).
- Communication commerciale (uniquement avec consentement explicite).

## 4. Base légale

- **Exécution contractuelle** (CGU acceptées à l'inscription).
- **Obligation légale** (facturation, comptabilité — 10 ans).
- **Intérêt légitime** (sécurité, détection de fraude).
- **Consentement** (newsletters, cookies non-essentiels).

## 5. Durée de conservation

- Données de compte : 3 ans après la dernière connexion.
- Factures et comptabilité : 10 ans (obligation légale).
- Logs techniques : 12 mois.
- Cookies : 13 mois maximum.

## 6. Destinataires

- L'éditeur lui-même (support, comptabilité).
- Sous-traitants techniques (Mollie pour les paiements, Resend pour les e-mails,
  MongoDB Atlas pour l'hébergement des données, Emergent Labs pour l'infrastructure).
- Autorités publiques sur réquisition légale.

**Aucune donnée n'est revendue à des tiers.**

## 7. Transferts hors UE

Certains sous-traitants techniques sont situés hors UE (États-Unis). Les
transferts sont encadrés par les clauses contractuelles types de la Commission
européenne.

## 8. Droits des personnes

Conformément au RGPD, vous disposez des droits suivants :
- **Droit d'accès** : obtenir une copie de vos données.
- **Droit de rectification** : corriger des données erronées.
- **Droit à l'effacement** : demander la suppression de vos données.
- **Droit d'opposition** : vous opposer à un traitement.
- **Droit à la portabilité** : récupérer vos données dans un format lisible.
- **Droit de limitation** : geler un traitement contesté.

Pour exercer ces droits : **{c['email']}** avec justificatif d'identité.
Réponse sous 30 jours maximum.

## 9. Réclamations

En cas de litige non résolu, vous pouvez saisir la CNIL :
- Site : https://www.cnil.fr
- Adresse : 3 place de Fontenoy, 75007 Paris.
""".strip(),
    }


def render_cookies():
    c = PLATFORM_COMPANY
    return {
        "title": "Politique des cookies",
        "updated": _today(),
        "content": f"""
## 1. Qu'est-ce qu'un cookie ?

Un cookie est un petit fichier texte déposé sur votre terminal lors de votre
visite sur {c['site_web']}. Il permet de mémoriser vos préférences, d'analyser
l'usage du site et de sécuriser votre session.

## 2. Cookies utilisés par Altiora

### 2.1 Cookies strictement nécessaires (pas de consentement requis)
| Nom | Finalité | Durée |
|---|---|---|
| `access_token` | Authentification de session (JWT) | 7 jours |
| `csrf_token` | Protection CSRF | Session |

### 2.2 Cookies de mesure d'audience (consentement requis)
| Nom | Finalité | Durée | Fournisseur |
|---|---|---|---|
| `ph_*` | Mesure d'usage interne (PostHog) | 12 mois | PostHog Inc. (US) |

### 2.3 Cookies tiers (intégrations)
- **Mollie** : cookies de session pour le checkout des commandes.
- **Google (si Merchant Center / Ads activé)** : cookies publicitaires et de
  remarketing sur les sites Concepteurs ayant opté pour ces services.

## 3. Gérer vos préférences

Vous pouvez à tout moment :
- Refuser les cookies non-essentiels depuis la bannière affichée à votre
  première visite.
- Configurer votre navigateur pour bloquer ou supprimer les cookies.
- Nous écrire à **{c['email']}** pour exercer vos droits RGPD.

## 4. Durée de conservation

Les cookies ont une durée de vie maximale de 13 mois, conformément à la
recommandation de la CNIL.

## 5. Contact

Pour toute question sur notre usage des cookies : **{c['email']}**
""".strip(),
    }


def get_legal_page(slug: str):
    """Return a legal page by slug, or None."""
    registry = {
        "mentions-legales": render_mentions_legales,
        "cgu": render_cgu,
        "confidentialite": render_confidentialite,
        "cookies": render_cookies,
    }
    fn = registry.get(slug)
    return fn() if fn else None
