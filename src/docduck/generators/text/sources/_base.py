"""TextSource interface: pluggable backends for sentence/title generation.

The block renderers (prose, blockquote, list, definition, heading, title)
ask the active TextSource for raw text. Markov is the built-in default; a
HF-dataset source ships in `hf.py`. Custom sources can be added with
`@register_text_source("name")`.

The active source is process-global, mirroring the existing
`set_content_mode` pattern. Set once before generation, queried by every
`gen_*` call.
"""

from abc import ABC, abstractmethod

from ....registry import Registry

text_sources: Registry = Registry("text_source")


class TextSource(ABC):
    """Abstract source of human-readable text for the block renderers.

    Implementations return raw text. Post-processing (content_mode,
    Pango markup) is applied by the caller in `sentences.py` /
    `structured.py`, so sources do not need to know about it.
    """

    @abstractmethod
    def sentence(self, lang: str | None) -> str:
        """One sentence. Block renderers stitch these into paragraphs,
        list items, blockquote bodies, definition bodies."""

    @abstractmethod
    def short(self, lang: str | None, max_words: int = 12) -> str | None:
        """A short phrase (truncated to ~max_words) for titles, headings,
        definition terms, and form field values. Return None to let the
        caller fall back to the template-based generator."""


def register_text_source(name: str, weight: float = 1.0):
    """Decorator: register a factory under `name`."""
    return text_sources.register(name, weight=weight)


_active: TextSource | None = None


def get_text_source() -> TextSource:
    """Return the active source, lazily instantiating MarkovSource on first use."""
    global _active
    if _active is None:
        from .markov import MarkovSource

        _active = MarkovSource()
    return _active


def set_text_source(name: str, **kwargs) -> TextSource:
    """Switch the active source. Factory kwargs flow through to its __init__."""
    global _active
    factory = text_sources.get(name)
    if factory is None:
        raise KeyError(f"unknown text source {name!r}; registered: {list(text_sources.as_dict())}")
    _active = factory(**kwargs)
    return _active


def reset_text_source() -> None:
    """Restore the default Markov source on the next `get_text_source()`."""
    global _active
    _active = None
