"""Phonotactic pseudo-words and pure-random gibberish word builders.

Both functions take a target character length and return a single token of
that length: used by the dispatcher's pseudo/gibberish fallback to replace
Markov words while preserving page length.
"""

from __future__ import annotations

import random

# Gibberish: random letter clusters
_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _gibberish_word(length: int) -> str:
    """Random letter cluster of exactly `length` chars (min 1)."""
    length = max(1, length)
    return "".join(random.choices(_LETTERS, k=length))


# Pseudo-text: phonotactically-plausible fake words
_CONSONANTS = "bcdfghjklmnpqrstvwxz"
_VOWELS = "aeiou"


def _pseudo_word_of_length(length: int) -> str:
    """Build a fake word with CVCV... alternation matching `length` chars."""
    length = max(1, length)
    out = []
    use_consonant = random.random() < 0.6  # start with consonant most of the time
    for _ in range(length):
        out.append(random.choice(_CONSONANTS if use_consonant else _VOWELS))
        use_consonant = not use_consonant
    return "".join(out)
