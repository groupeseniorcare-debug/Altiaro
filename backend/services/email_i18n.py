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
    # ────────────────────────────────────────────────────────────────────
    # Sprint 2.4 finalisation — strings utilisées par routes/emails.py
    # ────────────────────────────────────────────────────────────────────
    "order_confirmation.title_with_name": {
        "fr": "Merci pour votre commande, {customer_name} !",
        "en": "Thank you for your order, {customer_name}!",
        "de": "Vielen Dank für Ihre Bestellung, {customer_name}!",
        "nl": "Bedankt voor uw bestelling, {customer_name}!",
        "it": "Grazie per il tuo ordine, {customer_name}!",
        "es": "¡Gracias por tu pedido, {customer_name}!",
    },
    "order_confirmation.confirmed_text": {
        "fr": "Votre commande <strong>#{order_number}</strong> a été confirmée. Nous préparons l'expédition et vous recevrez un email dès qu'elle partira.",
        "en": "Your order <strong>#{order_number}</strong> has been confirmed. We're preparing the shipment and will email you as soon as it's on its way.",
        "de": "Ihre Bestellung <strong>#{order_number}</strong> wurde bestätigt. Wir bereiten den Versand vor und melden uns per E-Mail, sobald sie unterwegs ist.",
        "nl": "Uw bestelling <strong>#{order_number}</strong> is bevestigd. We bereiden de verzending voor en sturen u een e-mail zodra deze onderweg is.",
        "it": "Il tuo ordine <strong>#{order_number}</strong> è stato confermato. Stiamo preparando la spedizione e ti avviseremo via email non appena partirà.",
        "es": "Tu pedido <strong>#{order_number}</strong> ha sido confirmado. Estamos preparando el envío y te enviaremos un correo en cuanto salga.",
    },
    "order_confirmation.your_order": {
        "fr": "Votre commande", "en": "Your order", "de": "Ihre Bestellung",
        "nl": "Uw bestelling", "it": "Il tuo ordine", "es": "Tu pedido",
    },
    "order_confirmation.subtotal": {
        "fr": "Sous-total", "en": "Subtotal", "de": "Zwischensumme",
        "nl": "Subtotaal", "it": "Subtotale", "es": "Subtotal",
    },
    "order_confirmation.shipping": {
        "fr": "Livraison", "en": "Shipping", "de": "Versand",
        "nl": "Verzending", "it": "Spedizione", "es": "Envío",
    },
    "order_confirmation.tax": {
        "fr": "TVA", "en": "VAT", "de": "MwSt.",
        "nl": "Btw", "it": "IVA", "es": "IVA",
    },
    "order_confirmation.quantity": {
        "fr": "Quantité", "en": "Quantity", "de": "Menge",
        "nl": "Aantal", "it": "Quantità", "es": "Cantidad",
    },
    "order_confirmation.track_my_order": {
        "fr": "Suivre ma commande", "en": "Track my order", "de": "Bestellung verfolgen",
        "nl": "Bestelling volgen", "it": "Segui il mio ordine", "es": "Seguir mi pedido",
    },
    "order_confirmation.legal_notice": {
        "fr": "Paiement opéré par Altiaro SAS (France) pour le compte de {brand}.",
        "en": "Payment processed by Altiaro SAS (France) on behalf of {brand}.",
        "de": "Zahlung abgewickelt von Altiaro SAS (Frankreich) im Auftrag von {brand}.",
        "nl": "Betaling verwerkt door Altiaro SAS (Frankrijk) namens {brand}.",
        "it": "Pagamento elaborato da Altiaro SAS (Francia) per conto di {brand}.",
        "es": "Pago procesado por Altiaro SAS (Francia) en nombre de {brand}.",
    },
    "order_confirmation.security_notice": {
        "fr": "Cet email est envoyé à l'adresse indiquée lors du paiement. Si vous ne reconnaissez pas cette commande, contactez-nous immédiatement.",
        "en": "This email is sent to the address provided during payment. If you don't recognize this order, contact us immediately.",
        "de": "Diese E-Mail wird an die bei der Zahlung angegebene Adresse gesendet. Falls Sie diese Bestellung nicht erkennen, kontaktieren Sie uns bitte sofort.",
        "nl": "Deze e-mail wordt gestuurd naar het adres dat tijdens de betaling is opgegeven. Als u deze bestelling niet herkent, neem dan onmiddellijk contact met ons op.",
        "it": "Questa email viene inviata all'indirizzo fornito durante il pagamento. Se non riconosci questo ordine, contattaci immediatamente.",
        "es": "Este correo se envía a la dirección proporcionada durante el pago. Si no reconoces este pedido, contáctanos inmediatamente.",
    },
    "order_confirmation.preheader": {
        "fr": "Votre commande #{order_number} est confirmée",
        "en": "Your order #{order_number} is confirmed",
        "de": "Ihre Bestellung #{order_number} ist bestätigt",
        "nl": "Uw bestelling #{order_number} is bevestigd",
        "it": "Il tuo ordine #{order_number} è confermato",
        "es": "Tu pedido #{order_number} está confirmado",
    },
    "shipping_update.title_with_name": {
        "fr": "📦 Votre commande est expédiée, {customer_name} !",
        "en": "📦 Your order has shipped, {customer_name}!",
        "de": "📦 Ihre Bestellung wurde versendet, {customer_name}!",
        "nl": "📦 Uw bestelling is verzonden, {customer_name}!",
        "it": "📦 Il tuo ordine è stato spedito, {customer_name}!",
        "es": "📦 ¡Tu pedido ha sido enviado, {customer_name}!",
    },
    "shipping_update.body_text": {
        "fr": "Bonne nouvelle : la commande <strong>#{order_number}</strong> est partie chez {carrier}.",
        "en": "Good news: order <strong>#{order_number}</strong> is on its way with {carrier}.",
        "de": "Gute Nachrichten: Bestellung <strong>#{order_number}</strong> ist bei {carrier} unterwegs.",
        "nl": "Goed nieuws: bestelling <strong>#{order_number}</strong> is onderweg met {carrier}.",
        "it": "Buone notizie: l'ordine <strong>#{order_number}</strong> è in viaggio con {carrier}.",
        "es": "Buenas noticias: el pedido <strong>#{order_number}</strong> está en camino con {carrier}.",
    },
    "shipping_update.help_text": {
        "fr": "La livraison peut prendre quelques jours ouvrés. En cas de problème, contactez-nous — nous sommes là pour vous aider.",
        "en": "Delivery may take a few business days. If there's an issue, contact us — we're here to help.",
        "de": "Die Lieferung kann einige Werktage dauern. Bei Problemen melden Sie sich gern bei uns.",
        "nl": "De levering kan enkele werkdagen duren. Bij problemen, neem contact met ons op — we helpen graag.",
        "it": "La consegna può richiedere alcuni giorni lavorativi. In caso di problemi, contattaci — siamo qui per aiutarti.",
        "es": "La entrega puede tardar algunos días hábiles. Si hay algún problema, contáctanos — estamos aquí para ayudarte.",
    },
    "shipping_update.preheader": {
        "fr": "Expédition #{order_number} — suivi {tracking}",
        "en": "Shipment #{order_number} — tracking {tracking}",
        "de": "Versand #{order_number} — Sendung {tracking}",
        "nl": "Verzending #{order_number} — tracking {tracking}",
        "it": "Spedizione #{order_number} — tracking {tracking}",
        "es": "Envío #{order_number} — seguimiento {tracking}",
    },
    "shipping_update.default_carrier": {
        "fr": "votre transporteur", "en": "your carrier", "de": "Ihr Spediteur",
        "nl": "uw vervoerder", "it": "il tuo corriere", "es": "tu transportista",
    },
    "shell.greeting_fallback": {
        "fr": "Bonjour", "en": "Hello", "de": "Guten Tag",
        "nl": "Hallo", "it": "Salve", "es": "Hola",
    },
    "shell.contact_us_html": {
        "fr": 'Une question ? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Contactez-nous</a>',
        "en": 'Any questions? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Contact us</a>',
        "de": 'Fragen? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Kontaktieren Sie uns</a>',
        "nl": 'Vragen? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Neem contact met ons op</a>',
        "it": 'Domande? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Contattaci</a>',
        "es": '¿Preguntas? <a href="{contact_url}" style="color:{primary};text-decoration:none;">Contáctanos</a>',
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
