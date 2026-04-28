"""Phase D' — Mapping pays → langue + devise (avec parité 1:1 EUR/GBP)."""
COUNTRY_TO_LANG = {
    "FR":"fr","BE":"fr","CH":"fr","LU":"fr","MC":"fr",
    "GB":"en","IE":"en","US":"en","CA":"en","AU":"en","NZ":"en",
    "DE":"de","AT":"de",
    "NL":"nl",
    "IT":"it",
    "ES":"es",
}
COUNTRY_TO_CURRENCY = {"GB":"GBP"}  # 1:1 EUR sinon
DEFAULT_CURRENCY = "EUR"
DEFAULT_LANG = "fr"
CURRENCY_SYMBOL = {"EUR":"€","GBP":"£","USD":"$","CHF":"CHF"}


def detect(country: str | None, fallback_lang: str = DEFAULT_LANG):
    c = (country or "").upper().strip() or None
    return {
        "country": c,
        "language": COUNTRY_TO_LANG.get(c, fallback_lang) if c else fallback_lang,
        "currency": COUNTRY_TO_CURRENCY.get(c, DEFAULT_CURRENCY),
        "currency_symbol": CURRENCY_SYMBOL.get(COUNTRY_TO_CURRENCY.get(c, DEFAULT_CURRENCY), "€"),
    }
