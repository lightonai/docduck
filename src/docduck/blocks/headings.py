"""Heading and subheading blocks."""

import random

from gi.repository import Pango

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import layout_height, pango_layout, show_text_layout
from ._registry import register_block


@register_block("heading", weight=1)
def draw_heading(
    ctx,
    x,
    y,
    width,
    *,
    text_color,
    accent_color,
    style=None,
    fonts=None,
    max_height=None,
    **kw,
):
    d = D["heading"]
    lang = kw.get("lang")
    title = text_gen.gen_heading(lang=lang)
    size = style.heading_size if style else random.choice(d["fallback_sizes"])
    font = fonts.get("serif", size, bold=True) if fonts else f"DejaVu Serif Bold {size}"

    heading_style = random.choice(d["styles"])

    align = Pango.Alignment.CENTER if heading_style == "centered" else Pango.Alignment.LEFT
    display_text = title.upper() if heading_style in ("small_caps", "plain") else title

    ctx.move_to(x, y)
    layout = pango_layout(ctx, display_text, font, width, alignment=align)

    if heading_style == "accent_bg":
        xp, yp = d["accent_bg_x_pad"], d["accent_bg_y_pad"]
        h = layout_height(layout) + d["accent_bg_height_pad"]
        ctx.set_source_rgba(*accent_color, 0.1)
        ctx.rectangle(x, y - 2, width, h)
        ctx.fill()
        ctx.move_to(x + xp, y + yp)
        layout = pango_layout(ctx, display_text, font, width - xp * 2, alignment=align)

    show_text_layout(ctx, layout, text_color)
    h = layout_height(layout)

    if heading_style == "underline":
        ctx.set_source_rgb(*accent_color)
        ctx.set_line_width(random.choice(d["underline_widths"]))
        lo, hi = d["underline_extent"]
        ctx.move_to(x, y + h + 4)
        ctx.line_to(x + width * random.uniform(lo, hi), y + h + 4)
        ctx.stroke()
        h += d["underline_padding"]
    elif heading_style == "accent_bg":
        h += 6

    return BlockResult(
        height=h + d["bottom_margin"],
        text=f"# {display_text}",
        data={"level": 1, "title": display_text, "heading_style": heading_style},
    )


@register_block("subheading", weight=6)
def draw_subheading(
    ctx,
    x,
    y,
    width,
    *,
    text_color,
    accent_color,
    style=None,
    fonts=None,
    max_height=None,
    **kw,
):
    d = D["subheading"]
    lang = kw.get("lang")
    title = text_gen.gen_heading(lang=lang)
    level = random.choice(d["levels"])
    size = style.subheading_size if style else random.choice(d["fallback_sizes"])
    font = fonts.get("sans", size, bold=True) if fonts else f"DejaVu Sans Bold {size}"

    ctx.move_to(x, y)
    layout = pango_layout(ctx, title, font, width)
    show_text_layout(ctx, layout, text_color)
    h = layout_height(layout)

    if level == 2 and random.random() < d["underline_probability"]:
        ctx.set_source_rgba(*accent_color, 0.4)
        ctx.set_line_width(0.8)
        ctx.move_to(x, y + h + 2)
        ctx.line_to(x + width * random.uniform(0.2, 0.5), y + h + 2)
        ctx.stroke()
        h += 4

    prefix = "#" * level
    return BlockResult(
        height=h + d["bottom_margin"],
        text=f"{prefix} {title}",
        data={"level": level, "title": title},
    )
