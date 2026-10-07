"""Pluggable page chrome: banner, running header, page number, border, etc.

Stages (in order): BACKGROUND, BEFORE_BLOCKS, BLOCK_INJECTION, AFTER_BLOCKS.
Each chrome function checks its own activation flag on `style` and returns an
optional dict to merge into `chrome_state` (downstream chrome reads this).
"""

from ._registry import ChromeStage, chrome, register_chrome

# isort: split
# Submodule imports trigger self-registration: must come after _registry.
from . import (  # noqa: F401
    banner,
    edge_shadow,
    logo_inject,
    page_border,
    page_number,
    running_header,
)

__all__ = [
    "chrome",
    "register_chrome",
    "ChromeStage",
]
