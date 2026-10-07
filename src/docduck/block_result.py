"""Structured block result.

Every block's draw function returns a `BlockResult` carrying:
- `height`: total rendered height in pixels (required)
- `text`: ground-truth text, typically markdown-flavored (headings have '#',
  code blocks have fences, etc.): this is what serializers consume by default
- `data`: optional structured payload (e.g. table rows, list items) for
  serializers that want richer output than `text`
"""

from dataclasses import dataclass, field


@dataclass
class BlockResult:
    """Return value for block draw functions."""

    height: float
    text: str = ""
    data: dict = field(default_factory=dict)
