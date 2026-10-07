"""Generator context: carries language and future DI slots through generators.

Avoids module-level globals (e.g. the old `table_gen._lang`). A `GenContext`
is created at the top of each generation call and passed down explicitly.
"""

from dataclasses import dataclass


@dataclass
class GenContext:
    """Immutable-ish context threaded through content generators.

    lang: target language code (None or 'en' for English).
    """

    lang: str | None = None
