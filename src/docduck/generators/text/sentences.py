"""Sentence-, paragraph- and heading-level text generators.

These functions are the workhorse for prose blocks, callouts, headings,
titles and similar continuous-text content. They sample from Markov
models when available (see ``models.py``) and fall back to a small
template grammar so output is never None.
"""

import random
import re

from ...blocks._helpers import wrap_highlight
from ...cli.build_corpora import LANG_SCRIPTS
from ...defaults import DEFAULTS
from .models import _SCRIPT_RETRY_TRIES, _accept_sample, _pick_model
from .modes import _apply_mode, get_content_mode

# Tokenized corpora come back as separate word tokens (["word", ",", "..."]) which
# we join on spaces when building the Markov training text: so Markov output
# inherits `word ,` spacing. Real prose has `word,`. Normalize at the source so
# both rendered pages and GT show clean punctuation.
_PRE_PUNCT_SPACE_RE = re.compile(r"\s+([.,;:!?\)\]])")
_OPEN_PUNCT_SPACE_RE = re.compile(r"([\(\[])\s+")


def _normalize_spacing(text: str) -> str:
    """Strip whitespace before closing punctuation and after openers."""
    if not text:
        return text
    text = _PRE_PUNCT_SPACE_RE.sub(r"\1", text)
    text = _OPEN_PUNCT_SPACE_RE.sub(r"\1", text)
    return text


def _markov_sentence(lang: str = None, max_words: int = 35) -> str | None:
    """Generate a single sentence from a Markov model."""
    _, model = _pick_model(lang)
    if model is None:
        return None
    s = None
    for _ in range(_SCRIPT_RETRY_TRIES if LANG_SCRIPTS.get(lang or "") else 1):
        s = model.make_sentence(tries=50, max_words=max_words)
        if _accept_sample(s, lang):
            return _normalize_spacing(s)
    return _normalize_spacing(s)  # last try: return rather than None


def _markov_short(lang: str = None, max_words: int = 12) -> str | None:
    """Short phrase for headings/titles/captions. Routes through the active
    TextSource so HF datasets (or any custom source) replace Markov."""
    from .sources import get_text_source

    return get_text_source().short(lang, max_words=max_words)


_NOUNS = [
    "system",
    "analysis",
    "method",
    "result",
    "study",
    "model",
    "process",
    "structure",
    "function",
    "approach",
    "development",
    "population",
    "relationship",
    "evidence",
    "theory",
    "data",
    "information",
    "effect",
    "research",
    "problem",
    "question",
    "experience",
    "observation",
    "field",
    "experiment",
    "hypothesis",
    "framework",
    "mechanism",
    "parameter",
    "distribution",
    "measurement",
    "phenomenon",
    "equation",
    "algorithm",
    "network",
    "surface",
    "pressure",
    "temperature",
    "frequency",
    "signal",
]

_VERBS = [
    "demonstrates",
    "indicates",
    "suggests",
    "provides",
    "reveals",
    "establishes",
    "confirms",
    "describes",
    "identifies",
    "determines",
    "represents",
    "produces",
    "requires",
    "involves",
    "includes",
    "maintains",
    "supports",
    "exhibits",
    "generates",
    "characterizes",
]

_ADJECTIVES = [
    "significant",
    "important",
    "primary",
    "fundamental",
    "substantial",
    "considerable",
    "relevant",
    "critical",
    "essential",
    "comprehensive",
    "complex",
    "initial",
    "previous",
    "subsequent",
    "corresponding",
    "proposed",
    "observed",
    "experimental",
    "theoretical",
    "statistical",
]

_ADVERBS = [
    "significantly",
    "clearly",
    "specifically",
    "particularly",
    "generally",
    "approximately",
    "respectively",
    "effectively",
    "consistently",
    "notably",
]

_PREPOSITIONS = ["in", "of", "for", "with", "between", "through", "across", "within"]
_CONJUNCTIONS = ["however", "moreover", "therefore", "nevertheless", "furthermore"]
_DETERMINERS = ["the", "a", "this", "each", "every", "that"]

_SENTENCE_PATTERNS = [
    "{cap} {v} {adj} {n} {prep} {det} {n}.",
    "The {n} of {det} {adj} {n} {v} {adv}.",
    "{cap}, {conj} {det} {n} {v} {adj}.",
    "In {det} {n}, {det} {adj} {n} {v} {det} {n}.",
    "Although {det} {n} {v} {adv}, {det} {n} {v} {adj}.",
    "The {adj} {n} {v} the {n} of {det} {adj} {n}.",
    "It was {adj} that {det} {n} {v} {adv} {prep} {det} {n}.",
    "Furthermore, {det} {adj} {n} {v} {det} {n} {adv}.",
    "This {n} {v} a {adj} {n} for {adj} {n}.",
    "Several {n} {v} {adv}, including {det} {adj} {n}.",
]


def _template_sentence():
    pattern = random.choice(_SENTENCE_PATTERNS)
    return pattern.format(
        cap=random.choice(_CONJUNCTIONS).capitalize(),
        n=random.choice(_NOUNS),
        v=random.choice(_VERBS),
        adj=random.choice(_ADJECTIVES),
        adv=random.choice(_ADVERBS),
        prep=random.choice(_PREPOSITIONS),
        det=random.choice(_DETERMINERS),
        conj=random.choice(_CONJUNCTIONS),
    )


def _make_sentence(lang: str = None) -> str:
    """One sentence. Routes through the active TextSource so HF datasets
    (or any custom source) replace Markov."""
    from .sources import get_text_source

    return get_text_source().sentence(lang)


def gen_paragraph(min_sentences=3, max_sentences=7, lang: str = None, markup=False) -> str:
    """Generate a random paragraph.

    If markup=True, randomly adds Pango markup: bold terms, italic phrases,
    superscript footnote markers, and inline citations.
    """
    n = random.randint(min_sentences, max_sentences)
    sentences = [_make_sentence(lang) for _ in range(n)]
    text = " ".join(sentences)
    text = _apply_mode(text)
    # Strikethrough mode already returns valid Pango markup: don't re-escape.
    if get_content_mode() == "strikethrough":
        return text
    if not markup:
        return text
    # Escape XML entities, re-split on sentence terminators, re-add markup
    sentences = [_escape_xml(s) for s in text.split(". ") if s]
    return " ".join(_add_inline_markup(s, i, len(sentences)) for i, s in enumerate(sentences))


def _escape_xml(text):
    """Escape &, <, > for safe use in Pango markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _add_inline_markup(sentence, idx, total):
    """Randomly add inline formatting to a sentence.

    Thresholds for bold/italic/sup/citation are rebased off the (opt-in)
    highlight probability so those branches keep their intended weight
    whether or not highlight is enabled. With `highlight_prob=0`, the
    highlight band collapses and total markup density drops by that amount.
    """
    r = random.random()
    hp = DEFAULTS["prose"].get("highlight_prob", 0.0)
    bold_end = hp + 0.12
    italic_end = bold_end + 0.08
    sup_end = italic_end + 0.08
    cite_end = sup_end + 0.10
    if hp > 0 and r < hp:
        # Highlight a phrase (2-4 words) with a soft marker-pen background.
        # GT emits ==phrase== via pango_to_markdown.
        words = sentence.split()
        if len(words) > 4:
            start = random.randint(0, len(words) - 3)
            end = min(start + random.randint(2, 4), len(words))
            phrase = " ".join(words[start:end])
            return " ".join(words[:start] + [wrap_highlight(phrase)] + words[end:])
    elif r < bold_end:
        words = sentence.split()
        for i, w in enumerate(words):
            if len(w) > 5 and w.isalpha():
                words[i] = f"<b>{w}</b>"
                break
        return " ".join(words)
    elif r < italic_end:
        words = sentence.split()
        if len(words) > 4:
            start = random.randint(0, len(words) - 3)
            end = min(start + random.randint(2, 3), len(words))
            words[start] = f"<i>{words[start]}"
            words[end - 1] = f"{words[end - 1]}</i>"
            return " ".join(words)
    elif r < sup_end:
        n = random.randint(1, 12)
        return f"{sentence.rstrip('.')}<sup>{n}</sup>."
    elif r < cite_end:
        style = random.choice(["bracket", "author"])
        if style == "bracket":
            refs = sorted(random.sample(range(1, 30), random.randint(1, 3)))
            cite = ", ".join(str(r) for r in refs)
            return f"{sentence.rstrip('.')} [{cite}]."
        else:
            authors = random.choice(
                [
                    "Smith et al.",
                    "Johnson &amp; Lee",
                    "Wang et al.",
                    "Brown &amp; Davis",
                    "Kim et al.",
                    "García et al.",
                ]
            )
            year = random.randint(2018, 2025)
            return f"{sentence.rstrip('.')} ({authors}, {year})."
    return sentence


def gen_paragraphs(
    count=3, min_sentences=3, max_sentences=7, lang: str = None, markup=False
) -> str:
    """Generate multiple paragraphs separated by newlines."""
    return "\n\n".join(
        gen_paragraph(min_sentences, max_sentences, lang, markup=markup) for _ in range(count)
    )


def gen_title(lang: str = None) -> str:
    """Generate a document title."""
    s = _markov_short(lang)
    if s:
        s = s.rstrip(".").rstrip(",")
        if len(s) > 60:
            s = s[:57].rsplit(" ", 1)[0]
        # Titles start with a capital; Markov sampling can return a token
        # beginning lowercase (e.g. "crazy horse speaks...").
        if s and s[0].islower():
            s = s[0].upper() + s[1:]
        return _apply_mode(s).rstrip(".,")

    templates = [
        "On the {adj} {n} of {adj} {n}",
        "A {adj} Approach to {n} {n}",
        "{adj} {n} in {adj} {n}: A Review",
        "The Role of {n} in {adj} {n}",
        "Towards {adj} {n}: Methods and {n}",
        "{adj} Analysis of {n} and {n}",
        "Understanding {adj} {n} Through {n}",
    ]
    return _apply_mode(
        random.choice(templates).format(
            adj=random.choice(_ADJECTIVES).capitalize(),
            n=random.choice(_NOUNS).capitalize(),
        )
    )


def gen_heading(lang: str = None) -> str:
    """Generate a section heading."""
    s = _markov_short(lang)
    if s:
        s = s.rstrip(".").rstrip(",")
        if len(s) > 50:
            s = s[:47].rsplit(" ", 1)[0]
        return _apply_mode(s).rstrip(".,")

    templates = [
        "{n} and {n}",
        "The {adj} {n}",
        "{n} of {n}",
        "{adj} {n}",
        "Experimental {n}",
        "Results and {n}",
    ]
    return _apply_mode(
        random.choice(templates).format(
            adj=random.choice(_ADJECTIVES).capitalize(),
            n=random.choice(_NOUNS).capitalize(),
        )
    )
