"""Shared rendering helpers used by block renderers.

These are internal utilities: not part of the public API. Blocks import
from here to share Pango layout helpers, the LaTeX math renderer, and
text-visibility clipping logic.
"""

import math
import random
import re
import warnings

import cairo
import numpy as np

# PyGObject Pango/PangoCairo versions are pinned in docduck/__init__.py.
from gi.repository import Pango, PangoCairo

from ..latex import render_latex as _render_latex_real

_MARKUP_RE = re.compile(r"<[^>]+>")

# Soft marker-pen backgrounds used by the opt-in highlight feature. The five
# colors cover yellow / amber / green / blue / pink: the typical palette of
# office highlighter pens. `wrap_highlight` is the single place that emits
# the Pango markup; `pango_to_markdown` above reverses it to `==text==`.
HIGHLIGHT_COLORS = ("#fff176", "#ffe082", "#c5e1a5", "#b3e5fc", "#f8bbd0")


def wrap_highlight(text: str) -> str:
    """Wrap text in a Pango bgcolor span (random highlight color)."""
    return f'<span bgcolor="{random.choice(HIGHLIGHT_COLORS)}">{text}</span>'


def maybe_highlight(text: str, prob: float) -> str:
    """Wrap `text` with probability `prob`; pass through on a miss or empty input."""
    if not text or prob <= 0 or random.random() >= prob:
        return text
    return wrap_highlight(text)


def strip_markup(text: str) -> str:
    """Strip Pango/HTML markup tags and unescape entities for ground truth."""
    text = _MARKUP_RE.sub("", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def pango_to_markdown(text: str) -> str:
    """Convert Pango inline markup to markdown so GT preserves formatting.

    Maps: <b>x</b> → **x**, <i>x</i> → *x*, <sup>N</sup> → ^N^, <s>x</s> → ~~x~~,
    <span bgcolor="…">x</span> → ==x== (markdown "mark"/highlight syntax).
    Unknown tags are stripped. XML entities are unescaped.
    """
    text = re.sub(r"<b>(.+?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.+?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<sup>(.+?)</sup>", r"^\1^", text, flags=re.DOTALL)
    text = re.sub(r"<s>(.+?)</s>", r"~~\1~~", text, flags=re.DOTALL)
    # Highlight: any <span> that carries a bgcolor/background attribute.
    text = re.sub(
        r'<span\s+[^>]*(?:bgcolor|background)\s*=\s*"[^"]*"[^>]*>(.+?)</span>',
        r"==\1==",
        text,
        flags=re.DOTALL,
    )
    text = _MARKUP_RE.sub("", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def pango_layout(
    ctx,
    text,
    font_desc_str,
    width,
    justify=False,
    alignment=Pango.Alignment.LEFT,
    spacing=2,
    markup=False,
):
    """Create a Pango layout configured with common options."""
    layout = PangoCairo.create_layout(ctx)
    layout.set_font_description(Pango.FontDescription(font_desc_str))
    layout.set_width(int(width * Pango.SCALE))
    layout.set_alignment(alignment)
    layout.set_justify(justify)
    layout.set_spacing(int(spacing * Pango.SCALE))
    if markup:
        layout.set_markup(text, -1)
    else:
        layout.set_text(text, -1)
    return layout


def layout_height(layout) -> int:
    _, ext = layout.get_pixel_extents()
    return ext.height


def show_text_layout(ctx, layout, color):
    """Set RGB color on `ctx` and render `layout` at the current cursor.

    The 2-line ``set_source_rgb`` + ``PangoCairo.show_layout`` pair is the
    common terminal step of every block renderer that draws text. Callers
    still own the cursor (``ctx.move_to``) and the post-render bookkeeping
    (height accumulation, etc.).
    """
    ctx.set_source_rgb(*color)
    PangoCairo.show_layout(ctx, layout)


def rounded_rect(ctx, x, y, w, h, r=6):
    """Build a rounded-rectangle path on the current context (no fill/stroke)."""
    ctx.new_path()
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.arc(x + w - r, y + r, r, 1.5 * math.pi, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
    ctx.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
    ctx.close_path()


def get_visible_text(layout, original_text, max_height=None):
    """Return only the text Pango actually rendered (fits within `max_height`).

    When `set_height()` clips a layout, Pango still reports all lines but only
    renders those that fit. We walk the line iterator to find the byte offset
    where visible text ends, then slice the original string.
    """
    if max_height is None:
        return original_text

    line_count = layout.get_line_count()
    if line_count == 0:
        return ""

    layout_iter = layout.get_iter()
    last_visible_byte_end = 0

    while True:
        y_range = layout_iter.get_line_yrange()
        line_bottom = y_range[1] / Pango.SCALE
        if line_bottom > max_height:
            break
        line = layout_iter.get_line_readonly()
        last_visible_byte_end = line.start_index + line.length
        if not layout_iter.next_line():
            break

    if last_visible_byte_end <= 0:
        return ""

    text_bytes = original_text.encode("utf-8")
    visible_bytes = text_bytes[:last_visible_byte_end]
    return visible_bytes.decode("utf-8", errors="ignore").rstrip()


def get_column_visible_text(layout, text, col_height):
    """For multi-column: get visible text and remaining text.

    Returns (visible_text, remaining_text, n_lines_shown).
    """
    line_count = layout.get_line_count()
    layout_iter = layout.get_iter()
    lines_shown = 0
    byte_offset = 0

    while True:
        yr = layout_iter.get_line_yrange()
        if yr[1] / Pango.SCALE > col_height:
            break
        line = layout_iter.get_line_readonly()
        byte_offset = line.start_index + line.length
        lines_shown += 1
        if not layout_iter.next_line():
            break

    if lines_shown < line_count and byte_offset > 0:
        text_bytes = text.encode("utf-8")
        char_offset = len(text_bytes[:byte_offset].decode("utf-8"))
        visible = text[:char_offset].rstrip()
        remaining = text[char_offset:].lstrip("\n")
    else:
        visible = text
        remaining = ""

    return visible, remaining, lines_shown


_math_parser = None


def _get_math_parser():
    """Lazy-load the matplotlib mathtext parser (fallback when pdflatex unavailable)."""
    global _math_parser
    if _math_parser is None:
        from matplotlib.mathtext import MathTextParser

        _math_parser = MathTextParser("agg")
    return _math_parser


def render_latex_line(tex, *, color, dpi, fontsize):
    """Render a single LaTeX string to a premultiplied BGRA numpy array.

    Uses real pdflatex when available; falls back to matplotlib mathtext.
    Returns (arr, depth) where arr is H×W×4 uint8 ready for Cairo FORMAT_ARGB32.
    """
    result = _render_latex_real(tex, color=color, dpi=dpi, fontsize=fontsize)
    if result is not None:
        return result

    import matplotlib.font_manager as fm

    parser = _get_math_parser()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        parsed = parser.parse(f"${tex}$", dpi=dpi, prop=fm.FontProperties(size=fontsize))
    gray = np.asarray(parsed.image, dtype=np.float32) / 255.0
    h, w = gray.shape
    r, g, b = color[0], color[1], color[2]
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[:, :, 0] = (b * gray * 255).astype(np.uint8)
    arr[:, :, 1] = (g * gray * 255).astype(np.uint8)
    arr[:, :, 2] = (r * gray * 255).astype(np.uint8)
    arr[:, :, 3] = (gray * 255).astype(np.uint8)
    return arr, parsed.depth


def composite_math_array(ctx, arr, x, y, width):
    """Composite a math RGBA array onto the context, centered horizontally.

    Returns (img_w, img_h) after scaling.
    """
    h, w = arr.shape[:2]
    math_surface = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, w, h)
    scale = min(width / w, 1.0)
    img_w = int(w * scale)
    img_h = int(h * scale)
    center_x = x + (width - img_w) / 2

    ctx.save()
    ctx.translate(center_x, y)
    ctx.scale(scale, scale)
    ctx.set_source_surface(math_surface, 0, 0)
    ctx.paint()
    ctx.restore()
    return img_w, img_h
