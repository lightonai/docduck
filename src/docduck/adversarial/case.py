"""Case and punctuation distortions that exercise transcription fidelity.

All probes here keep the underlying lexicon intact and only alter the
casing or the punctuation run: so the GT is unambiguous and any change
in OCR output reflects normalization, not a real read.
"""

from __future__ import annotations

import random
import re

from .core import _VOWEL_CHARS


def all_caps_text(text: str, sentence_prob: float = 0.5) -> str:
    """Uppercase a fraction of sentences. Tests: does the OCR preserve full
    UPPERCASE or normalize to sentence/title case?"""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for s in sentences:
        if random.random() < sentence_prob:
            out.append(s.upper())
        else:
            out.append(s)
    return " ".join(out)


def mixed_case_text(text: str, word_prob: float = 0.20) -> str:
    """Randomly recase each char in a fraction of words. Tests: does the OCR
    preserve `cAtCh ThE bAlL` literally or normalize the casing?"""

    def recase_word(w: str) -> str:
        if random.random() >= word_prob:
            return w
        return "".join(c.upper() if random.random() < 0.5 else c.lower() for c in w)

    return " ".join(recase_word(w) for w in text.split())


def repeat_chars_text(
    text: str, word_prob: float = 0.10, repeat_min: int = 3, repeat_max: int = 6
) -> str:
    """Lengthen a random vowel in a fraction of words (`hello` → `helloooo`).
    Tests: does the OCR preserve the exact character count, or normalize to
    the lexicon spelling?"""

    def stretch(w: str) -> str:
        if random.random() >= word_prob:
            return w
        vowel_positions = [i for i, c in enumerate(w) if c in _VOWEL_CHARS]
        if not vowel_positions:
            return w
        i = random.choice(vowel_positions)
        n = random.randint(repeat_min, repeat_max)
        return w[:i] + w[i] * n + w[i + 1 :]

    return " ".join(stretch(w) for w in text.split())


def punct_storm_text(
    text: str, sentence_prob: float = 0.4, extras_min: int = 2, extras_max: int = 5
) -> str:
    """Append extra punctuation to sentence ends (`Why?` → `Why?!?!!?`).
    Tests: does the OCR preserve unusual punctuation runs, or collapse them
    to canonical single terminators?"""
    sentences = re.split(r"(?<=[.!?])\s+", text)

    def storm(s: str) -> str:
        m = re.match(r"^(.*?)([.!?]+)\s*$", s, re.DOTALL)
        if not m or random.random() >= sentence_prob:
            return s
        core, term = m.group(1), m.group(2)
        n = random.randint(extras_min, extras_max)
        extra = "".join(random.choice("!?.") for _ in range(n))
        return core + term + extra

    return " ".join(storm(s) for s in sentences)


def all_caps_mid_sentence_text(text: str, word_prob: float = 0.10) -> str:
    """Randomly UPPERCASE individual words inside running text."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob and w.isalpha():
            out.append(w.upper())
        else:
            out.append(w)
    return " ".join(out)
