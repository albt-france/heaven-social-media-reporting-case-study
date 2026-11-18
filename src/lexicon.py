"""Rule-based sentiment and theme tagging in 5 languages (FR, EN, DE, ES, IT). No LLM, no download, no key.

Method (kept simple on purpose, so every score can be explained):
- text lower-cased, accents kept, split into words;
- sentiment = (positive words - negative words) / max(1, positive + negative), in [-1, 1];
  a negation word up to 2 tokens before a sentiment word flips it ("pas bon", "not good", "nicht gut");
- a comment is "positive" above +0.25, "negative" below -0.25, otherwise "neutral";
- themes = keyword stems per theme; a text can carry several themes.
Limits: no sarcasm, no emoji meaning beyond a few, short lexicons. Good enough to rank markets and spot spikes,
not to quote a precise sentiment level. Validated on a hand-labelled sample in the notebook.
"""
from __future__ import annotations

import re

POS = {
    "en": "love loved lovely great amazing perfect best beautiful gorgeous glowing soft smooth recommend obsessed favourite favorite nice good happy works effective holy grail",
    "fr": "adore adoré aime j'aime top parfait parfaite génial géniale magnifique sublime doux douce recommande efficace super bien bon bonne meilleur meilleure incroyable canon",
    "de": "liebe toll super perfekt schön wunderschön weich empfehle wirksam gut beste großartig genial lieblingsprodukt klasse",
    "es": "encanta amo perfecto perfecta genial precioso preciosa suave recomiendo eficaz bueno buena mejor increíble maravilloso",
    "it": "adoro amo perfetto perfetta fantastico bellissimo bellissima morbido consiglio efficace buono buona migliore stupendo top",
}
NEG = {
    "en": "hate bad worst awful terrible broke breakout irritation itchy disappointed disappointing waste expensive overpriced sticky greasy fake unavailable sold-out",
    "fr": "déteste nul nulle horrible déçu déçue décevant décevante cher chère arnaque irritation boutons gras collant rupture introuvable indisponible",
    "de": "hasse schlecht schrecklich enttäuscht enttäuschend teuer irritation pickel klebrig ausverkauft nicht-verfügbar mist",
    "es": "odio malo mala horrible decepcionado decepcionada caro cara irritación granos pegajoso agotado agotada estafa",
    "it": "odio brutto brutta pessimo pessima deluso delusa caro cara irritazione brufoli appiccicoso esaurito esaurita truffa",
}
NEGATORS = {"not", "no", "never", "don't", "doesn't", "isn't", "pas", "jamais", "plus", "nicht", "kein", "keine", "nunca",
            "nada", "non", "mai"}
EMOJI_POS, EMOJI_NEG = set("😍🥰❤✨💖👍🔥😊"), set("😡👎😭😤💔🤮")

THEMES = {
    "price_promo": r"price|prix|preis|precio|prezzo|promo|discount|réduc|soldes|rabatt|oferta|sconto|sale|cher|teuer|caro|cheap",
    "stock_availability": r"stock|rupture|sold.?out|ausverkauft|agotad|esaurit|unavailable|indisponible|introuvable|restock|back in",
    "efficacy_skin": r"skin|peau|haut|piel|pelle|acne|acné|boutons|pickel|granos|brufoli|hydrat|feucht|idrat|glow|wrinkle|ride|spf|sunscreen|solaire",
    "texture_shade": r"shade|teinte|farbton|tono|tonalit|texture|textur|textura|consistenza|finish|matte|mat\b|coverage|couvrance",
    "ingredients_clean": r"ingredient|ingrédient|inhaltsstoff|ingrediente|vegan|clean|cruelty|parfum-free|fragrance.?free|natural|naturel|natürlich|natural",
    "creator_content": r"tutorial|tuto|grwm|routine|review|avis|haul|influenc|creator|créat|unboxing|swatch",
    "service_delivery": r"deliver|livraison|lieferung|envío|envio|spedizione|order|commande|bestellung|pedido|ordine|customer service|sav",
}


def tokens(text: str) -> list[str]:
    return re.findall(r"[\w'\-]+", (text or "").lower())


def sentiment_score(text: str, lang: str = "en") -> float:
    toks = tokens(text)
    lex_p = set().union(*(set(v.split()) for v in POS.values()))
    lex_n = set().union(*(set(v.split()) for v in NEG.values()))
    p = n = 0
    for i, t in enumerate(toks):
        val = 1 if t in lex_p else -1 if t in lex_n else 0
        if val and any(w in NEGATORS for w in toks[max(0, i - 2):i]):
            val = -val
        p += val > 0
        n += val < 0
    p += sum(ch in EMOJI_POS for ch in text or "")
    n += sum(ch in EMOJI_NEG for ch in text or "")
    return round((p - n) / max(1, p + n), 3)


def label(score: float) -> str:
    return "positive" if score > 0.25 else "negative" if score < -0.25 else "neutral"


def classify_themes(text: str) -> dict[str, bool]:
    low = (text or "").lower()
    return {k: bool(re.search(rx, low)) for k, rx in THEMES.items()}
