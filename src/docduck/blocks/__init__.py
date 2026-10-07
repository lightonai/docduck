"""Block renderers: one file per block type.

Built-in blocks self-register via `@register_block("name", weight=N)` on import.
Adding a new block means dropping a file that decorates its `draw_*` function.
"""

# PyGObject Pango/PangoCairo versions are pinned in docduck/__init__.py.
# Importing every block module triggers self-registration.
from . import (  # noqa: F401
    blockquote,
    callout,
    code,
    form,
    headings,
    image,
    lists,
    logo,
    math,
    prose,
    rule,
    table,
)
from ._helpers import (
    composite_math_array,
    get_column_visible_text,
    get_visible_text,
    layout_height,
    pango_layout,
    render_latex_line,
    rounded_rect,
    strip_markup,
)
from ._registry import blocks, register_block
from .blockquote import draw_blockquote
from .callout import draw_callout
from .code import draw_code
from .form import draw_form
from .headings import draw_heading, draw_subheading
from .image import draw_image_placeholder
from .lists import draw_definition_list, draw_list
from .logo import draw_logo
from .math import draw_math
from .prose import draw_multicolumn, draw_prose, draw_tiny_text
from .rule import draw_rule
from .table import draw_table

BLOCK_TYPES = blocks.as_dict()

__all__ = [
    "blocks",
    "register_block",
    "BLOCK_TYPES",
    "pango_layout",
    "layout_height",
    "rounded_rect",
    "strip_markup",
    "get_visible_text",
    "get_column_visible_text",
    "render_latex_line",
    "composite_math_array",
    "draw_heading",
    "draw_subheading",
    "draw_prose",
    "draw_tiny_text",
    "draw_multicolumn",
    "draw_blockquote",
    "draw_callout",
    "draw_list",
    "draw_definition_list",
    "draw_table",
    "draw_math",
    "draw_code",
    "draw_image_placeholder",
    "draw_rule",
    "draw_logo",
    "draw_form",
]
