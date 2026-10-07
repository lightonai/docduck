"""Visual-twin character substitutions.

Four modes share a "same shape, different codepoint" theme:
  - confusables: ASCII pairs like l/I, O/0, rn/m, cl/d
  - digit_heavy: letters → visually-similar digits (i→1, o→0, e→3, …)
  - homoglyph:   Latin letters → Cyrillic/Greek look-alikes
  - leetspeak:   guided letter→digit at common positions

A pixel-faithful OCR transcribes the literal codepoint that was on the page;
a prior-biased OCR silently normalizes back to the original letter.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Confusables: swap characters to their visual twins
# ---------------------------------------------------------------------------

_CONFUSABLES = {
    "l": "I",
    "I": "l",
    "O": "0",
    "o": "0",
    "0": "O",
    "1": "l",
    "5": "S",
    "S": "5",
    "8": "B",
    "B": "8",
    "rn": "m",
    "m": "rn",
    "cl": "d",
}


def confusables_text(text: str, swap_probability: float = 0.08) -> str:
    """Swap a fraction of characters to visual twins. Preserves word count + length
    (except for rn/m and cl/d which change length slightly).
    """
    out_chars: list[str] = []
    i = 0
    while i < len(text):
        swapped = False
        if i + 1 < len(text):
            pair = text[i : i + 2]
            if pair in _CONFUSABLES and random.random() < swap_probability:
                out_chars.extend(list(_CONFUSABLES[pair]))
                i += 2
                swapped = True
        if not swapped:
            ch = text[i]
            if ch in _CONFUSABLES and random.random() < swap_probability:
                out_chars.append(_CONFUSABLES[ch])
            else:
                out_chars.append(ch)
            i += 1
    return "".join(out_chars)


# ---------------------------------------------------------------------------
# Digit-heavy: aggressive letter-to-digit swaps (i/1, o/0, l/1, e/3, etc.)
# ---------------------------------------------------------------------------

_DIGIT_SWAPS = {
    "i": "1",
    "I": "1",
    "l": "1",
    "o": "0",
    "O": "0",
    "e": "3",
    "E": "3",
    "a": "4",
    "A": "4",
    "s": "5",
    "S": "5",
    "g": "9",
    "G": "6",
    "t": "7",
    "T": "7",
    "b": "6",
    "B": "8",
    "z": "2",
    "Z": "2",
}


def digit_heavy_text(text: str, swap_probability: float = 0.40) -> str:
    """Swap letters to visually-similar digits at high rate (leet-speak-ish).

    At 40% swap probability the text is still readable to humans but a strong
    prior-based OCR may silently restore the original letters.
    """
    return "".join(
        _DIGIT_SWAPS[ch] if ch in _DIGIT_SWAPS and random.random() < swap_probability else ch
        for ch in text
    )


# ---------------------------------------------------------------------------
# Homoglyph injection: replace Latin chars with visually identical
# Cyrillic / Greek codepoints. The page looks unchanged to a human; a
# pixel-faithful OCR keeps the codepoint, a prior-leaning OCR silently
# normalises to Latin.
# ---------------------------------------------------------------------------

_HOMOGLYPHS: dict[str, str] = {
    # Latin -> Cyrillic visual twin (preferred, Cyrillic block is denser)
    "a": "а",  # CYRILLIC SMALL LETTER A
    "c": "с",  # CYRILLIC SMALL LETTER ES
    "e": "е",  # CYRILLIC SMALL LETTER IE
    "o": "о",  # CYRILLIC SMALL LETTER O
    "p": "р",  # CYRILLIC SMALL LETTER ER
    "x": "х",  # CYRILLIC SMALL LETTER HA
    "y": "у",  # CYRILLIC SMALL LETTER U
    "A": "А",  # CYRILLIC CAPITAL LETTER A
    "B": "В",  # CYRILLIC CAPITAL LETTER VE
    "C": "С",  # CYRILLIC CAPITAL LETTER ES
    "E": "Е",  # CYRILLIC CAPITAL LETTER IE
    "H": "Н",  # CYRILLIC CAPITAL LETTER EN
    "K": "К",  # CYRILLIC CAPITAL LETTER KA
    "M": "М",  # CYRILLIC CAPITAL LETTER EM
    "O": "О",  # CYRILLIC CAPITAL LETTER O
    "P": "Р",  # CYRILLIC CAPITAL LETTER ER
    "T": "Т",  # CYRILLIC CAPITAL LETTER TE
    "X": "Х",  # CYRILLIC CAPITAL LETTER HA
}


def homoglyph_text(text: str, char_prob: float = 0.12) -> str:
    """Replace ~char_prob of eligible Latin chars with Cyrillic look-alikes.

    Restricted to characters inside words (won't touch the first char of a
    word or surrounding punctuation: keeps tokenisation stable).
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) < 3:
            out.append(w)
            continue
        chars = list(w)
        # Skip char[0] so word-initial caps are preserved and tokenisation
        # boundaries don't shift visually.
        for i in range(1, len(chars)):
            c = chars[i]
            twin = _HOMOGLYPHS.get(c)
            if twin is not None and rng.random() < char_prob:
                chars[i] = twin
        out.append("".join(chars))
    return " ".join(out)


# ---------------------------------------------------------------------------
# Leetspeak: selective digit-for-letter substitution at common positions.
# Tests whether OCR transcribes the literal digit (faithful) or "fixes" to
# the original letter (LM prior + pattern recognition). Different from
# digit_heavy which is random; this is GUIDED at common leet positions so
# every fix decision is unambiguous.
# ---------------------------------------------------------------------------

_LEET_MAP: dict[str, str] = {
    "a": "4",
    "e": "3",
    "o": "0",
    "i": "1",
    "s": "5",
    "t": "7",
    "l": "1",
    "b": "8",
    "g": "9",
}


def leetspeak_text(text: str, char_prob: float = 0.40) -> str:
    """Replace ~char_prob of eligible letters with the leet digit twin.

    Only touches eligible letters; word lengths preserved; first char of
    each word skipped to keep word-shape signal intact.
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) < 4:
            out.append(w)
            continue
        chars = list(w)
        for i in range(1, len(chars)):
            c = chars[i].lower()
            twin = _LEET_MAP.get(c)
            if twin is not None and rng.random() < char_prob:
                chars[i] = twin
        out.append("".join(chars))
    return " ".join(out)
