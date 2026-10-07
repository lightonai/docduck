"""Markov model loading and language/genre selection.

Models are JSON files shipped under ``src/docduck/corpora/`` (or rebuilt
via ``docduck-corpora``). Loading is lazy and cached in the ``_models``
dict.
"""

import os
import random

import markovify

from ...cli.build_corpora import LANG_SCRIPTS, script_ratio
from ...defaults import DEFAULTS as D

# Runtime script-ratio filter for non-Latin models built from mixed sources.
# For non-Latin langs, Markov sampling retries until the candidate sentence is
# predominantly in the target script (`DEFAULTS["text"]["script_ratio_threshold"]`
# ratio of letters) or we give up and return the last try. Rejects pure-English
# entries that leak in when a user builds from mixed text. Each retry is a
# few-microsecond dict walk: no real cost.
_SCRIPT_RETRY_TRIES = 50


# Corpora live alongside the top-level ``docduck`` package, not inside
# ``generators/text/``. Walk three dirnames up: text/ → generators/ →
# docduck/: then append ``corpora``.
_CORPORA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "corpora",
)

_models: dict[str, markovify.NewlineText] = {}

# The one model docduck ships. It is built from Project Gutenberg text, which
# is public domain. `english_genres()` also reports any extra en_* models found
# on disk, so user-built corpora join the pool without a code change.
SHIPPED_ENGLISH_GENRE = "en_literature"


def english_genres() -> list[str]:
    """English genre models available on disk, defaulting to the shipped one."""
    present = sorted(m for m in available_models() if m.startswith("en_"))
    return present or [SHIPPED_ENGLISH_GENRE]


ENGLISH_GENRES = [SHIPPED_ENGLISH_GENRE]

# Canonical ISO 639-1 codes the generator knows a script for. None are shipped;
# build one with `docduck-corpora --lang CODE --input ...`.
MULTILINGUAL_CODES = [
    "fr",
    "de",
    "es",
    "pt",
    "it",
    "nl",
    "pl",
    "sv",
    "tr",
    "vi",
    "ro",
    "ru",
    "uk",
    "ar",
    "zh",
    "ja",
    "ko",
    "hi",
    "th",
]


def available_models() -> list[str]:
    """Return list of model names that have been built (JSON files on disk)."""
    if not os.path.isdir(_CORPORA_DIR):
        return []
    return [f.removesuffix(".json") for f in os.listdir(_CORPORA_DIR) if f.endswith(".json")]


def available_languages() -> list[str]:
    """Return list of non-English language codes with built models."""
    return [m for m in available_models() if not m.startswith("en_")]


def _load_model(name: str) -> markovify.NewlineText | None:
    """Load a Markov model from disk, caching in memory."""
    if name in _models:
        return _models[name]
    path = os.path.join(_CORPORA_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        model = markovify.NewlineText.from_json(f.read())
    _models[name] = model
    return model


# Optional page-level genre lock. When set, every English _pick_model call on
# a page uses the same genre so the page reads as one document rather than a
# mix. Left unset, genre is re-sampled per call (more per-page variety, less
# coherence). generate_batch sets/clears this per page.
_locked_genre: str | None = None


def set_locked_genre(genre: str | None) -> None:
    """Lock the English genre for subsequent _pick_model calls, or clear with None."""
    global _locked_genre
    _locked_genre = genre


def get_locked_genre() -> str | None:
    return _locked_genre


def _pick_model(lang: str = None) -> tuple[str, markovify.NewlineText | None]:
    """Pick a model by language code or English genre.

    Returns (model_name, model) tuple. model may be None if not built.
    """
    if lang and not lang.startswith("en"):
        model = _load_model(lang)
        if model:
            return lang, model
    # English: honor the page-level lock if set, else sample per call.
    genre = _locked_genre or random.choice(english_genres())
    return genre, _load_model(genre)


def _accept_sample(text: str | None, lang: str | None) -> bool:
    """True when the sample passes the script-ratio filter (if any)."""
    if text is None:
        return False
    script = LANG_SCRIPTS.get(lang or "")
    if script is None:
        return True  # Latin-script langs: no filter
    return script_ratio(text, script) >= D["text"]["script_ratio_threshold"]
