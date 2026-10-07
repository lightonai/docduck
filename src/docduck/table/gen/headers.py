"""Header sampling: localized from the Markov word pool plus literal
tokens (p-value, percent suffix)."""

import random

from ...defaults import DEFAULTS
from .words import _get_word_pool, _sample_phrase


def _sample_header(lang, col_type):
    """Generate a header for the given column type in `lang`.

    Literals (p-value, %) stay universal; other types sample from Markov.
    """
    cfg = DEFAULTS["table"]
    literals = cfg["header_literal_tokens"]

    if col_type == "pvalue":
        return random.choice(literals["pvalue"])

    n = 1 if random.random() < 0.75 else 2
    phrase = _sample_phrase(lang, n_words=n, max_chars=cfg["header_max_chars"])
    if phrase is None:
        # Model unavailable / empty: fall back to column type name
        return col_type.capitalize()

    if col_type == "percent":
        return phrase + literals["percent_suffix"]
    return phrase


def _sample_short_header(lang, col_type, max_chars=10):
    """Single short word localized header (or literal for pvalue).

    Enforces `max_chars`: unlike `_sample_phrase(n_words=1)`, which ignores it.
    """
    literals = DEFAULTS["table"]["header_literal_tokens"]
    if col_type == "pvalue":
        return random.choice(literals["pvalue"])
    budget = max_chars - (len(literals["percent_suffix"]) if col_type == "percent" else 0)
    pool = _get_word_pool(lang)
    short = [w for w in pool if len(w) <= budget] if pool else []
    if not short:
        return col_type.capitalize()[:max_chars]
    phrase = random.choice(short)
    if col_type == "percent":
        return phrase + literals["percent_suffix"]
    return phrase
