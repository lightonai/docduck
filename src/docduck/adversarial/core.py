"""Shared state and primitives for the adversarial text-transform package.

Holds the canonical `VALID_MODES` registry, the per-language typo wordsets /
alphabets, and small helpers reused across distortion families.
"""

from __future__ import annotations

import random
import re
from contextvars import ContextVar

VALID_MODES = (
    "natural",
    "scrambled",
    "confusables",
    "confusables_heavy",
    "digit_heavy",
    "digit_extreme",
    "famous_swap",
    "homophone_trap",
    "strikethrough",
    "pseudo",
    "gibberish",
    # Pixel-faithfulness probes: test whether the OCR transcribes exactly
    # what's on the page or silently normalizes. Each one has an unambiguous
    # ground-truth representation (no convention ambiguity).
    "all_caps",
    "mixed_case",
    "repeat_chars",
    "punct_storm",
    "leading_zeros",
    "diverse_typos",
    "precision_numbers",
    "foreign_names",
    "scientific_symbols",
    "critical_not",
    "factual_swap",
    "bold_typos",
    "typo_explained",
    "brand_swap",
    "homoglyph",
    "stutter",
    "mojibake",
    "leetspeak",
    "roman_numerals",
    "wide_kerning",
    "footnote_markers",
    "code_switching",
    "mixed_case_brand",
    "locale_numbers",
    "structured_ids",
    "date_formats",
    "lookalike_drugs",
    "citation_format",
    "hyphenation_breaks",
    "bullet_markers",
    "italic_emphasis",
    "greek_variables",
    "bidi_text",
    "mixed_script_word",
    "rare_currency",
    "highlighted_text",
    "long_urls",
    "emails",
    "strikethrough_emphasis",
    "whitespace_tabs",
    "all_caps_mid_sentence",
    "code_block",
    "postal_codes",
)


_VOWEL_CHARS = "aeiouAEIOU"

# Bare integer matcher used by leading_zeros and roman_numerals.
_NUMBER_RE = re.compile(r"(?<!\d)\d+(?!\d)")


def _esc_xml(s: str) -> str:
    """Minimal XML escape for content embedded in Pango markup."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Typo / mutation primitives (shared by diverse_typos and bold_typos).
# ---------------------------------------------------------------------------

# Per-language SCOWL-style wordlists shipped via apt (wamerican, wfrench,
# wngerman, wspanish, witalian, wportuguese). Used by diverse_typos to
# confirm a mutation produced a non-word. If a lang has no dict installed
# we degrade to the American-English baseline.
_LANG_DICTS = {
    "en": "/usr/share/dict/american-english",
    "fr": "/usr/share/dict/french",
    "de": "/usr/share/dict/ngerman",
    "es": "/usr/share/dict/spanish",
    "it": "/usr/share/dict/italian",
    "pt": "/usr/share/dict/portuguese",
}

_WORDSETS: dict[str, set[str]] = {}


def _load_wordset(lang: str = "en") -> set[str]:
    """Lazy-load a lowercase wordset for `lang`. Strips digits/punct lines
    (some lists include numerics). Returns empty set if dict is missing:
    diverse_typos degrades to a no-op in that case."""
    if lang not in _WORDSETS:
        path = _LANG_DICTS.get(lang, _LANG_DICTS["en"])
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                _WORDSETS[lang] = {
                    w.strip().lower() for w in f if w.strip() and not any(c.isdigit() for c in w)
                }
        except OSError:
            _WORDSETS[lang] = set()
    return _WORDSETS[lang]


# The composer sets this from PageConfig.lang so diverse_typos picks the
# right wordset. Default "en" keeps single-language users unaffected.
_typo_lang: ContextVar[str] = ContextVar("docduck_typo_lang", default="en")


def set_typo_lang(lang: str | None) -> None:
    """Set the language whose wordset diverse_typos should consult."""
    _typo_lang.set(lang or "en")


_TYPO_OPS = ("drop", "swap", "double", "substitute")

# Substitute alphabets per language. Diacritics included so French/German/
# Spanish/etc. typos look natural (a vowel can be swapped to any plausible
# in-language letter, not forced to ASCII). Drop/swap/double don't need
# the alphabet: they only rearrange existing characters.
_LANG_ALPHABETS = {
    "en": "abcdefghijklmnopqrstuvwxyz",
    "fr": "abcdefghijklmnopqrstuvwxyzàâçéèêëîïôûùüÿ",
    "de": "abcdefghijklmnopqrstuvwxyzäöüß",
    "es": "abcdefghijklmnopqrstuvwxyzñáéíóúü",
    "it": "abcdefghijklmnopqrstuvwxyzàèéìòù",
    "pt": "abcdefghijklmnopqrstuvwxyzáàâãéêíóôõúç",
}


def _mutate_word(word: str, rng: random.Random, alphabet: str | None = None) -> str | None:
    """Apply one random single-char mutation. Returns None if word too short."""
    if len(word) < 5:
        return None
    op = rng.choice(_TYPO_OPS)
    # Avoid touching the first/last char so the word stays recognizable.
    i = rng.randint(1, len(word) - 2)
    if op == "drop":
        return word[:i] + word[i + 1 :]
    if op == "swap":
        if i + 1 >= len(word):
            return None
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if op == "double":
        return word[:i] + word[i] + word[i:]
    if op == "substitute":
        pool = alphabet or _LANG_ALPHABETS["en"]
        choices = pool.replace(word[i].lower(), "")
        if not choices:
            return None
        return word[:i] + rng.choice(choices) + word[i + 1 :]
    return None


def _split_word_punct(w: str) -> tuple[str, str, str]:
    """Strip surrounding non-alpha punctuation. Returns (lead, core, tail)."""
    i = 0
    while i < len(w) and not w[i].isalpha():
        i += 1
    j = len(w)
    while j > i and not w[j - 1].isalpha():
        j -= 1
    return w[:i], w[i:j], w[j:]
