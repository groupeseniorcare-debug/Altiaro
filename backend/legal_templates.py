"""Templates légaux français standards, Claude remplit uniquement quelques variables.

Variables attendues : {raison_sociale}, {siren}, {adresse}, {ville}, {cp}, {email_contact},
{directeur_publication}, {hebergeur}, {tva_intracom}, {niche_name}.
"""
from __future__ import annotations


MENTIONS_LEGALES = """# Mentions légales

## 1. Éditeur du site
Le site **{site_name}** est édité par **{raison_sociale}**, société par actions simplifiée (SAS)
au capital social variable, dont le siège social est situé au **{adresse}, {cp} {ville}**.

- SIREN : **{siren}**
- Numéro de TVA intracommunautaire : **{tva_intracom}**
- Directeur de la publication : **{directeur_publication}**
- Email de contact : **{email_contact}**

## 2. Hébergeur
Le site est hébergé par **{hebergeur}**.

## 3. Propriété intellectuelle
L'ensemble des contenus (textes, images, logos, marques, vidéos) présents sur ce site est
protégé par le droit d'auteur et le droit des marques. Toute reproduction, représentation,
modification, publication ou adaptation de tout ou partie des éléments du site est
strictement interdite sans autorisation écrite préalable.

## 4. Données personnelles
Conformément au Règlement Général sur la Protection des Données (RGPD), vous disposez
d'un droit d'accès, de rectification, d'effacement, de portabilité, d'opposition et de
limitation du traitement de vos données personnelles. Pour exercer ces droits,
contactez-nous à {email_contact}.

## 5. Cookies
Le site utilise des cookies pour améliorer l'expérience utilisateur et mesurer l'audience.
Vous pouvez à tout moment paramétrer ou refuser les cookies depuis les réglages de votre navigateur.

## 6. Droit applicable
Les présentes mentions légales sont régies par le droit français. Tout litige relatif à
l'utilisation du site sera de la compétence exclusive des tribunaux français.
"""

CGV = """# Conditions Générales de Vente

## Article 1 — Objet
Les présentes Conditions Générales de Vente (CGV) régissent les relations contractuelles
entre **{raison_sociale}**, exploitant le site **{site_name}** spécialisé dans la
commercialisation de produits **{niche_name}**, et tout client consommateur.

## Article 2 — Commande
La commande est validée après confirmation par le client et paiement intégral du prix.
Un email de confirmation est envoyé automatiquement. Le contrat est conclu au moment de
cette confirmation.

## Article 3 — Prix
Les prix sont indiqués en euros toutes taxes comprises (TTC), hors frais de livraison.
Les frais de livraison sont précisés avant validation de la commande.

## Article 4 — Paiement
Le paiement s'effectue par carte bancaire via notre prestataire de paiement sécurisé Mollie.
Les transactions sont chiffrées (SSL). **{raison_sociale}** ne conserve aucune donnée bancaire.

## Article 5 — Livraison
Les commandes sont expédiées sous 2 à 5 jours ouvrés. Le délai de livraison varie selon la
destination (France métropolitaine : 2-4 jours · Europe : 4-8 jours). Un numéro de suivi
est fourni par email.

## Article 6 — Droit de rétractation
Conformément à l'article L.221-18 du Code de la consommation, le client dispose d'un délai
de **14 jours** à compter de la réception de sa commande pour exercer son droit de
rétractation, sans avoir à justifier de motif. Les frais de retour sont à la charge du client.
Le remboursement intervient dans un délai de 14 jours après réception du produit retourné.

## Article 7 — Garanties légales
Tous nos produits bénéficient de la **garantie légale de conformité** (2 ans) et de la
**garantie des vices cachés**, conformément aux articles L.217-4 et suivants du Code de
la consommation et 1641 et suivants du Code civil.

## Article 8 — Service Après-Vente
Pour toute question, réclamation ou demande de retour, contactez notre service client à
**{email_contact}**. Nous nous engageons à répondre sous 48h ouvrées.

## Article 9 — Médiation
En cas de litige non résolu à l'amiable, le client peut recourir gratuitement au médiateur
de la consommation compétent, conformément à l'article L.612-1 du Code de la consommation.

## Article 10 — Droit applicable
Les présentes CGV sont soumises au droit français. En cas de litige, les tribunaux français
sont seuls compétents.
"""

CONFIDENTIALITE = """# Politique de confidentialité

## 1. Identité du responsable de traitement
Le responsable du traitement de vos données personnelles est **{raison_sociale}**,
dont le siège social est situé au **{adresse}, {cp} {ville}**.

## 2. Données collectées
Nous collectons uniquement les données nécessaires à l'exécution de votre commande :
- **Identité** : nom, prénom, civilité
- **Coordonnées** : email, téléphone, adresse postale de livraison
- **Commande** : produits achetés, montant, historique
- **Navigation** : adresse IP, cookies techniques et analytiques

## 3. Finalités
Vos données sont utilisées pour :
- Traiter et livrer vos commandes
- Gérer la relation client (SAV, SAV, fidélité)
- Vous envoyer des communications marketing (avec votre consentement)
- Respecter nos obligations légales (comptabilité, fiscalité)

## 4. Base légale
- Exécution du contrat de vente (article 6.1.b RGPD)
- Intérêt légitime pour la sécurité et la prévention de la fraude (article 6.1.f)
- Consentement explicite pour les communications marketing (article 6.1.a)

## 5. Durée de conservation
- Données de commande : **3 ans** après la dernière commande (garantie légale)
- Données comptables : **10 ans** (obligation légale)
- Cookies : **13 mois maximum**

## 6. Destinataires
Vos données sont uniquement partagées avec :
- Nos prestataires techniques (hébergeur, prestataire de paiement Mollie, transporteurs)
- Les autorités fiscales et judiciaires sur réquisition légale

## 7. Vos droits
Conformément au RGPD, vous disposez des droits suivants :
- **Droit d'accès** à vos données
- **Droit de rectification** des données inexactes
- **Droit à l'effacement** (« droit à l'oubli »)
- **Droit à la portabilité** de vos données
- **Droit d'opposition** au traitement
- **Droit de limitation** du traitement
- **Droit de déposer une réclamation** auprès de la CNIL (www.cnil.fr)

Pour exercer ces droits, contactez-nous à **{email_contact}**. Nous répondons sous 30 jours.

## 8. Sécurité
Nous mettons en œuvre des mesures techniques et organisationnelles pour protéger vos
données : chiffrement SSL, accès restreint, sauvegardes chiffrées, mots de passe hachés.

## 9. Cookies
Nous utilisons des cookies techniques nécessaires au fonctionnement du site et, avec
votre consentement, des cookies analytiques (Google Analytics) et marketing.
Vous pouvez gérer vos préférences à tout moment depuis le bandeau cookies.
"""


COOKIES = """# Politique de cookies

## 1. Qu'est-ce qu'un cookie ?
Un cookie est un petit fichier texte stocké sur votre terminal (ordinateur, tablette,
smartphone) lors de votre visite sur **{site_name}**. Il permet au site de mémoriser
certaines informations pour améliorer votre expérience.

## 2. Cookies utilisés sur notre site

### Cookies strictement nécessaires (exemptés de consentement)
- **Panier** : mémorisation du panier entre les pages
- **Session** : maintien de la session client connectée
- **Préférences** : langue, devise, acceptation du bandeau cookies

### Cookies de mesure d'audience (avec consentement)
- **Google Analytics 4** : statistiques anonymes de visite
- **Google Tag Manager** : gestion centralisée des tags

### Cookies marketing (avec consentement)
- **Meta Pixel** (Facebook) : ciblage publicitaire
- **Google Ads Conversion** : suivi des conversions publicitaires

## 3. Durée de conservation
Les cookies sont conservés **13 mois maximum** conformément aux recommandations CNIL.

## 4. Gérer mes préférences
À tout moment, vous pouvez :
- Modifier vos choix depuis le bandeau « Gérer les cookies » en bas de page
- Paramétrer votre navigateur pour refuser les cookies
- Consulter la documentation de votre navigateur
  ([Chrome](https://support.google.com/chrome/answer/95647),
  [Firefox](https://support.mozilla.org/fr/kb/activer-desactiver-cookies),
  [Safari](https://support.apple.com/fr-fr/guide/safari/sfri11471/mac))

## 5. Conséquences du refus
Refuser les cookies n'empêche pas la navigation mais peut désactiver certaines
fonctionnalités (panier persistant, personnalisation).

## 6. Réclamation
Pour toute question, contactez **{email_contact}**. Vous pouvez également déposer une
réclamation auprès de la **CNIL** (www.cnil.fr).
"""


LIVRAISON = """# Livraison & délais

## Zones de livraison
Nous livrons dans toute la **France métropolitaine**, ainsi que :
- **Belgique, Luxembourg, Pays-Bas** : 3-6 jours ouvrés
- **Suisse** (frontières douanières) : 5-8 jours ouvrés
- **Royaume-Uni** : 5-10 jours ouvrés (frais de douane à la charge du client)
- **Allemagne, Autriche** : 3-6 jours ouvrés

## Délais de préparation
Votre commande est préparée sous **24 à 48 heures ouvrées** après réception du paiement.
Les produits volumineux (fauteuils, meubles) peuvent nécessiter **3 à 5 jours ouvrés**
de préparation supplémentaires.

## Délais de livraison (après expédition)
| Destination | Mode standard | Mode express |
|---|---|---|
| France métropolitaine | 2-4 j | 24-48 h |
| Europe UE | 3-6 j | 2-3 j |
| Royaume-Uni | 5-10 j | 3-5 j |

## Suivi de commande
Un email avec le numéro de suivi vous est envoyé dès l'expédition. Vous pouvez suivre
votre colis en temps réel depuis votre espace client ou via le lien du transporteur.

## Frais de livraison
- **Offerte dès 50 €** d'achat en France métropolitaine
- **5,90 €** en dessous de 50 €
- Livraison express et Europe : tarif calculé au checkout selon poids et destination
- Produits volumineux : livraison sur rendez-vous avec possibilité d'installation (option)

## Réception du colis
Nous vous recommandons de **vérifier l'état du colis en présence du livreur**. En cas de
colis visiblement endommagé, refusez-le ou émettez des **réserves précises et datées** sur
le bon de livraison, puis contactez-nous sous 48 h.

## Absence à la livraison
Si vous êtes absent, le transporteur laisse un avis de passage. Vous disposez généralement
de 10 jours pour retirer le colis en point relais ou bureau de poste.

## Support livraison
Pour toute question : **{email_contact}**. Réponse sous 24h ouvrées.
"""


RETOURS = """# Retours & rétractation

## Droit de rétractation de 14 jours
Conformément à l'article **L.221-18 du Code de la consommation**, vous disposez d'un délai
de **14 jours calendaires** à compter de la réception de votre commande pour exercer votre
droit de rétractation, **sans avoir à justifier de motif ni pénalité**.

## Comment exercer mon droit de rétractation ?
1. Informez-nous de votre décision via :
   - Email à **{email_contact}** (modèle de formulaire ci-dessous)
   - Le formulaire de contact de votre espace client
2. Retournez le produit dans son **emballage d'origine**, accompagné de tous ses accessoires
3. Joignez une copie de la facture ou du bon de retour

## Adresse de retour
**{raison_sociale}** — Service Retours
{adresse}
{cp} {ville}

## Frais de retour
Les **frais de retour sont à votre charge**, sauf en cas de produit défectueux ou
non-conforme (voir garanties).

## Remboursement
Nous procédons au remboursement dans un délai de **14 jours** à compter de la réception du
produit retourné, par le même moyen de paiement utilisé pour la commande. Aucun frais de
remboursement ne vous est facturé.

## Exclusions légales
Conformément à l'article **L.221-28**, le droit de rétractation ne s'applique pas :
- Aux produits confectionnés sur mesure ou personnalisés
- Aux produits d'hygiène descellés après livraison
- Aux produits périssables

## Garantie légale de conformité (2 ans)
Indépendamment de la rétractation, tous nos produits bénéficient de la **garantie légale
de conformité** (articles L.217-4 à L.217-14 du Code de la consommation) pendant **2 ans**.
En cas de défaut, le remplacement ou le remboursement est **gratuit**.

## Formulaire type de rétractation
> À l'attention de **{raison_sociale}**, {adresse}, {cp} {ville}
>
> Je/nous (*) vous notifie/notifions (*) par la présente ma/notre (*) rétractation
> du contrat portant sur la vente du bien ci-dessous :
>
> Commandé le : ........................
> Reçu le : ........................
> Numéro de commande : ........................
> Nom du/des consommateur(s) : ........................
> Adresse du/des consommateur(s) : ........................
>
> Date : ........................    Signature : ........................
>
> (*) Rayez la mention inutile
"""


MEDIATION = """# Médiation de la consommation

Conformément à l'article **L.612-1 du Code de la consommation**, tout consommateur a le
droit de recourir gratuitement à un médiateur de la consommation en vue de la résolution
amiable d'un litige.

## 1. Avant la médiation
Avant de saisir le médiateur, le client doit avoir :
1. Contacté notre service client à **{email_contact}**
2. Attendu une réponse ou un délai raisonnable de traitement (60 jours maximum)
3. Conservé les preuves écrites des échanges

## 2. Médiateur de la consommation désigné
**{raison_sociale}** a désigné le médiateur suivant pour la résolution amiable des litiges :

> **CM2C — Centre de la Médiation de la Consommation de Conciliateurs de Justice**
> 14 rue Saint-Jean — 75017 Paris
> Site : **https://cm2c.net**
> Email : cm2c@cm2c.net

Vous pouvez saisir le médiateur **gratuitement** dans un délai de **1 an** à compter de
votre première réclamation écrite.

## 3. Plateforme européenne de règlement des litiges (ODR)
En vertu du règlement UE n° 524/2013, vous avez également la possibilité de recourir à la
plateforme européenne de règlement des litiges de consommation :

> **https://ec.europa.eu/consumers/odr**

## 4. Recours judiciaires
Si la médiation n'aboutit pas, vous conservez le droit de saisir les tribunaux compétents
conformément aux règles du Code de procédure civile.

## 5. Contact
Pour toute question relative à la médiation : **{email_contact}**.
"""


DEFAULT_LEGAL_VARS = {
    "raison_sociale": "Altiaro SAS",
    "siren": "[À COMPLÉTER]",
    "tva_intracom": "[À COMPLÉTER]",
    "adresse": "[À COMPLÉTER]",
    "cp": "[CODE POSTAL]",
    "ville": "[VILLE]",
    "directeur_publication": "[NOM DU DIRECTEUR]",
    "hebergeur": "Emergent Platform",
    "email_contact": "contact@{domain}",
}


def render_legal(template: str, variables: dict) -> str:
    """Render legal template with variables. Missing vars become [À COMPLÉTER]."""
    safe = dict(DEFAULT_LEGAL_VARS)
    safe.update({k: v for k, v in variables.items() if v})
    try:
        return template.format(**safe)
    except KeyError as e:
        # Fallback: leave missing keys as-is
        import re
        missing = f"[{str(e).strip(chr(39))}]"
        return re.sub(r"\{" + str(e).strip("'") + r"\}", missing, template)
