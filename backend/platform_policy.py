"""Altiaro platform-wide constants — NOT editable by Concepteurs.

These values are the commercial policy of the Altiaro platform and apply
identically to ALL sites. They are returned read-only to the Concepteur
via /api/sites/:id/policy and to the storefront via /api/public/sites/:id/policy.
"""

PLATFORM_POLICY = {
    "taxes": {
        "regime": "tva_standard",  # standard 20% FR + OSS UE
        "rates_by_country": {
            "FR": 20.0,
            "BE": 21.0,
            "LU": 17.0,
            "DE": 19.0,
            "NL": 21.0,
            "CH": 0.0,   # hors UE, facturation HT
            "UK": 20.0,  # hors UE, TVA équivalente
        },
        "oss_enabled": True,
        "explanation": (
            "Taux appliqués automatiquement par Altiaro selon le pays de livraison. "
            "Régime OSS UE activé par défaut (seuil 10k€/an géré par la plateforme)."
        ),
    },
    "shipping": {
        "policy": "free_everywhere",
        "label": "Livraison offerte",
        "covered_countries": ["FR", "BE", "LU", "DE", "NL", "CH", "UK"],
        "delivery_estimate": {
            "FR": "2-4 jours ouvrés",
            "BE": "3-5 jours ouvrés",
            "LU": "3-5 jours ouvrés",
            "DE": "4-6 jours ouvrés",
            "NL": "4-6 jours ouvrés",
            "CH": "5-8 jours ouvrés (hors UE)",
            "UK": "5-8 jours ouvrés (hors UE)",
        },
        "explanation": (
            "Altiaro offre la livraison sur tous les sites, dans les 7 marchés couverts. "
            "Les frais sont absorbés par la marge plateforme. Les Concepteurs ne paramètrent rien."
        ),
    },
    "payment": {
        "provider": "Mollie",
        "methods_enabled": [
            "creditcard",      # Visa, Mastercard, Amex
            "bancontact",      # BE
            "ideal",           # NL
            "applepay",
            "googlepay",
            "paypal",          # via Mollie
        ],
        "b2b_bank_transfer_min": 500.0,
        "explanation": (
            "Tous les sites Altiaro acceptent les mêmes méthodes de paiement via Mollie. "
            "Virement B2B activé automatiquement pour les paniers >= 500€. "
            "Aucun paramétrage côté Concepteur."
        ),
    },
    "returns": {
        "policy": "14_days_no_reason",
        "label": "Retour gratuit sous 14 jours",
        "shipping_paid_by": "altiaro",  # Altiaro prend en charge le retour
        "explanation": (
            "Rétractation légale 14 jours + frais de retour pris en charge par Altiaro "
            "(inclus dans la marge plateforme)."
        ),
    },
    "warranty": {
        "years": 2,
        "label": "Garantie 2 ans incluse",
        "explanation": "Garantie légale de conformité (2 ans) appliquée sur tous les produits.",
    },
    "customer_service": {
        "hours": "9h-18h du lundi au vendredi",
        "response_time_sla": "2h ouvrées",
        "channels": ["email", "chat", "phone"],
        "language_support": ["fr"],
    },
}


def get_platform_policy() -> dict:
    return PLATFORM_POLICY
