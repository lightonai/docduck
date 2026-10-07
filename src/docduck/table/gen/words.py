"""Word-pool and per-cell-type value generators.

The pool is a per-language cache of distinct words sampled from the Markov
corpus, filtered for length and stopwords. Cell generators draw from this
pool (text/label columns) or generate synthetic numeric values directly.
"""

import random

# Function words to skip when sampling individual words (per language).
# Only the most common connectives: enough to bias toward nouns.
_STOPWORDS = {
    "en": {
        "the",
        "a",
        "an",
        "of",
        "in",
        "to",
        "and",
        "or",
        "but",
        "for",
        "with",
        "on",
        "at",
        "by",
        "from",
        "that",
        "this",
        "is",
        "was",
        "were",
        "are",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "did",
        "not",
        "no",
        "as",
        "it",
        "its",
        "he",
        "she",
        "they",
        "we",
        "you",
        "i",
        "her",
        "him",
    },
    "fr": {
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "et",
        "ou",
        "à",
        "en",
        "au",
        "aux",
        "pour",
        "par",
        "sur",
        "avec",
        "sans",
        "dans",
        "que",
        "qui",
        "est",
        "sont",
        "être",
        "avoir",
        "ne",
        "pas",
        "ce",
        "cette",
        "ces",
        "son",
        "sa",
        "ses",
        "il",
        "elle",
        "ils",
        "elles",
    },
    "de": {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "ein",
        "eine",
        "einer",
        "und",
        "oder",
        "aber",
        "von",
        "zu",
        "mit",
        "in",
        "auf",
        "bei",
        "ist",
        "war",
        "sind",
        "werden",
        "haben",
        "hat",
        "nicht",
        "kein",
        "er",
        "sie",
        "es",
        "wir",
        "ich",
    },
    "es": {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "y",
        "o",
        "pero",
        "en",
        "a",
        "con",
        "por",
        "para",
        "sin",
        "sobre",
        "que",
        "es",
        "son",
        "fue",
        "ser",
        "no",
        "su",
        "sus",
        "él",
        "ella",
    },
    "it": {
        "il",
        "la",
        "lo",
        "gli",
        "le",
        "un",
        "una",
        "di",
        "del",
        "della",
        "e",
        "o",
        "ma",
        "in",
        "a",
        "con",
        "per",
        "da",
        "che",
        "è",
        "sono",
        "non",
        "suo",
        "sua",
        "lui",
        "lei",
    },
    "pt": {
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "e",
        "ou",
        "mas",
        "em",
        "com",
        "por",
        "para",
        "que",
        "é",
        "são",
        "não",
    },
    "ru": {
        "и",
        "в",
        "на",
        "с",
        "по",
        "за",
        "от",
        "к",
        "о",
        "из",
        "у",
        "не",
        "но",
        "что",
        "как",
        "это",
        "он",
        "она",
        "они",
        "мы",
    },
    "ar": {
        "في",
        "من",
        "إلى",
        "على",
        "عن",
        "و",
        "أو",
        "لكن",
        "هذا",
        "هذه",
        "ذلك",
        "هو",
        "هي",
        "هم",
        "ال",
    },
    "zh": set(),  # character-based: hard to pick stopwords generically
    "ja": set(),
    "ko": set(),
    "hi": {"और", "या", "है", "हैं", "था", "थी", "में", "से", "को", "का", "के", "की", "पर", "यह", "वह"},
}


# Per-language word pool cache
_word_pools: dict = {}


def _get_word_pool(lang, max_pool=500):
    """Build a pool of distinct words from the Markov corpus for `lang`.

    Words are extracted from Markov sentences, filtered for reasonable length
    and non-stopwords. Cached per-language via the module `_word_pools` dict.

    The pool is built under an isolated random state so its first-time
    construction doesn't perturb the caller's random stream. Otherwise
    cold-cache vs warm-cache calls would diverge: breaking reproducibility
    across back-to-back batches in the same process.
    """
    if lang in _word_pools:
        return _word_pools[lang]

    from ...generators import text as text_gen

    prev_state = random.getstate()
    # Per-language deterministic seed so the pool contents are stable
    # regardless of when they're built. Python's built-in ``hash()`` for
    # strings is randomized per-process (PYTHONHASHSEED), so use a stable
    # hash instead: otherwise identical `--seed` invocations in different
    # processes produce different table word pools.
    import hashlib

    seed_bytes = hashlib.blake2b(f"word_pool:{lang}".encode(), digest_size=4).digest()
    random.seed(int.from_bytes(seed_bytes, "little"))

    stopwords = _STOPWORDS.get(lang or "en", _STOPWORDS["en"])
    words = []
    seen = set()
    for _ in range(80):
        s = text_gen._markov_short(lang, max_words=40)
        if not s:
            continue
        for tok in s.split():
            tok = tok.strip(".,;:!?()[]{}\"'`«»—–-*_~").strip()
            if not tok or len(tok) < 2 or len(tok) > 20:
                continue
            low = tok.lower()
            if low in stopwords or low in seen:
                continue
            # Skip pure numbers, URLs, markup, money, percentages, or any
            # token containing punctuation/digits/suspect chars.
            if tok.isdigit() or any(c in tok for c in "=<>/\\|@#`*_~$%&^+,;:!?.0123456789"):
                continue
            seen.add(low)
            words.append(tok)
            if len(words) >= max_pool:
                break
        if len(words) >= max_pool:
            break

    _word_pools[lang] = words
    random.setstate(prev_state)
    return words


def _sample_word(lang):
    """Sample a single word from `lang`'s word pool."""
    pool = _get_word_pool(lang)
    if not pool:
        return None
    return random.choice(pool)


def _sample_phrase(lang, n_words=1, max_chars=20):
    """Sample `n_words` words joined with spaces.

    For n_words==1 returns a single word. For 2-3 words, joins distinct samples.
    Returns None if the pool is empty.
    """
    pool = _get_word_pool(lang)
    if not pool:
        return None
    if n_words == 1:
        return _sample_word(lang)
    if len(pool) < n_words:
        return random.choice(pool)
    words = random.sample(pool, n_words)
    result = " ".join(words)
    if len(result) > max_chars:
        return min((w for w in words if len(w) <= max_chars), default=words[0], key=len)
    return result


def _gen_word(lang):
    """Sample a single-word text cell for text-type columns."""
    return _sample_word(lang) or "—"


def _gen_label(lang):
    """Sample a label: 1 word most of the time, 2 occasionally."""
    n = 1 if random.random() < 0.7 else 2
    return _sample_phrase(lang, n_words=n, max_chars=18) or "—"


def _gen_short_label(lang, max_chars=10):
    """Always-single-word label filtered to `max_chars`. For narrow label columns."""
    pool = _get_word_pool(lang)
    short = [w for w in pool if len(w) <= max_chars] if pool else []
    return random.choice(short) if short else "—"


def _distinct_label(lang, avoid: set[str], max_tries: int = 20) -> str:
    """Sample a label not already in `avoid`. Falls back to a suffix if exhausted."""
    for _ in range(max_tries):
        candidate = _gen_label(lang)
        if candidate not in avoid:
            return candidate
    # Very unlikely: collision pool exhausted. Append a disambiguator.
    return f"{_gen_label(lang)} {len(avoid) + 1}"


def _gen_int(_lang=None, lo=1, hi=999):
    return str(random.randint(lo, hi))


def _gen_float(_lang=None, lo=0.1, hi=99.9, decimals=None):
    if decimals is None:
        decimals = random.choice([1, 2, 3])
    return f"{random.uniform(lo, hi):.{decimals}f}"


def _gen_percent(_lang=None):
    return f"{random.uniform(0, 100):.1f}%"


def _gen_pvalue(_lang=None):
    v = random.uniform(0.0001, 0.5)
    if v < 0.001:
        return f"{v:.4f}"
    return f"{v:.3f}"


def _gen_year(_lang=None):
    return str(random.randint(1950, 2025))


def _gen_money(_lang=None):
    v = random.uniform(1, 50000)
    if v > 1000:
        return f"${v:,.0f}"
    return f"${v:.2f}"


def _gen_range(_lang=None):
    a = random.uniform(1, 50)
    b = a + random.uniform(0.5, 20)
    return f"{a:.1f}–{b:.1f}"


def _gen_plusminus(_lang=None):
    v = random.uniform(1, 100)
    e = random.uniform(0.1, v * 0.3)
    return f"{v:.1f} ± {e:.1f}"


def _gen_ratio(_lang=None):
    a, b = random.randint(1, 20), random.randint(1, 20)
    return f"{a}:{b}"


# column_type → cell generator; every generator takes `lang` as first arg
# (numeric generators ignore it) so the table builders can call them uniformly.
_CELL_GENERATORS = {
    "text": _gen_word,
    "label": _gen_label,
    "int": _gen_int,
    "float": _gen_float,
    "percent": _gen_percent,
    "pvalue": _gen_pvalue,
    "year": _gen_year,
    "money": _gen_money,
    "range": _gen_range,
    "plusminus": _gen_plusminus,
    "ratio": _gen_ratio,
}
