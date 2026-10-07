"""Blockquote: quoted-text block with left accent bar and optional attribution."""

import random

from gi.repository import Pango, PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import layout_height, pango_layout, show_text_layout
from ._registry import register_block


@register_block("blockquote", weight=5)
def draw_blockquote(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    d = D["blockquote"]
    lang = kw.get("lang")
    text = text_gen.gen_blockquote(lang=lang)
    size = style.body_size if style else random.choice(d["fallback_sizes"])
    spacing = style.line_spacing if style else 2.5
    font = fonts.get("serif", size, italic=True) if fonts else f"DejaVu Serif Italic {size}"

    bar_width = d["bar_width"]
    bar_pad = d["bar_padding"]
    text_x = x + bar_width + bar_pad
    text_w = width - bar_width - bar_pad

    # Downsize by dropping trailing sentences until it fits max_height.
    parts = [p for p in text.split(". ") if p.strip()]
    while parts:
        text = ". ".join(parts)
        if not text.endswith("."):
            text += "."
        layout = pango_layout(ctx, text, font, text_w, justify=True, spacing=spacing)
        block_h = layout_height(layout) + d["v_padding"] * 2
        if max_height is None or block_h + d["bottom_margin"] <= max_height or len(parts) == 1:
            break
        parts.pop()
    ctx.move_to(text_x, y)

    if random.random() < d["bg_probability"]:
        ctx.set_source_rgba(*accent_color, 0.05)
        ctx.rectangle(x, y, width, block_h)
        ctx.fill()

    ctx.set_source_rgba(*accent_color, d["bar_opacity"])
    ctx.rectangle(x, y, bar_width, block_h)
    ctx.fill()

    ctx.move_to(text_x, y + d["v_padding"])
    layout = pango_layout(ctx, text, font, text_w, justify=True, spacing=spacing)
    show_text_layout(ctx, layout, text_color)

    attribution = ""
    if random.random() < d["attribution_probability"]:
        attr_text = f"— {text_gen._apply_mode(text_gen._make_sentence(lang))}"
        attr_text = attr_text[:60].rsplit(" ", 1)[0].rstrip()
        attr_font = fonts.get("serif", size - 1) if fonts else f"DejaVu Serif {size - 1}"
        attr_y = y + block_h
        ctx.move_to(text_x, attr_y)
        attr_layout = pango_layout(
            ctx, attr_text, attr_font, text_w, alignment=Pango.Alignment.RIGHT
        )
        ctx.set_source_rgba(*text_color, 0.6)
        PangoCairo.show_layout(ctx, attr_layout)
        attr_h = layout_height(attr_layout) + 4
        attribution = f"\n{attr_text}"
    else:
        attr_h = 0

    ground_truth = f"> {text}{attribution}"
    return BlockResult(
        height=block_h + attr_h + d["bottom_margin"],
        text=ground_truth,
        data={"quote": text, "attribution": attribution.lstrip("\n")},
    )
