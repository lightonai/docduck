"""Pango-markup emphasis probes plus structural / whitespace variations.

These modes wrap words in Pango span tags (italic, strike, highlight,
wide letter-spacing) or prepend list-bullet glyphs and code-block fences.
The prose renderer must be in markup mode for most of these to take
visual effect (default 50% of prose blocks use markup).
"""

from __future__ import annotations

import random
import re

from .core import _esc_xml

# ---------------------------------------------------------------------------
# Strikethrough: wrap ~20% of words in Pango <s>…</s> markup. Output is
# valid Pango markup (& < > escaped outside the added tags); prose block
# must render with markup=True for the strikes to show visually.
# GT converts <s>…</s> → markdown ~~…~~ via pango_to_markdown.
# ---------------------------------------------------------------------------


def strikethrough_text(text: str, prob: float = 0.20) -> str:
    def wrap(w: str) -> str:
        lead = trail = ""
        i = 0
        while i < len(w) and not w[i].isalnum():
            lead += w[i]
            i += 1
        j = len(w)
        while j > i and not w[j - 1].isalnum():
            trail = w[j - 1] + trail
            j -= 1
        core = w[i:j]
        if core and random.random() < prob:
            return f"{_esc_xml(lead)}<s>{_esc_xml(core)}</s>{_esc_xml(trail)}"
        return _esc_xml(w)

    return " ".join(wrap(w) for w in text.split())


# ---------------------------------------------------------------------------
# Strikethrough emphasis: Pango <s>...</s>. Tests strike preservation.
# ---------------------------------------------------------------------------


def strikethrough_emphasis_text(text: str, word_prob: float = 0.12) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob and w.isalpha():
            out.append(f"<s>{w}</s>")
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Italic emphasis: Pango <i> markup on random words.
# ---------------------------------------------------------------------------


def italic_emphasis_text(text: str, word_prob: float = 0.15) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob and w.isalpha():
            out.append(f"<i>{w}</i>")
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Highlighted text: Pango span background colour (simulated highlighter).
# ---------------------------------------------------------------------------


def highlighted_text(text: str, word_prob: float = 0.12) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    colours = ["#ffff00", "#90ee90", "#ffb6c1", "#87ceeb"]
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob and w.isalpha():
            c = rng.choice(colours)
            out.append(f'<span background="{c}">{w}</span>')
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Wide-kerning: wrap mutated words in Pango span with high letter_spacing.
# Renders letters with visible gaps between them. Probes word-segmentation:
# does OCR see the word or individual letters?
# ---------------------------------------------------------------------------


def wide_kerning_text(text: str, word_prob: float = 0.12, spacing: int = 10000) -> str:
    """Wrap a fraction of words in Pango wide-letter-spacing markup.

    Pango letter_spacing units are 1/1024 of a point. 10 000 ≈ 10 pt gap
    between letters (very wide). The prose renderer must be in markup mode
    for this to take effect (default 50% of prose blocks).
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) < 5 or rng.random() >= word_prob:
            out.append(w)
            continue
        # Escape minimal Pango chars
        esc = w.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append(f'<span letter_spacing="{spacing}">{esc}</span>')
    return " ".join(out)


# ---------------------------------------------------------------------------
# Bullet markers: deliberate variety of list bullets. Tests OCR's handling
# of `-` / `•` / `◦` / `●` / `▪` / `◆` / `1.` / `a)` / `i)`.
# ---------------------------------------------------------------------------

_BULLET_GLYPHS = ["•", "◦", "●", "▪", "▫", "◆", "★", "‣", "⁃"]


def bullet_markers_text(text: str, sentence_prob: float = 0.50) -> str:
    """Replace some sentence breaks with bullets to force list-like layout."""
    rng = random.Random(random.getrandbits(64))
    sents = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for s in sents:
        if rng.random() < sentence_prob:
            bullet = rng.choice(_BULLET_GLYPHS)
            out.append(f"{bullet} {s}")
        else:
            out.append(s)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Code block: inject monospace-style fragments with special chars.
# ---------------------------------------------------------------------------

_CODE_FRAGMENTS = [
    "if (x > 0) { return x; }",
    "for i in range(10): print(i)",
    "regex: /^([0-9]+)\\.([a-z]+)$/",
    '{ "key": [1, 2, 3], "flag": true }',
    "x = (a + b) * c / d",
    "def foo(x, *, y=1): return x + y",
    '<div class="row" data-x="1"/>',
    "SELECT * FROM t WHERE id > 100;",
]


def code_block_text(text: str, sentence_prob: float = 0.30) -> str:
    rng = random.Random(random.getrandbits(64))
    sents = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for s in sents:
        out.append(s)
        if rng.random() < sentence_prob:
            out.append("`" + rng.choice(_CODE_FRAGMENTS) + "`")
    return " ".join(out)


# ---------------------------------------------------------------------------
# Whitespace fidelity: inject deliberate multi-space + tab patterns.
# ---------------------------------------------------------------------------


def whitespace_tabs_text(text: str, prob: float = 0.06) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if rng.random() < prob:
            sep = rng.choice(["\t", "   ", "  ", "\t\t"])
            out.append(sep + w)
        else:
            out.append(w)
    return " ".join(out)
