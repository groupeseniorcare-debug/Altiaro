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


DEFAULT_LEGAL_VARS = {
    "raison_sociale": "Altiora SAS",
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
