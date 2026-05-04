"""Sprint 2.4 — Emails Resend i18n (6 langues : fr, en, de, nl, it, es).

Le système existant dans `routes/emails.py` produit les 3 emails clients
(order_confirmation, shipping_update, admin_new_order) en français fixe.
Cette couche fournit une table de traductions des strings clés pour
toutes les langues supportées.

Usage :
    from services.email_i18n import t, LANGS

    subject = t("order_confirmation.subject", lang="de", brand="Altea")
    title = t("order_confirmation.title", lang="de", brand="Altea")

La langue sélectionnée est : `order.customer.lang` (si dispo), sinon
`site.primary_locale[:2]`, sinon 'fr'.
"""
from __future__ import annotations

from typing import Any, Dict

LANGS = ("fr", "en", "de", "nl", "it", "es")

# ─────────────────────────────────────────────────────────────────────
# Translation table
# ─────────────────────────────────────────────────────────────────────
STRINGS: Dict[str, Dict[str, str]] = {
    "order_confirmation.subject": {
        "fr": "Votre commande {brand} est confirmée",
        "en": "Your {brand} order is confirmed",
        "de": "Ihre {brand} Bestellung ist bestätigt",
        "nl": "Uw {brand}-bestelling is bevestigd",
        "it": "Il tuo ordine {brand} è confermato",
        "es": "Tu pedido {brand} está confirmado",
    },
    "order_confirmation.title": {
        "fr": "Merci pour votre commande",
        "en": "Thank you for your order",
        "de": "Vielen Dank für Ihre Bestellung",
        "nl": "Bedankt voor uw bestelling",
        "it": "Grazie per il tuo ordine",
        "es": "Gracias por tu pedido",
    },
    "order_confirmation.intro": {
        "fr": "Nous avons bien reçu votre commande #{order_number} et préparons son expédition.",
        "en": "We have received your order #{order_number} and are preparing its shipment.",
        "de": "Wir haben Ihre Bestellung #{order_number} erhalten und bereiten den Versand vor.",
        "nl": "We hebben uw bestelling #{order_number} ontvangen en bereiden de verzending voor.",
        "it": "Abbiamo ricevuto il tuo ordine #{order_number} e stiamo preparando la spedizione.",
        "es": "Hemos recibido tu pedido #{order_number} y estamos preparando el envío.",
    },
    "order_confirmation.summary_title": {
        "fr": "Récapitulatif", "en": "Order summary", "de": "Bestellübersicht",
        "nl": "Besteloverzicht", "it": "Riepilogo ordine", "es": "Resumen del pedido",
    },
    "order_confirmation.total": {
        "fr": "Total", "en": "Total", "de": "Gesamt",
        "nl": "Totaal", "it": "Totale", "es": "Total",
    },
    "order_confirmation.shipping_to": {
        "fr": "Livraison à", "en": "Shipping to", "de": "Versand an",
        "nl": "Verzending naar", "it": "Spedizione a", "es": "Envío a",
    },
    "order_confirmation.track": {
        "fr": "Suivre ma commande", "en": "Track my order", "de": "Bestellung verfolgen",
        "nl": "Bestelling volgen", "it": "Segui il mio ordine", "es": "Seguir mi pedido",
    },
    "order_confirmation.help": {
        "fr": "Une question ? Répondez simplement à cet email.",
        "en": "Any questions? Just reply to this email.",
        "de": "Fragen? Antworten Sie einfach auf diese E-Mail.",
        "nl": "Vragen? Beantwoord gewoon deze e-mail.",
        "it": "Domande? Rispondi semplicemente a questa email.",
        "es": "¿Preguntas? Simplemente responde a este correo.",
    },
    "shipping_update.subject": {
        "fr": "Votre commande {brand} est expédiée",
        "en": "Your {brand} order has shipped",
        "de": "Ihre {brand}-Bestellung wurde versendet",
        "nl": "Uw {brand}-bestelling is verzonden",
        "it": "Il tuo ordine {brand} è stato spedito",
        "es": "Tu pedido {brand} ha sido enviado",
    },
    "shipping_update.title": {
        "fr": "Votre colis est en route",
        "en": "Your parcel is on its way",
        "de": "Ihr Paket ist unterwegs",
        "nl": "Uw pakket is onderweg",
        "it": "Il tuo pacco è in viaggio",
        "es": "Tu paquete está en camino",
    },
    "shipping_update.tracking_label": {
        "fr": "Numéro de suivi", "en": "Tracking number", "de": "Sendungsnummer",
        "nl": "Trackingnummer", "it": "Numero di tracciamento", "es": "Número de seguimiento",
    },
    "shipping_update.carrier": {
        "fr": "Transporteur", "en": "Carrier", "de": "Spediteur",
        "nl": "Vervoerder", "it": "Corriere", "es": "Transportista",
    },
    "shipping_update.track": {
        "fr": "Suivre mon colis", "en": "Track my parcel", "de": "Paket verfolgen",
        "nl": "Pakket volgen", "it": "Segui il mio pacco", "es": "Seguir mi paquete",
    },
    "footer.thanks": {
        "fr": "L'équipe {brand}", "en": "The {brand} team", "de": "Das {brand} Team",
        "nl": "Het {brand}-team", "it": "Il team {brand}", "es": "El equipo {brand}",
    },
    "footer.unsubscribe": {
        "fr": "Se désinscrire", "en": "Unsubscribe", "de": "Abbestellen",
        "nl": "Uitschrijven", "it": "Annulla iscrizione", "es": "Darse de baja",
    },
}


def normalize_lang(raw: Any) -> str:
    """Accept 'fr', 'FR', 'fr-FR', 'fr_FR' and return the 2-letter code or 'fr'."""
    s = str(raw or "fr").lower().replace("_", "-")
    code = s.split("-")[0][:2]
    return code if code in LANGS else "fr"


def t(key: str, *, lang: str = "fr", **kwargs: Any) -> str:
    """Translate a key with {placeholder} interpolation."""
    lang = normalize_lang(lang)
    row = STRINGS.get(key)
    if not row:
        return key
    tpl = row.get(lang) or row.get("fr") or key
    try:
        return tpl.format(**kwargs)
    except Exception:
        return tpl


def detect_order_lang(order: Dict[str, Any], site: Dict[str, Any]) -> str:
    """Pick the best language code for an order email."""
    customer = (order or {}).get("customer") or {}
    for candidate in (customer.get("lang"),
                      customer.get("locale"),
                      (order or {}).get("locale"),
                      (site or {}).get("primary_locale"),
                      (site or {}).get("locale")):
        if candidate:
            return normalize_lang(candidate)
    return "fr"
