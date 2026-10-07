"""Word-order scramble within sentence boundaries.

Real words are kept; only their position is randomized. Punctuation at
sentence ends is preserved so the page still reads as a paragraph.
"""

from __future__ import annotations

import random
import re


def scramble_text(text: str) -> str:
    """Shuffle word order within each sentence; preserve punctuation at sentence ends."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    scrambled = []
    for s in sentences:
        m = re.match(r"^(.*?)([.!?]+)\s*$", s, re.DOTALL)
        core, term = (m.group(1), m.group(2)) if m else (s, "")
        words = core.split()
        if len(words) > 1:
            random.shuffle(words)
            words[0] = words[0].capitalize()
        scrambled.append(" ".join(words) + term)
    return " ".join(scrambled)
