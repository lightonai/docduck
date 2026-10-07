"""Cross-language and token-shape probes.

Grab-bag of modes that splice in foreign-language sentences, duplicate
tokens, or insert URL / email tokens with unusual punctuation.
"""

from __future__ import annotations

import random
import re

# ---------------------------------------------------------------------------
# Code-switching: splice short foreign-language sentences into English
# Markov prose. Tests whether OCR's language-detection front-end treats
# the foreign segment as the same language, transcribes accents
# correctly, or "fixes" the foreign words.
# ---------------------------------------------------------------------------

_CODE_SWITCH_PHRASES: list[tuple[str, str]] = [
    # (language code, phrase)
    ("fr", "Je ne sais pas où il est allé."),
    ("fr", "C'est une très bonne idée pour résoudre le problème."),
    ("fr", "Nous avons rendez-vous demain matin à huit heures."),
    ("fr", "Le café est délicieux mais un peu trop fort."),
    ("es", "No tengo idea de dónde está mi llave."),
    ("es", "El mañana traerá nuevas oportunidades para todos."),
    ("es", "La paella es la especialidad de la casa."),
    ("es", "Vamos a la playa este fin de semana sin falta."),
    ("de", "Ich weiß nicht, wo ich heute essen soll."),
    ("de", "Die Universität bietet sehr interessante Kurse an."),
    ("de", "Können Sie mir bitte den Weg zum Bahnhof zeigen?"),
    ("de", "Das Wetter wird morgen wieder besser werden."),
    ("it", "Non capisco perché tu sia così arrabbiato adesso."),
    ("it", "Domani andremo a Firenze per visitare gli Uffizi."),
    ("pt", "Eu não sei onde fica a estação de trem mais próxima."),
    ("pt", "Vamos almoçar juntos amanhã se você puder."),
]


def code_switching_text(text: str, sentence_prob: float = 0.15) -> str:
    """Insert a foreign-language sentence after every Nth English sentence."""
    rng = random.Random(random.getrandbits(64))
    parts = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for p in parts:
        out.append(p)
        if rng.random() < sentence_prob:
            _, phrase = rng.choice(_CODE_SWITCH_PHRASES)
            out.append(phrase)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Stutter: duplicate ~10% of word tokens ("the the cat sat"). LM-trained
# OCRs often silently de-duplicate; a faithful OCR keeps the repetition.
# ---------------------------------------------------------------------------


def stutter_text(text: str, word_prob: float = 0.12) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        out.append(w)
        # Don't double pure punctuation, and skip the very last sentence-
        # terminator so the paragraph still looks paragraph-shaped.
        if any(c.isalpha() for c in w) and len(w) >= 3 and rng.random() < word_prob:
            # Lowercase the duplicate so we don't end up with double capitals
            # mid-sentence (more natural-looking stutter).
            dup = w[0].lower() + w[1:] if w[0].isupper() and not w.isupper() else w
            out.append(dup)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Long URLs with query parameters. Tests special-char preservation.
# ---------------------------------------------------------------------------

_URL_HOSTS = [
    "example.com",
    "github.com",
    "ourservice.net",
    "data.gov",
    "tracker.io",
]
_URL_PATHS = ["api/v1/items", "resources/data", "search", "docs/manual"]


def long_urls_text(text: str, word_prob: float = 0.06) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 5 and rng.random() < word_prob:
            host = rng.choice(_URL_HOSTS)
            path = rng.choice(_URL_PATHS)
            params = "&".join(
                f"{k}={rng.randint(100, 99999)}"
                for k in rng.sample(
                    ["id", "utm_source", "session", "ref", "page", "lang"],
                    k=rng.randint(2, 4),
                )
            )
            out.append(f"https://{host}/{path}?{params}")
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Email addresses with unusual characters (dots, plus tags, hyphenated).
# ---------------------------------------------------------------------------

_EMAIL_LOCAL = [
    "john.smith",
    "user+tag",
    "first-last",
    "j.k.rowling",
    "a.b.c",
    "user_name",
    "support+ticket-42",
]
_EMAIL_DOMAIN = [
    "example.co.uk",
    "company.io",
    "subdomain.org.au",
    "mail.gov.fr",
    "host.net",
]


def emails_text(text: str, word_prob: float = 0.06) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            local = rng.choice(_EMAIL_LOCAL)
            domain = rng.choice(_EMAIL_DOMAIN)
            out.append(f"{local}@{domain}")
        else:
            out.append(w)
    return " ".join(out)
