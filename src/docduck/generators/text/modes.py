"""Adversarial content-mode handling.

The composer flips this at the start of each page so subsequent text
generation routes through the requested adversarial transform. Default
``"natural"`` leaves output untouched.
"""

from contextvars import ContextVar

from ... import adversarial

# Adversarial content mode. Default "natural" = unchanged Markov output.
# Composer sets this from PageConfig.features.content_mode.
_content_mode: ContextVar[str] = ContextVar("docduck_content_mode", default="natural")


def set_content_mode(mode: str | None) -> None:
    """Set the adversarial content mode for subsequent text-generation calls."""
    _content_mode.set(mode or "natural")


def get_content_mode() -> str:
    return _content_mode.get()


def _apply_mode(text: str) -> str:
    mode = _content_mode.get()
    return adversarial.transform(text, mode) if text else text
