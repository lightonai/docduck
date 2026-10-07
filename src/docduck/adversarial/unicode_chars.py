"""Non-ASCII / multi-script probes.

Each mode injects a token that exercises Unicode preservation: diacritics,
Greek letters, scientific operators, mojibake byte sequences, RTL script
embedding, or superscript footnote markers. A faithful OCR emits the exact
codepoint; a normalizing OCR transliterates to ASCII.
"""

from __future__ import annotations

import random
import re

# ---------------------------------------------------------------------------
# Foreign personal names with diacritics / non-ASCII chars. Tests whether
# OCR preserves the exact characters or silently transliterates to ASCII
# (Müller → Mueller / Muller, Søren → Soren, etc.): a real failure mode
# for citations, bibliographies, and identity documents. List spans
# European + Latin + Nordic + Eastern-European scripts using Latin
# extended characters only (no non-Latin scripts here, those are a
# separate probe).
# ---------------------------------------------------------------------------

_FOREIGN_NAMES = [
    # German
    "Müller",
    "Schäfer",
    "Köhler",
    "Bäcker",
    "Lützen",
    "Größe",
    # French
    "Béatrice",
    "François",
    "Élise",
    "Aurélien",
    "Hervé",
    "Théodore",
    # Spanish / Portuguese
    "García",
    "Núñez",
    "Peña",
    "Hernández",
    "São",
    "Conceição",
    # Nordic
    "Søren",
    "Kjær",
    "Åslund",
    "Lillström",
    "Ørsted",
    "Hägglund",
    # Eastern European with Latin extended
    "Łukasz",
    "Józef",
    "Małgorzata",
    "Naděžda",
    "Dvořák",
    "Świątek",
    # Other Romance
    "Niccolò",
    "Giuseppe",
    "Andreï",
    # Compound
    "Saint-Étienne",
    "Saint-Hélène",
]


def foreign_names_text(text: str, word_prob: float = 0.08) -> str:
    """Replace some Markov words with real foreign names containing diacritics.

    Each insertion records nothing: at scoring time we extract the foreign-
    name set from the GT and check whether each appears verbatim in the OCR.
    Tests: does the OCR preserve `ö, é, ñ, ø, ł, ě`, or silently transliterate
    to ASCII (`Mueller`, `Soren`, `Lukasz`)?
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            out.append(rng.choice(_FOREIGN_NAMES))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Scientific-symbol chunks. Each is a self-contained phrase that exercises
# one of the four Unicode-preservation axes OCR systems are weak at:
#   1. Greek letters in technical context (α-blocker, β-decay, σ standard
#      deviation, λ wavelength, Δ delta, Σ sigma, π pi, ε epsilon, …)
#   2. Unit symbols with non-ASCII (µ micro, ° degree, ‰ permille,
#      Å angstrom, Ω ohm)
#   3. Sub/superscripts as Unicode glyphs (H₂O, CO₂, x², 10⁻⁹)
#   4. Math comparison/operator glyphs (≤ ≥ ≈ ≠ ± × ÷ → ⇒ ∞ ∝ ∇)
#
# Listed phrases occur naturally in scientific / medical / engineering text.
# A pixel-faithful OCR preserves the exact Unicode codepoints; one biased
# toward "clean ASCII" output silently transliterates (µg→ug, °C→C,
# H₂O→H2O, ≤→<=, α→alpha). Both forms exist in real documents: but the
# *transcription target* should be what's actually on the page.
# ---------------------------------------------------------------------------

_SCIENTIFIC_SYMBOLS = [
    "5 µg/mL",
    "10 µM",
    "25°C",
    "−40°C",
    "pH 7.4",
    "pKa 4.76",
    "λ = 632.8 nm",
    "λmax = 280 nm",
    "α-blocker",
    "β-decay",
    "γ-radiation",
    "Δ G = −42 kJ/mol",
    "ΔH = +89 kJ/mol",
    "ΔS = 0.13 J/K",
    "Δt = 5 ms",
    "Σ xᵢ = N",
    "Σ Fnet = 0",
    "Πᵢ pᵢ",
    "∫₀^∞ f(x) dx",
    "±2.5σ",
    "±3.14×10⁻¹⁹",
    "x² + y² = r²",
    "10⁻⁹ s",
    "H₂O",
    "CO₂",
    "C₆H₁₂O₆",
    "NaHCO₃",
    "Fe³⁺",
    "Na⁺/K⁺-ATPase",
    "p ≤ 0.05",
    "n ≥ 30",
    "x ≠ 0",
    "f(x) ≈ x",
    "x → ∞",
    "A ⇒ B",
    "10 Ω",
    "5 mΩ",
    "100 µΩ",
    "0.5 Å",
    "1.5 Å",
    "2.4 GHz",
    "5 ‰ saline",
    "98.6°F",
    "−273.15°C",
    "30 m²",
    "12 m³",
    "ε₀ = 8.85×10⁻¹²",
    "μ₀ = 4π×10⁻⁷",
    "ℏ = 1.054×10⁻³⁴",
]


def scientific_symbols_text(text: str, word_prob: float = 0.06) -> str:
    """Replace some Markov words with curated scientific/unit symbol phrases.

    Each phrase contains at least one non-ASCII character (Greek, unit symbol,
    subscript, operator) so the scoring can isolate Unicode preservation
    failures. The phrase itself is short (typically 2-5 tokens) so it doesn't
    distort page layout.
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            out.append(rng.choice(_SCIENTIFIC_SYMBOLS))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Greek variables: inject Greek letters as scientific/math vars in prose.
# ---------------------------------------------------------------------------

_GREEK_VARS = [
    "α",
    "β",
    "γ",
    "δ",
    "ε",
    "ζ",
    "η",
    "θ",
    "ι",
    "κ",
    "λ",
    "μ",
    "ν",
    "ξ",
    "π",
    "ρ",
    "σ",
    "τ",
    "φ",
    "χ",
    "ψ",
    "ω",
    "Δ",
    "Σ",
    "Ω",
    "Λ",
]
_GREEK_USAGES = [
    "{g}-receptor",
    "{g}-blocker",
    "({g} = {n})",
    "{g} = {n}",
    "{g}({n})",
    "rate {g}",
    "{g}-value",
    "{g}/{n}",
]


def greek_variables_text(text: str, word_prob: float = 0.10) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            g = rng.choice(_GREEK_VARS)
            tpl = rng.choice(_GREEK_USAGES)
            n = rng.uniform(0.01, 99.99)
            phrase = tpl.format(g=g, n=f"{n:.2f}")
            out.append(phrase)
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Bidi text: embed Arabic phrase inside English sentences.
# ---------------------------------------------------------------------------

_BIDI_PHRASES = [
    "كلمة المرور",  # password
    "السلام عليكم",  # peace upon you
    "شكرا لك",  # thank you
    "حقوق النشر",  # copyright
    "بنك مركزي",  # central bank
    "صناعة الورق",  # paper industry
]


def bidi_text_mode(text: str, sentence_prob: float = 0.15) -> str:
    rng = random.Random(random.getrandbits(64))
    sents = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for s in sents:
        out.append(s)
        if rng.random() < sentence_prob:
            phrase = rng.choice(_BIDI_PHRASES)
            out.append(f"({phrase}).")
    return " ".join(out)


# ---------------------------------------------------------------------------
# Mixed-script word: proper nouns with diacritics from multiple scripts.
# ---------------------------------------------------------------------------

_MIXED_NAMES = [
    "naïveté",
    "San José",
    "Citroën",
    "Mötörhead",
    "Beyoncé",
    "Märzen",
    "São Paulo",
    "Reykjavík",
    "Žižek",
    "façade",
    "Łódź",
    "Antônio",
    "Côte d'Ivoire",
    "Hagåtña",
    "København",
    "Tübingen",
    "Düsseldorf",
]


def mixed_script_word_text(text: str, word_prob: float = 0.08) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            out.append(rng.choice(_MIXED_NAMES))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Footnote-markers: append Unicode superscript digit after random words.
# Probes Unicode preservation: does OCR keep ¹²³ as superscript or
# transcribe as inline digit "1", "2", "3"?
# ---------------------------------------------------------------------------

_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def footnote_markers_text(text: str, word_prob: float = 0.10) -> str:
    """Append a superscript digit after random words (no space before)."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if rng.random() >= word_prob or not w[-1:].isalnum():
            out.append(w)
            continue
        marker = rng.choice(_SUPERSCRIPT_DIGITS)
        out.append(w + marker)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Mojibake: pre-corrupted accented words. Tests whether OCR preserves the
# visible-but-broken byte sequence (faithful) or silently re-canonicalises
# to the original accented form (LM prior). Real-world failure mode for any
# document touched by a bad UTF-8 → Latin-1 round-trip.
# ---------------------------------------------------------------------------

_MOJIBAKE_PHRASES: list[tuple[str, str]] = [
    # (corrupted form rendered on page, canonical form an LM would auto-correct to)
    ("cafÃ©", "café"),
    ("rÃ©sumÃ©", "résumé"),
    ("naÃ¯ve", "naïve"),
    ("dÃ©jÃ  vu", "déjà vu"),
    ("CrÃªpe", "Crêpe"),
    ("piÃ±ata", "piñata"),
    ("jalapeÃ±o", "jalapeño"),
    ("MÃ¼ller", "Müller"),
    ("BjÃ¶rn", "Björn"),
    ("ZÃ¼rich", "Zürich"),
    ("MÃ¶bius", "Möbius"),
    ("GÃ¶del", "Gödel"),
    ("SchrÃ¶dinger", "Schrödinger"),
    ("FranÃ§ois", "François"),
    ("garÃ§on", "garçon"),
    ("LeÃ³n", "León"),
    ("EspaÃ±a", "España"),
    ("MÃ©xico", "México"),
    ("PerÃº", "Perú"),
    ("BogotÃ¡", "Bogotá"),
    ("over â‚¬500", "over €500"),
    ("Â£250", "£250"),
    ("â€œquoted textâ€", "“quoted text”"),
    ("Itâ€™s", "It’s"),
    ("donâ€™t", "don’t"),
    ("â€“dashâ€”", "—dash—"),
    ("FaÃ§ade", "Façade"),
    ("rÃ´le", "rôle"),
    ("tÃªte-Ã -tÃªte", "tête-à-tête"),
    ("coöperate", "coöperate"),  # control: rare diaeresis kept as-is
]


def mojibake_text(text: str, word_prob: float = 0.10) -> str:
    """Replace some Markov words with pre-corrupted mojibake phrases."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            ms, _canon = rng.choice(_MOJIBAKE_PHRASES)
            out.append(ms)
        else:
            out.append(w)
    return " ".join(out)
