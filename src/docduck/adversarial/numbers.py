"""Numeric distortions: digits, locales, IDs, dates, postal codes, currencies.

Each probe inserts a fixed-format token (number-shaped) into prose and
tests whether the OCR preserves the exact digit count, separator, format,
or currency symbol.
"""

from __future__ import annotations

import random
import re

from .core import _NUMBER_RE

# ---------------------------------------------------------------------------
# Leading zeros: pad bare integers so the OCR has to choose between
# preserving every digit or stripping to the canonical numeral.
# ---------------------------------------------------------------------------


def leading_zeros_text(
    text: str, number_prob: float = 0.6, pad_min: int = 1, pad_max: int = 4
) -> str:
    """Pad bare integers with leading zeros (`42` → `0042`). Tests: does the
    OCR preserve the literal digit count, or strip leading zeros to the
    canonical numeral?"""

    def pad(m: re.Match) -> str:
        num = m.group(0)
        if random.random() >= number_prob:
            return num
        n_pad = random.randint(pad_min, pad_max)
        return ("0" * n_pad) + num

    return _NUMBER_RE.sub(pad, text)


# ---------------------------------------------------------------------------
# Precision numbers: long random decimals with at least 4 fractional digits.
# ---------------------------------------------------------------------------


def precision_numbers_text(
    text: str,
    word_prob: float = 0.10,
    min_digits: int = 8,
    max_digits: int = 14,
) -> str:
    """Replace some Markov words with high-precision decimal numbers.

    Each injected number is a uniformly-random digit string of total length
    in [min_digits, max_digits], split into an integer and fractional part.
    These don't have natural English equivalents: a pixel-faithful OCR will
    transcribe every digit; one that "cleans up" data might round, truncate,
    or insert thousands separators.

    No language conditioning: digit strings are universal, the probe runs
    identically per language.
    """
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            total = rng.randint(min_digits, max_digits)
            # Always have an integer part >= 1 digit and decimals >= 4 digits
            # so that "auto-rounding to 2 decimals" is a detectable distortion.
            int_len = rng.randint(1, max(1, total - 4))
            dec_len = total - int_len
            int_part = "".join(
                rng.choices("123456789" if int_len == 1 else "0123456789", k=int_len)
            )
            if int_len > 1:
                int_part = rng.choice("123456789") + "".join(
                    rng.choices("0123456789", k=int_len - 1)
                )
            dec_part = "".join(rng.choices("0123456789", k=dec_len))
            out.append(f"{int_part}.{dec_part}")
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Roman numerals: replace small integers with Roman form. Tests notation
# preservation: does OCR transcribe "MCMLXXIV" verbatim or "fix" to "1974"?
# ---------------------------------------------------------------------------

_ROMAN_VALUES = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    if n <= 0 or n >= 4000:
        return str(n)
    out = []
    for v, s in _ROMAN_VALUES:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


_INT_RE = re.compile(r"(?<!\w)(\d{1,4})(?!\w)")


def roman_numerals_text(text: str, number_prob: float = 0.6) -> str:
    """Replace 1-4 digit integers (1..3999) with Roman form, ~60% of the time."""
    rng = random.Random(random.getrandbits(64))

    def sub(m: re.Match) -> str:
        n = int(m.group(1))
        if 1 <= n <= 3999 and rng.random() < number_prob:
            return to_roman(n)
        return m.group(0)

    return _INT_RE.sub(sub, text)


# ---------------------------------------------------------------------------
# Locale numbers: financial-document amounts in EU ("1.234,56 €") vs US
# ("$1,234.56") formats. Tests whether OCR preserves the locale's
# thousands / decimal separators or silently normalises to one convention.
# Top industrial relevance: invoice / receipt / balance-sheet parsing.
# ---------------------------------------------------------------------------


def _format_amount(amount: float, locale: str) -> str:
    """Render `amount` (positive float) in EU or US notation with currency."""
    if locale == "us":
        intp, frac = f"{amount:,.2f}".split(".")
        return f"${intp}.{frac}"
    if locale == "eu":
        # EU: "." as thousands sep, "," as decimal
        intp, frac = f"{amount:,.2f}".split(".")
        intp = intp.replace(",", ".")
        return f"{intp},{frac} €"
    if locale == "uk":
        intp, frac = f"{amount:,.2f}".split(".")
        return f"£{intp}.{frac}"
    return f"{amount}"


def locale_numbers_text(text: str, word_prob: float = 0.07) -> str:
    """Replace some words with currency-formatted amounts in mixed locales.

    Each insertion picks a locale at random (us / eu / uk) so the page
    contains a mix; OCR can be tested for locale fidelity.
    """
    rng = random.Random(random.getrandbits(64))
    locales = ["us", "eu", "uk"]
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            amount = rng.uniform(1.23, 99999.99)
            loc = rng.choice(locales)
            out.append(_format_amount(amount, loc))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Structured IDs: alphanumeric codes with separators (invoice numbers,
# tracking IDs, case numbers, IBANs). Tests OCR fidelity on fixed-format
# tokens that are typically extracted by downstream regexes.
# ---------------------------------------------------------------------------

_ID_TEMPLATES = [
    "INV-{Y}-{X4}",
    "ORD-{Y}-{X3}-{X3}",
    "TRACK-{X4}-{X3}-{X3}",
    "1Z{X3}AA{N10}",  # UPS-like
    "{N12}",  # Numeric ID
    "GB{N2}WEST{N14}",  # UK IBAN-like
    "DE{N2}{N18}",  # DE IBAN-like
    "CASE-{Y}-{X2}-{N5}",
    "PO#{N8}",
    "SKU-{X2}-{X3}-{N4}",
    "{X1}{N6}-{X1}{N6}",  # Insurance claim-like
    "REF:{X3}{N5}",
]


def _expand_template(t: str, rng: random.Random) -> str:
    """Expand templated id, e.g. {X3} → 3 random uppercase letters, {N5} → 5 digits."""

    def repl(m: re.Match) -> str:
        spec = m.group(1)
        if spec == "Y":
            return str(rng.randint(2019, 2026))
        if spec.startswith("X"):
            n = int(spec[1:])
            return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(n))
        if spec.startswith("N"):
            n = int(spec[1:])
            return "".join(rng.choice("0123456789") for _ in range(n))
        return m.group(0)

    return re.sub(r"\{([A-Z]\d*)\}", repl, t)


def structured_ids_text(text: str, word_prob: float = 0.05) -> str:
    """Replace some words with random structured IDs."""
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 5 and rng.random() < word_prob:
            t = rng.choice(_ID_TEMPLATES)
            out.append(_expand_template(t, rng))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Date formats: same date rendered in 6+ conventions to test OCR's
# tendency to silently normalise dates to one canonical format. Real cost
# in document-processing pipelines that regex-extract dates by format.
# ---------------------------------------------------------------------------

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTHS_FULL = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _format_date(y: int, m: int, d: int, fmt: str) -> str:
    if fmt == "iso":
        return f"{y:04d}-{m:02d}-{d:02d}"
    if fmt == "us":
        return f"{m:02d}/{d:02d}/{y:04d}"
    if fmt == "eu":
        return f"{d:02d}/{m:02d}/{y:04d}"
    if fmt == "dot":
        return f"{d:02d}.{m:02d}.{y:04d}"
    if fmt == "short_month":
        return f"{d:d} {_MONTHS[m - 1]} {y:04d}"
    if fmt == "long_month_us":
        return f"{_MONTHS_FULL[m - 1]} {d:d}, {y:04d}"
    return ""


def date_formats_text(text: str, word_prob: float = 0.06) -> str:
    """Replace some words with random dates in one of 6 formats."""
    rng = random.Random(random.getrandbits(64))
    formats = ["iso", "us", "eu", "dot", "short_month", "long_month_us"]
    out: list[str] = []
    for w in text.split():
        if len(w) >= 5 and rng.random() < word_prob:
            y = rng.randint(2010, 2026)
            m = rng.randint(1, 12)
            # safe day to avoid Feb 30
            d = rng.randint(1, 28)
            fmt = rng.choice(formats)
            out.append(_format_date(y, m, d, fmt))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Postal codes: varied international formats.
# ---------------------------------------------------------------------------

_POSTAL_FORMATS = [
    "{N5}-{N4}",  # US ZIP+4
    "{N5}",  # US ZIP
    "{A1}{N1}{A1} {N1}{A1}{N1}",  # Canadian
    "{N2}-{N3}",  # JP
    "{A2} {N1}{A1} {N1}{A1}",  # UK
    "{N5}",  # DE
]


def _expand_postal(t: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        spec = m.group(1)
        if spec.startswith("A"):
            n = int(spec[1:])
            return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(n))
        if spec.startswith("N"):
            n = int(spec[1:])
            return "".join(rng.choice("0123456789") for _ in range(n))
        return m.group(0)

    return re.sub(r"\{([AN]\d+)\}", repl, t)


def postal_codes_text(text: str, word_prob: float = 0.06) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 5 and rng.random() < word_prob:
            out.append(_expand_postal(rng.choice(_POSTAL_FORMATS), rng))
        else:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Rare currencies: ₹ ₪ ₣ ₱ ₩ ฿ ₫.
# ---------------------------------------------------------------------------

_RARE_CURRENCY_SYMBOLS = ["₹", "₪", "₣", "₱", "₩", "฿", "₫", "₺", "₴", "₦"]


def rare_currency_text(text: str, word_prob: float = 0.07) -> str:
    rng = random.Random(random.getrandbits(64))
    out: list[str] = []
    for w in text.split():
        if len(w) >= 4 and rng.random() < word_prob:
            sym = rng.choice(_RARE_CURRENCY_SYMBOLS)
            amount = rng.uniform(10, 99999)
            out.append(f"{sym}{amount:,.2f}")
        else:
            out.append(w)
    return " ".join(out)
