"""Programmatic per-word typo injectors.

Unlike `phrases.py`'s curated typo sentences, these mutate live Markov
words at render time so each page gets a unique typo vocabulary. The
mutation primitives and per-language wordsets live in `core.py`.

  - diverse_typos:      plain non-word typo injection
  - bold_typos:         same mutation, wrapped in <b>...</b> Pango markup
  - hyphenation_breaks: insert mid-word hyphen at a soft-break position
"""

from __future__ import annotations

import random

from .core import (
    _LANG_ALPHABETS,
    _load_wordset,
    _mutate_word,
    _split_word_punct,
    _typo_lang,
)


def diverse_typos_text(text: str, word_prob: float = 0.15) -> str:
    """Programmatically inject single-edit non-word typos into Markov prose.

    Strategy: for each long-enough word (>=5 chars), with `word_prob` chance,
    apply one mutation. Reject any mutation whose result is itself in the
    English wordlist (we only want non-word typos so the scoring can
    unambiguously tell "OCR fixed it" from "OCR read a real but different
    word"). Capitalization of the original word is preserved.
    """
    lang = _typo_lang.get()
    wordset = _load_wordset(lang)
    alphabet = _LANG_ALPHABETS.get(lang, _LANG_ALPHABETS["en"])
    rng = random.Random(random.getrandbits(64))

    out: list[str] = []
    for raw in text.split():
        lead, core, tail = _split_word_punct(raw)
        if not core or len(core) < 5 or rng.random() >= word_prob:
            out.append(raw)
            continue
        # Try up to 3 times to get a non-word mutation
        mutated: str | None = None
        for _ in range(3):
            cand = _mutate_word(core.lower(), rng, alphabet=alphabet)
            if cand is None:
                break
            if wordset and cand not in wordset:
                # restore case (first char if original was titlecase / upper)
                if core[0].isupper():
                    cand = cand[0].upper() + cand[1:]
                mutated = cand
                break
        out.append(lead + (mutated if mutated else core) + tail)
    return " ".join(out)


def bold_typos_text(text: str, word_prob: float = 0.15) -> str:
    """Same mutation as diverse_typos, but wraps the mutated word in Pango
    bold markup. Tests: does visual emphasis on the mutated word reduce
    autocorrection? Prose renderer must be in markup mode for the bolding
    to actually render (default 50% of prose blocks use markup)."""
    lang = _typo_lang.get()
    wordset = _load_wordset(lang)
    alphabet = _LANG_ALPHABETS.get(lang, _LANG_ALPHABETS["en"])
    rng = random.Random(random.getrandbits(64))

    out: list[str] = []
    for raw in text.split():
        lead, core, tail = _split_word_punct(raw)
        if not core or len(core) < 5 or rng.random() >= word_prob:
            out.append(raw)
            continue
        mutated: str | None = None
        for _ in range(3):
            cand = _mutate_word(core.lower(), rng, alphabet=alphabet)
            if cand is None:
                break
            if wordset and cand not in wordset:
                if core[0].isupper():
                    cand = cand[0].upper() + cand[1:]
                mutated = cand
                break
        if mutated:
            # Pango bold; the prose renderer's _strip_markup turns this into
            # **word** in the markdown GT, so the typo word in GT is also
            # explicitly marked as emphasized.
            out.append(lead + f"<b>{mutated}</b>" + tail)
        else:
            out.append(raw)
    return " ".join(out)


def hyphenation_breaks_text(text: str, word_prob: float = 0.15) -> str:
    """Long words split with `-` at a soft-line position.

    Real failure for any document with paragraph justification.
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 8 and rng.random() < word_prob and w.isalpha():
            mid = len(w) // 2
            mid = max(2, min(len(w) - 2, mid + rng.randint(-1, 1)))
            out.append(f"{w[:mid]}-{w[mid:]}")
        else:
            out.append(w)
    return " ".join(out)
