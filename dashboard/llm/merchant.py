"""Stable merchant keys: bank concepts for the same shop differ in dates, cards and references."""

import re
import unicodedata

# Generic movement labels the bank puts in front of the merchant, longest first.
_PREFIXES = (
    "liquidacion periodica",
    "pago con tarjeta en",
    "pago movil en",
    "transferencia a favor de",
    "transferencia de",
    "transferencia a",
    "compra en",
    "bizum de",
    "bizum a",
    "adeudo",
    "recibo",
    "compra",
    "cargo",
)
_STOPWORDS = {"recibo", "ref", "referencia", "numero", "de", "del", "la", "el", "los", "las", "en", "et", "sa", "sl", "sau", "slu", "tarj", "tarjeta"}
_MAX_TOKENS = 3


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def merchant_key(concept: str) -> str:
    """Lowercase merchant tokens without prefixes, digits, cities, cards or references.

    'Pago Movil En Lush Alcala, Madrid, Tarj. :*0000' -> 'lush alcala'. Empty when nothing is left.
    """
    text = _plain(concept).split(",")[0].strip()
    for prefix in _PREFIXES:
        if text.startswith(prefix + " ") or text == prefix:
            text = text[len(prefix) :].strip()
            break
    tokens = [t for t in re.sub(r"[^a-z ]+", " ", text).split() if len(t) > 1 and t not in _STOPWORDS]
    return " ".join(tokens[:_MAX_TOKENS])
