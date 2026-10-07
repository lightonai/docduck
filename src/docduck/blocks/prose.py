"""Prose, tiny-text (footnotes), and multicolumn prose blocks."""

import random

from gi.repository import Pango

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import (
    get_column_visible_text,
    get_visible_text,
    layout_height,
    pango_layout,
    pango_to_markdown,
    show_text_layout,
    strip_markup,
)
from ._registry import register_block


def _markup_visible_prefix(markup_text: str, visible_plain: str) -> str:
    """Return the markdown version of `markup_text` truncated to match
    the length of `visible_plain` (which is the stripped-markup prefix).

    Converts Pango markup to markdown, then if truncation happened, trims
    the markdown to the last complete word of `visible_plain`.
    """
    md_full = pango_to_markdown(markup_text)
    plain_full = strip_markup(markup_text)
    if visible_plain.strip() == plain_full.strip():
        return md_full
    # Truncation happened. Find the last word boundary in visible_plain
    # and locate it in md_full; emit the prefix up to there.
    vp = visible_plain.rstrip()
    if not vp:
        return ""
    tail_n = D["prose"]["tail_search_chars"]
    tail = vp[-tail_n:] if len(vp) > tail_n else vp
    idx = md_full.rfind(tail)
    if idx < 0:
        # Fallback: return plain visible (no markdown) rather than break
        return visible_plain
    return md_full[: idx + len(tail)]


@register_block("prose", weight=25)
def draw_prose(ctx, x, y, width, *, text_color, style=None, fonts=None, max_height=None, **kw):
    d = D["prose"]
    lang = kw.get("lang")
    n_para = random.randint(*d["n_paragraphs"])
    # Strikethrough mode emits Pango <s>…</s> tags; force markup=True so
    # Pango renders them as visual strikes.
    use_markup = random.random() < 0.5 or text_gen.get_content_mode() == "strikethrough"
    text = text_gen.gen_paragraphs(n_para, lang=lang, markup=use_markup)
    size = style.body_size if style else random.choice(d["fallback_sizes"])
    spacing = style.line_spacing if style else d["fallback_line_spacing"]
    justify = style.justify if style else True
    font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"
    indent = int(size * random.uniform(1.5, 2.5) * Pango.SCALE)

    cur_y = y
    visible_parts = []
    paragraphs = text.split("\n\n")
    for pi, para in enumerate(paragraphs):
        if max_height and (cur_y - y) >= max_height - 10:
            break
        ctx.move_to(x, cur_y)
        remaining_h = (max_height - (cur_y - y)) if max_height else None
        layout = pango_layout(
            ctx, para, font, width, justify=justify, spacing=spacing, markup=use_markup
        )
        layout.set_indent(indent)
        if remaining_h:
            layout.set_height(int(remaining_h * Pango.SCALE))
        show_text_layout(ctx, layout, text_color)
        h = layout_height(layout)
        # For visible text extraction, use the plain text version; then
        # promote to markdown so bold/italic/sup markup survives into GT.
        plain_para = strip_markup(para) if use_markup else para
        visible = get_visible_text(layout, plain_para, remaining_h)
        if visible:
            visible_parts.append(_markup_visible_prefix(para, visible) if use_markup else visible)
        cur_y += h + int(size * 0.4)

    total_h = cur_y - y + d["bottom_margin"]
    return BlockResult(
        height=total_h,
        text="\n\n".join(visible_parts),
        data={"paragraphs": visible_parts},
    )


@register_block("tiny_text", weight=1)
def draw_tiny_text(ctx, x, y, width, *, text_color, style=None, fonts=None, max_height=None, **kw):
    d = D["tiny_text"]
    lang = kw.get("lang")
    n_footnotes = random.randint(*d["footnote_count"])
    size = style.tiny_size if style else random.choice(d["fallback_sizes"])
    font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"

    start_y = y
    if random.random() < d["rule_probability"]:
        ctx.set_source_rgba(*text_color, d["rule_opacity"])
        ctx.set_line_width(d["rule_width"])
        ctx.move_to(x, y)
        ctx.line_to(x + width * d["rule_extent"], y)
        ctx.stroke()
        y += d["rule_spacing"]

    # Generate once, then drop footnotes until it fits within max_height.
    text = text_gen.gen_footnotes(n_footnotes, lang=lang)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    while lines:
        text = "\n".join(lines)
        layout = pango_layout(ctx, text, font, width, spacing=d["line_spacing"])
        total_h = (y - start_y) + layout_height(layout) + d["bottom_margin"]
        if max_height is None or total_h <= max_height or len(lines) == 1:
            break
        lines.pop()  # drop last footnote and retry

    ctx.move_to(x, y)
    show_text_layout(ctx, layout, text_color)
    return BlockResult(
        height=total_h,
        text=text,
        data={"footnotes": lines},
    )


@register_block("multicolumn", weight=8)
def draw_multicolumn(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=300, **kw
):
    d = D["multicolumn"]
    lang = kw.get("lang")
    n_cols = random.choice(d["column_counts"])
    gutter = random.randint(*d["gutter_width"])
    col_w = (width - gutter * (n_cols - 1)) // n_cols
    text = text_gen.gen_paragraphs(
        random.randint(*d["n_paragraphs"]), min_sentences=3, max_sentences=6, lang=lang
    )
    size = style.body_size if style else random.choice(d["fallback_sizes"])
    spacing = style.line_spacing if style else d["fallback_line_spacing"]
    font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"
    remaining = text
    col_height = min(max_height, d["max_column_height"])
    actual_height = 0
    visible_parts = []

    for col in range(n_cols):
        if not remaining:
            break
        col_x = x + col * (col_w + gutter)
        ctx.move_to(col_x, y)

        layout = pango_layout(ctx, remaining, font, col_w, justify=True, spacing=spacing)
        layout.set_indent(int(size * 2.0 * Pango.SCALE))
        layout.set_height(int(col_height * Pango.SCALE))
        show_text_layout(ctx, layout, text_color)
        actual_height = max(actual_height, layout_height(layout))

        visible, remaining, _ = get_column_visible_text(layout, remaining, col_height)
        visible_parts.append(visible)

        if col < n_cols - 1 and remaining:
            rule_x = col_x + col_w + gutter / 2
            ctx.set_source_rgba(*accent_color, d["separator_opacity"])
            ctx.set_line_width(d["separator_width"])
            ctx.move_to(rule_x, y)
            ctx.line_to(rule_x, y + actual_height)
            ctx.stroke()

    ground_truth = " ".join(visible_parts)
    return BlockResult(
        height=actual_height + d["bottom_margin"],
        text=ground_truth,
        data={"columns": visible_parts},
    )
