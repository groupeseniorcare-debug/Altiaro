"""Centralized legal information for the Altiaro platform AND every Concepteur
store hosted on it.

Bloc 2 — Refactor :

* `PLATFORM_LEGAL_INFO`  → source-of-truth dict with the real legal data
                           extracted from the KBIS (SIREN/SIRET/APE/address).
                           ⚠️  AUCUN NOM PERSONNEL : conformément aux consignes
                           Bloc 2, le représentant légal AFFICHE PUBLIQUEMENT
                           est toujours le nom commercial (« la Société Altea »
                           pour le site Altea, « la Société Altiaro » pour la
                           plateforme elle-même), JAMAIS un prénom/nom de
                           personne physique.

* `render_for_site(site)` → généreur de pages légales pour un store concepteur
                           (mentions-légales, cgv, cgu, confidentialité,
                           cookies, retours, livraison) en substituant
                           [NOM_COMMERCIAL] / [EMAIL_CONTACT] / [TELEPHONE]
                           depuis les données du site.

* `render_mentions_legales()` etc. — versions « plateforme Altiaro » (pour la
                           landing publique altiaro.com).

Priorité de lecture (futur) : DB collection `platform_legal` > .env > constante
hardcoded. Pour l'instant la constante hardcoded est l'unique source.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE OF TRUTH — extraite du KBIS fourni par l'utilisateur (Bloc 2).
# Cette structure est utilisée :
#   1. Pour la plateforme Altiaro elle-même (landing publique altiaro.com)
#   2. Pour CHAQUE site concepteur (Altiaro = exploitant légal unique des
#      stores → toutes les boutiques affichent ces infos KBIS communes,
#      avec leur propre nom commercial / email / téléphone substitués).
# ─────────────────────────────────────────────────────────────────────────────
PLATFORM_LEGAL_INFO: Dict[str, str] = {
    # ─── Identité légale officielle ────────────────────────────────────
    "siren":              os.environ.get("ALTIARO_SIREN", "883 803 967"),
    "siret":              os.environ.get("ALTIARO_SIRET", "883 803 967 00016"),
    "code_naf":           os.environ.get("ALTIARO_CODE_NAF", "4782Z"),
    "activite":           "Commerce de détail sur éventaires et marchés "
                          "(activité principale APE 4782Z) — e-commerce premium",
    "date_creation":      "30/05/2020",
    "rne_inscription":    "Inscrit au Registre National des Entreprises (RNE) "
                          "le 30/05/2020",
    "adresse":            os.environ.get(
        "ALTIARO_LEGAL_ADDRESS",
        "4 IMP CLOS FLEURI, 42320 FARNAY, France",
    ),
    # ⚠️  Forme juridique générique : afficher « Société » uniquement
    # (consigne stricte — pas « auto-entreprise », pas « micro-entreprise »,
    # pas « EI »).
    "forme_juridique":    os.environ.get("ALTIARO_LEGAL_FORM", "Société"),
    # TVA : non applicable, mention obligatoire CGI 293 B
    "tva_intra":          "Non applicable",
    "tva_mention_cgv":    "TVA non applicable, art. 293 B du CGI",
    # ─── Plateforme Altiaro (landing publique) ─────────────────────────
    "platform_nom":       "Altiaro",
    "platform_email":     "contact@altiaro.com",
    "platform_telephone": "+33 6 95 18 17 03",
    "platform_site_web":  "https://altiaro.com",
    # ─── Hébergement ───────────────────────────────────────────────────
    "hebergeur_nom":      "Emergent Labs",
    "hebergeur_adresse":  "Infrastructure Kubernetes (Cloudflare devant)",
    # ─── Activité ──────────────────────────────────────────────────────
    "activite_libelle":   "Vente de biens et services en ligne (e-commerce)",
}


# ─────────────────────────────────────────────────────────────────────────────
# Compat : ancien nom utilisé par les imports existants. On garde la même
# structure publique pour ne pas casser, mais on ne réfère plus à un nom
# personnel.
# ─────────────────────────────────────────────────────────────────────────────
PLATFORM_COMPANY = {
    "nom":                  PLATFORM_LEGAL_INFO["platform_nom"],
    "forme_juridique":      PLATFORM_LEGAL_INFO["forme_juridique"],
    "siren":                PLATFORM_LEGAL_INFO["siren"],
    "siret":                PLATFORM_LEGAL_INFO["siret"],
    "date_creation":        PLATFORM_LEGAL_INFO["date_creation"],
    "rne_inscription":      PLATFORM_LEGAL_INFO["rne_inscription"],
    "tva_intra":            PLATFORM_LEGAL_INFO["tva_intra"],
    "tva_mention_cgv":      PLATFORM_LEGAL_INFO["tva_mention_cgv"],
    "code_naf":             PLATFORM_LEGAL_INFO["code_naf"],
    "activite":             PLATFORM_LEGAL_INFO["activite"],
    "adresse":              PLATFORM_LEGAL_INFO["adresse"],
    "email":                PLATFORM_LEGAL_INFO["platform_email"],
    "telephone":            PLATFORM_LEGAL_INFO["platform_telephone"],
    "directeur_publication": PLATFORM_LEGAL_INFO["platform_nom"],   # nom commercial
    "hebergeur_nom":        PLATFORM_LEGAL_INFO["hebergeur_nom"],
    "hebergeur_adresse":    PLATFORM_LEGAL_INFO["hebergeur_adresse"],
    "site_web":             PLATFORM_LEGAL_INFO["platform_site_web"],
}


def _today() -> str:
    return datetime.utcnow().strftime("%d/%m/%Y")


def _coalesce(*values: Any) -> str:
    """Pick the first non-empty stringified value."""
    for v in values:
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _site_legal_context(site: Dict[str, Any]) -> Dict[str, str]:
    """Build the substitution context for a single Concepteur store.

    Reads brand info from the site document and falls back to the platform
    defaults (Altiaro KBIS) for everything else. The merchant of record IS
    Altiaro — every store shares the same SIRET/address.
    """
    design = (site or {}).get("design") or {}
    brand = (design.get("brand") or {})
    contact = (design.get("contact") or {})
    site_id = site.get("id") if site else None
    slug = site.get("slug") if site else None

    nom_commercial = _coalesce(
        brand.get("name"),
        site.get("name") if site else None,
        slug,
        "la Boutique",
    )
    # Email: prefer site-defined, else slug-based, else platform contact
    email = _coalesce(
        contact.get("support_email"),
        contact.get("email"),
        f"contact@{slug}.com" if slug else None,
        f"contact@{nom_commercial.lower().replace(' ', '')}.com" if nom_commercial else None,
        PLATFORM_LEGAL_INFO["platform_email"],
    )
    telephone = _coalesce(
        contact.get("support_phone"),
        contact.get("phone"),
        PLATFORM_LEGAL_INFO["platform_telephone"],
    )
    # Public origin where this store is reachable (used in mentions légales)
    origin = _coalesce(
        site.get("custom_domain") and f"https://{site.get('custom_domain')}",
        site.get("public_url"),
        f"https://altiaro.com/shop/{site_id}" if site_id else "",
    )

    ctx = {
        # site-specific
        "nom_commercial":       nom_commercial,
        "email_contact":        email,
        "telephone":            telephone,
        "origin":               origin,
        "slug":                 slug or "",
        # platform-shared (always KBIS)
        "siren":                PLATFORM_LEGAL_INFO["siren"],
        "siret":                PLATFORM_LEGAL_INFO["siret"],
        "code_naf":             PLATFORM_LEGAL_INFO["code_naf"],
        "adresse":              PLATFORM_LEGAL_INFO["adresse"],
        "forme_juridique":      PLATFORM_LEGAL_INFO["forme_juridique"],
        "rne_inscription":      PLATFORM_LEGAL_INFO["rne_inscription"],
        "tva_mention_cgv":      PLATFORM_LEGAL_INFO["tva_mention_cgv"],
        "tva_intra":            PLATFORM_LEGAL_INFO["tva_intra"],
        "hebergeur_nom":        PLATFORM_LEGAL_INFO["hebergeur_nom"],
        "hebergeur_adresse":    PLATFORM_LEGAL_INFO["hebergeur_adresse"],
        "platform_nom":         PLATFORM_LEGAL_INFO["platform_nom"],
        "platform_email":       PLATFORM_LEGAL_INFO["platform_email"],
        "today":                _today(),
    }
    return ctx


# ═════════════════════════════════════════════════════════════════════════════
# RENDU POUR UN SITE CONCEPTEUR (Altea, etc.)
# ═════════════════════════════════════════════════════════════════════════════

def render_site_mentions_legales(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Mentions légales",
        "updated": c["today"],
        "body_md": f"""
## 1. Éditeur du site

La boutique en ligne **{c['nom_commercial']}** (ci-après « le Site ») est éditée et
exploitée par la **Société {c['platform_nom']}**, marchand de référence pour
l'ensemble des boutiques de la plateforme.

- **Forme juridique** : {c['forme_juridique']}
- **SIREN** : {c['siren']}
- **SIRET (siège)** : {c['siret']}
- **Code APE/NAF** : {c['code_naf']}
- **Inscription** : {c['rne_inscription']}
- **Siège social** : {c['adresse']}
- **TVA intracommunautaire** : {c['tva_intra']} ({c['tva_mention_cgv']})
- **Directeur de la publication** : la Société {c['nom_commercial']}
- **E-mail** : {c['email_contact']}
- **Téléphone** : {c['telephone']}

## 2. Hébergement

Le Site est hébergé par :
- **{c['hebergeur_nom']}** — {c['hebergeur_adresse']}

Pour toute demande relative à l'hébergement (notamment dans le cadre de la
LCEN, art. 6-III), merci de contacter directement l'hébergeur.

## 3. Propriété intellectuelle

L'ensemble du contenu du Site (textes, photos, logos, marque
« {c['nom_commercial']} », vidéos, code, design) est la propriété exclusive de
la Société {c['platform_nom']} (exerçant sous le nom commercial
{c['nom_commercial']} pour ce Site) et est protégé par les lois françaises et
internationales relatives à la propriété intellectuelle.

Toute reproduction, représentation, modification, publication, adaptation
totale ou partielle, par quelque moyen ou procédé que ce soit, est interdite
sans autorisation écrite préalable.

## 4. Responsabilité

L'éditeur s'efforce de fournir des informations aussi précises que possible.
Toutefois, il ne pourra être tenu responsable des omissions, inexactitudes ou
carences dans la mise à jour, qu'elles soient de son fait ou du fait de tiers
partenaires.

## 5. Données personnelles & cookies

Voir notre [Politique de confidentialité](/shop/{c['slug']}/confidentialite) et
notre [Politique des cookies](/shop/{c['slug']}/cookies).

## 6. Droit applicable

Les présentes mentions légales sont soumises au droit français. Tout litige
relève de la compétence exclusive des tribunaux du ressort du siège social de
l'éditeur.

## 7. Contact

Pour toute question : **{c['email_contact']}** · {c['telephone']}
""".strip(),
    }


def render_site_cgv(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Conditions générales de vente",
        "updated": c["today"],
        "body_md": f"""
## Préambule

Les présentes Conditions Générales de Vente (CGV) régissent les ventes
réalisées sur la boutique **{c['nom_commercial']}**, exploitée par la **Société
{c['platform_nom']}** (SIREN {c['siren']}, SIRET {c['siret']}, siège social :
{c['adresse']}).

Toute commande passée sur le Site implique l'acceptation pleine et entière des
présentes CGV.

## 1. Objet

Les présentes CGV s'appliquent à toute vente de produits proposée par la
Société {c['platform_nom']} sous le nom commercial {c['nom_commercial']}, à des
clients consommateurs (B2C).

## 2. Produits

Les caractéristiques essentielles des produits sont décrites sur la fiche
correspondante. Les photographies sont non contractuelles. Les produits restent
la propriété de l'éditeur jusqu'au paiement intégral du prix.

## 3. Prix et TVA

Les prix sont indiqués en euros (€), toutes taxes éventuelles incluses.

> **{c['tva_mention_cgv']}.**

Les prix peuvent évoluer à tout moment ; ils sont fermes et définitifs au
moment de la validation de la commande.

## 4. Commande

La commande est validée après acceptation expresse par le client (clic sur
« Procéder au paiement ») et confirmation du paiement. Un accusé de réception
est envoyé par e-mail à l'adresse fournie.

## 5. Paiement

Le paiement s'effectue en ligne par carte bancaire ou méthode équivalente via
notre prestataire **Mollie** (paiement sécurisé). Aucune donnée bancaire n'est
stockée sur nos serveurs.

## 6. Livraison

Les délais indicatifs de livraison sont précisés sur la fiche produit. La
livraison s'effectue à l'adresse indiquée par le client lors de la commande.
En cas de retard supérieur à 7 jours sur le délai annoncé, le client peut
demander l'annulation et le remboursement intégral de sa commande.

Les frais de livraison sont indiqués avant validation du paiement.

## 7. Droit de rétractation (14 jours)

Conformément aux articles L221-18 et suivants du Code de la consommation,
le client dispose d'un **délai de 14 jours** à compter de la réception du
produit pour exercer son droit de rétractation, sans avoir à motiver sa
décision.

Pour exercer ce droit, il suffit d'écrire à **{c['email_contact']}** ou de
nous joindre au **{c['telephone']}** dans le délai imparti.

Le produit doit être retourné dans son emballage d'origine, en état neuf.
Les frais de retour sont à la charge du client (sauf en cas de produit
défectueux).

Le remboursement intervient sous 14 jours à compter de la réception du produit
retourné, par le même moyen de paiement utilisé pour la commande.

**Exceptions** (pas de rétractation possible — art. L221-28 du Code de la
consommation) : produits scellés ouverts, produits personnalisés, biens
périssables.

## 8. Garantie légale de conformité

Les produits bénéficient :
- de la **garantie légale de conformité** (art. L217-3 et suivants du Code de
  la consommation) — **2 ans** à compter de la livraison ;
- de la **garantie des vices cachés** (art. 1641 du Code civil) — **2 ans** à
  compter de la découverte du vice.

Pour exercer ces garanties : **{c['email_contact']}**.

## 9. Service après-vente

Notre service client est joignable du lundi au vendredi de 9h à 18h
(hors jours fériés) au **{c['telephone']}** ou par e-mail à
**{c['email_contact']}**. Réponse en moyenne sous 24h ouvrées.

## 10. Médiation à la consommation

Conformément à l'article L612-1 du Code de la consommation, le client peut
recourir gratuitement à un médiateur en cas de litige non résolu : **AME CONSO**
— www.mediationconso-ame.com — 197 Boulevard Saint-Germain, 75007 Paris.

Plateforme européenne de règlement en ligne des litiges (RLL) :
**https://ec.europa.eu/consumers/odr**.

## 11. Données personnelles

Les données personnelles sont traitées conformément à notre
[Politique de confidentialité](/shop/{c['slug']}/confidentialite).

## 12. Droit applicable & juridictions

Les présentes CGV sont soumises au droit français. Tout litige relève de la
compétence exclusive des tribunaux français.

## 13. Contact

**{c['nom_commercial']}** — éditée par la Société {c['platform_nom']}
- E-mail : {c['email_contact']}
- Téléphone : {c['telephone']}
- Adresse : {c['adresse']}
""".strip(),
    }


def render_site_confidentialite(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Politique de confidentialité",
        "updated": c["today"],
        "body_md": f"""
## 1. Responsable du traitement

La **Société {c['platform_nom']}** (SIREN {c['siren']}, siège social :
{c['adresse']}) exerçant sous le nom commercial **{c['nom_commercial']}** pour
ce Site, est responsable du traitement de vos données personnelles.

**Contact RGPD** : {c['email_contact']} · {c['telephone']}

## 2. Données collectées

Lors d'une commande ou d'un contact, nous collectons :
- **Identité** : nom, prénom, civilité.
- **Coordonnées** : e-mail, téléphone, adresse de livraison et de facturation.
- **Commandes** : produits commandés, montants, dates.
- **Données techniques** : adresse IP, type de navigateur, cookies de session.

## 3. Finalités

- Exécution du contrat de vente (préparation, expédition, facturation, SAV).
- Obligations légales (comptabilité — 10 ans, lutte anti-fraude).
- Communication commerciale (uniquement avec consentement explicite).
- Amélioration du service (statistiques anonymisées).

## 4. Base légale

- **Exécution du contrat** : pour les commandes.
- **Obligation légale** : facturation, comptabilité.
- **Intérêt légitime** : sécurité, prévention de la fraude.
- **Consentement** : newsletters, cookies non-essentiels.

## 5. Durée de conservation

| Donnée | Durée |
|---|---|
| Données de compte client | 3 ans après dernière connexion |
| Factures, comptabilité | 10 ans (obligation légale) |
| Logs techniques | 12 mois |
| Cookies non-essentiels | 13 mois maximum |

## 6. Destinataires

- **{c['nom_commercial']}** (équipe service client, comptabilité).
- **Sous-traitants techniques** :
  - **Mollie** (paiements) — Pays-Bas.
  - **Resend** (e-mails transactionnels) — États-Unis.
  - **OVH** (DNS, infrastructure domaine) — France.
  - **Cloudflare** (CDN, anti-DDoS) — États-Unis.
  - **MongoDB Atlas** (base de données) — UE.
  - **Emergent Labs** (infrastructure Kubernetes) — États-Unis.
- **Autorités publiques** sur réquisition légale.

**Aucune donnée n'est revendue à des tiers.**

## 7. Transferts hors UE

Certains sous-traitants techniques sont situés hors UE (États-Unis). Les
transferts sont encadrés par les **clauses contractuelles types** de la
Commission européenne (article 46 du RGPD).

## 8. Vos droits

Conformément au RGPD, vous disposez :
- **Droit d'accès** : obtenir une copie de vos données.
- **Droit de rectification** : corriger des données erronées.
- **Droit à l'effacement** (« droit à l'oubli ») : demander la suppression.
- **Droit d'opposition** : vous opposer à un traitement (notamment marketing).
- **Droit à la portabilité** : récupérer vos données dans un format réutilisable.
- **Droit à la limitation** : geler temporairement un traitement.
- **Droit de retirer votre consentement** à tout moment.

Pour exercer ces droits : **{c['email_contact']}** avec justificatif
d'identité. Réponse sous 30 jours maximum.

## 9. Réclamation

En cas de litige non résolu, vous pouvez saisir la **CNIL** :
- Site : https://www.cnil.fr
- Adresse : 3 place de Fontenoy, TSA 80715, 75334 Paris Cedex 07.

## 10. Mises à jour

Cette politique peut être mise à jour. La date de dernière mise à jour figure
en pied de page.
""".strip(),
    }


def render_site_cookies(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Politique des cookies",
        "updated": c["today"],
        "body_md": f"""
## 1. Qu'est-ce qu'un cookie ?

Un cookie est un petit fichier texte déposé sur votre terminal lors de votre
visite. Il permet de mémoriser vos préférences, sécuriser votre session, ou
mesurer l'usage du Site.

## 2. Cookies utilisés sur {c['nom_commercial']}

### 2.1 Cookies strictement nécessaires (sans consentement, art. 82 LCEN)

| Nom | Finalité | Durée |
|---|---|---|
| Session de panier | Mémoriser votre panier en cours | Session |
| `altiaro_consent_v1` | Mémoriser vos choix cookies | 13 mois |
| Anti-fraude / sécurité | Protection CSRF, anti-bot | Session |

### 2.2 Mesure d'audience (consentement requis)

| Outil | Finalité | Durée | Fournisseur |
|---|---|---|---|
| Google Analytics 4 | Statistiques d'usage anonymisées | 13 mois | Google LLC (US) |

### 2.3 Marketing & publicité (consentement requis)

| Outil | Finalité | Fournisseur |
|---|---|---|
| Google Ads | Mesure des conversions, remarketing | Google LLC (US) |

### 2.4 Personnalisation (consentement requis)

| Cookie | Finalité | Durée |
|---|---|---|
| Préférence langue | Mémoriser la langue choisie | 6 mois |
| Recommandations | Mémoriser produits vus | 6 mois |

## 3. Gérer vos préférences

Vous pouvez à tout moment :
- **Modifier vos choix** via la bannière de consentement (cliquez sur l'icône
  cookie en bas de page si elle a été fermée).
- **Configurer votre navigateur** pour bloquer ou supprimer les cookies.
- **Nous écrire à {c['email_contact']}** pour exercer vos droits RGPD.

## 4. Durée de conservation

Conformément à la recommandation de la **CNIL**, les cookies non-essentiels
ont une durée de vie maximale de **13 mois**.

## 5. Contact

Pour toute question : **{c['email_contact']}** · {c['telephone']}
""".strip(),
    }


def render_site_retours(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Politique de retours",
        "updated": c["today"],
        "body_md": f"""
## 1. Droit de rétractation (14 jours)

Conformément aux articles L221-18 et suivants du Code de la consommation, vous
disposez d'un **délai de 14 jours** à compter de la réception de votre commande
pour exercer votre droit de rétractation, sans avoir à motiver votre décision.

## 2. Comment retourner un produit

1. Écrivez-nous à **{c['email_contact']}** en précisant votre numéro de
   commande (CF-XXXX) et le ou les produits à retourner.
2. Notre équipe vous envoie l'adresse de retour et un bordereau (sous 24h
   ouvrées).
3. Renvoyez le produit, dans son emballage d'origine et en état neuf, sous
   14 jours.

## 3. Frais de retour

Les frais de retour sont à la charge du client, sauf :
- **Produit défectueux ou non conforme** : retour pris en charge par
  {c['nom_commercial']}.
- **Erreur de notre part** (mauvais produit envoyé) : retour pris en charge.

## 4. Remboursement

Le remboursement intervient sous **14 jours** à compter de la réception du
produit retourné, par le même moyen de paiement utilisé pour la commande.

## 5. Exclusions

Conformément à l'article L221-28 du Code de la consommation, le droit de
rétractation **ne s'applique pas** :
- aux produits **personnalisés** ou réalisés sur mesure,
- aux produits **scellés ouverts** ne pouvant être réexpédiés pour des raisons
  d'hygiène,
- aux **biens périssables**.

## 6. Garantie légale

En sus du droit de rétractation, vous bénéficiez :
- de la **garantie légale de conformité** (2 ans, art. L217-3 du Code de la
  consommation) ;
- de la **garantie des vices cachés** (2 ans, art. 1641 du Code civil).

## 7. Contact

Pour toute question : **{c['email_contact']}** · {c['telephone']}
""".strip(),
    }


def render_site_livraison(site: Dict[str, Any]) -> Dict[str, str]:
    c = _site_legal_context(site)
    return {
        "title": "Livraison",
        "updated": c["today"],
        "body_md": f"""
## Délais

Les délais indicatifs sont précisés sur chaque fiche produit. En général :
- **France métropolitaine** : 3 à 7 jours ouvrés (selon le produit).
- **Belgique, Suisse, Luxembourg** : 5 à 10 jours ouvrés.
- **Autres pays UE** : 7 à 14 jours ouvrés.

## Frais

Les frais de port sont indiqués au moment du panier, avant la validation du
paiement. Ils dépendent du poids, du volume et de la destination.

**Livraison gratuite** offerte dès **50 € d'achat** en France métropolitaine.

## Suivi de commande

Dès l'expédition, un e-mail vous est envoyé avec le numéro de suivi. Vous
pouvez aussi suivre votre commande depuis votre **espace client**.

## En cas de retard

Si votre commande dépasse de plus de 7 jours le délai annoncé, écrivez-nous
à **{c['email_contact']}** ou appelez le **{c['telephone']}**. Au-delà de 14
jours, vous pouvez demander le remboursement intégral.

## Livraison à domicile

Pour les produits volumineux (mobilier, électroménager), la livraison
s'effectue **au pied de l'immeuble** par défaut. Une option *« Livraison
étage »* peut être proposée moyennant un supplément.

## Contact

Pour toute question logistique : **{c['email_contact']}** · {c['telephone']}
""".strip(),
    }


def get_site_legal_page(site: Dict[str, Any], slug: str) -> Optional[Dict[str, str]]:
    """Return a generated legal page for a Concepteur store, or None if unknown."""
    registry = {
        "mentions-legales": render_site_mentions_legales,
        "mentions":         render_site_mentions_legales,
        "cgv":              render_site_cgv,
        "confidentialite":  render_site_confidentialite,
        "privacy":          render_site_confidentialite,
        "cookies":          render_site_cookies,
        "retours":          render_site_retours,
        "returns":          render_site_retours,
        "livraison":        render_site_livraison,
        "shipping":         render_site_livraison,
    }
    fn = registry.get(slug)
    return fn(site) if fn else None


# ═════════════════════════════════════════════════════════════════════════════
# RENDU PLATEFORME ALTIARO (landing publique altiaro.com)
# ═════════════════════════════════════════════════════════════════════════════

def render_mentions_legales() -> Dict[str, str]:
    c = PLATFORM_LEGAL_INFO
    return {
        "title": "Mentions légales",
        "updated": _today(),
        "content": f"""
## 1. Éditeur du site

La plateforme **{c['platform_nom']}** est éditée par la **Société
{c['platform_nom']}**.

- Forme juridique : {c['forme_juridique']}
- SIREN : **{c['siren']}**
- SIRET (siège) : {c['siret']}
- Code APE/NAF : {c['code_naf']}
- Inscription : {c['rne_inscription']}
- Siège social : {c['adresse']}
- TVA intracommunautaire : {c['tva_intra']} ({c['tva_mention_cgv']})
- Directeur de la publication : la Société {c['platform_nom']}
- E-mail : {c['platform_email']}
- Téléphone : {c['platform_telephone']}

## 2. Hébergement

La plateforme est hébergée par :
- **{c['hebergeur_nom']}** — {c['hebergeur_adresse']}

## 3. Propriété intellectuelle

L'ensemble du contenu de cette plateforme (textes, logos, marque
« {c['platform_nom']} », vidéos, code) est la propriété exclusive de la Société
{c['platform_nom']}. Toute reproduction non autorisée est interdite.

## 4. Droit applicable

Les présentes mentions légales sont soumises au droit français. Tout litige
relève de la compétence exclusive des tribunaux français.
""".strip(),
    }


def render_cgu() -> Dict[str, str]:
    c = PLATFORM_LEGAL_INFO
    return {
        "title": "Conditions Générales d'Utilisation",
        "updated": _today(),
        "content": f"""
## Préambule

Les présentes Conditions Générales d'Utilisation (CGU) régissent l'accès et
l'utilisation de la plateforme **{c['platform_nom']}**, éditée par la Société
{c['platform_nom']} (SIREN {c['siren']}, siège social : {c['adresse']}).

## 1. Définitions

- **Plateforme** : le service en ligne accessible via {c['platform_site_web']}.
- **Utilisateur / Concepteur** : Utilisateur professionnel exploitant un ou
  plusieurs sites e-commerce via la Plateforme.
- **Éditeur** : la Société {c['platform_nom']}.

## 2. Inscription et compte

L'inscription est réservée aux professionnels. L'Utilisateur garantit
l'exactitude des informations fournies.

## 3. Services

{c['platform_nom']} met à disposition :
- Un moteur d'analyse de niches e-commerce,
- Un générateur de sites par IA,
- Un cockpit de gestion (catalogue, commandes, finance, SEO),
- Un système de paiement intégré (Mollie),
- Un accompagnement stratégique.

## 4. Obligations des Concepteurs

Le Concepteur s'engage à respecter les lois françaises et européennes
applicables (DGCCRF, RGPD, droit de la consommation).

## 5. Partage de la marge brute (50/50)

La marge brute hors taxes de chaque commande est partagée à parts égales entre
le Concepteur et l'Éditeur. Versements bi-mensuels par virement SEPA.

## 6. Résiliation

Préavis de 30 jours par e-mail à {c['platform_email']}.

## 7. Droit applicable

Droit français. Tribunaux du ressort du siège social de l'Éditeur.

## 8. Contact

**{c['platform_email']}** · {c['platform_telephone']}
""".strip(),
    }


def render_confidentialite() -> Dict[str, str]:
    c = PLATFORM_LEGAL_INFO
    return {
        "title": "Politique de confidentialité",
        "updated": _today(),
        "content": f"""
## 1. Responsable du traitement

La **Société {c['platform_nom']}** (SIREN {c['siren']}, siège : {c['adresse']})
est responsable du traitement de vos données.

**Contact** : {c['platform_email']}

## 2. Données collectées

Voir la version détaillée pour chaque boutique. En synthèse : identité,
coordonnées, commandes, données techniques.

## 3. Vos droits

Accès, rectification, effacement, opposition, portabilité, limitation, retrait
du consentement. Réponse sous 30 jours.

**Pour exercer vos droits** : {c['platform_email']}

## 4. Réclamation CNIL

https://www.cnil.fr — 3 place de Fontenoy, 75007 Paris.
""".strip(),
    }


def render_cookies() -> Dict[str, str]:
    c = PLATFORM_LEGAL_INFO
    return {
        "title": "Politique des cookies",
        "updated": _today(),
        "content": f"""
## 1. Cookies utilisés

### 1.1 Strictement nécessaires (pas de consentement)

| Nom | Finalité | Durée |
|---|---|---|
| `access_token` | Authentification de session (JWT) | 7 jours |
| `csrf_token` | Protection CSRF | Session |
| `altiaro_consent_v1` | Mémoriser vos choix | 13 mois |

### 1.2 Mesure d'audience (consentement requis)

| Nom | Finalité | Fournisseur |
|---|---|---|
| Google Analytics 4 | Mesure d'usage | Google LLC (US) |

## 2. Gérer vos préférences

Bannière à votre première visite + paramètres navigateur. Pour exercer vos
droits : {c['platform_email']}.
""".strip(),
    }


def get_legal_page(slug: str) -> Optional[Dict[str, str]]:
    """Return a platform-level legal page by slug (Altiaro itself), or None."""
    registry = {
        "mentions-legales": render_mentions_legales,
        "cgu":              render_cgu,
        "confidentialite":  render_confidentialite,
        "cookies":          render_cookies,
    }
    fn = registry.get(slug)
    return fn() if fn else None
