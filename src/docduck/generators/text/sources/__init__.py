"""Pluggable text sources. Default is Markov; HF is opt-in."""

from . import (
    hf,  # noqa: F401  (registers "hf")
    markov,  # noqa: F401  (registers "markov")
)
from ._base import (
    TextSource,
    get_text_source,
    register_text_source,
    reset_text_source,
    set_text_source,
    text_sources,
)

__all__ = [
    "TextSource",
    "get_text_source",
    "register_text_source",
    "reset_text_source",
    "set_text_source",
    "text_sources",
]
