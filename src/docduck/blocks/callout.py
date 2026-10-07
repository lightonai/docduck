"""Callout / info-box blocks (note, warning, tip, danger, info)."""

import random

from gi.repository import PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import pango_layout, rounded_rect
from ._registry import register_block


@register_block("callout", weight=6)
def draw_callout(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    """Render a callout/info box with colored background and labeled prefix."""
    d = D["callout"]
    lang = kw.get("lang")

    kind_name = random.choice(list(d["kinds"].keys()))
    kind = d["kinds"][kind_name]
    label = text_gen._markov_short(lang, max_words=d.get("label_max_words", 2)) or kind_name
    label = label.rstrip(".,;:").strip().title()
    bg = kind["bg"]
    border = kind["border"]

    size = style.body_size if style else random.choice(d["fallback_sizes"])
    font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"
    label_font = fonts.get("sans", size, bold=True) if fonts else f"DejaVu Sans Bold {size}"

    n_sent = random.randint(*d["n_sentences"])
    sentences = [text_gen._apply_mode(text_gen._make_sentence(lang)) for _ in range(n_sent)]

    h_pad = d["h_padding"]
    v_pad = d["v_padding"]
    bar_w = d["bar_width"]
    text_x = x + bar_w + h_pad

    label_layout = pango_layout(ctx, f"{label}:", label_font, width - bar_w - h_pad * 2)
    _, label_ext = label_layout.get_pixel_extents()
    label_w = label_ext.width + 8

    # Downsize body by dropping trailing sentences until it fits max_height.
    line_spacing = style.line_spacing if style else 2
    while sentences:
        body_text = " ".join(sentences)
        body_layout = pango_layout(
            ctx,
            body_text,
            font,
            width - bar_w - h_pad * 2 - label_w,
            spacing=line_spacing,
        )
        _, body_ext = body_layout.get_pixel_extents()
        content_h = max(label_ext.height, body_ext.height)
        block_h = content_h + v_pad * 2
        if max_height is None or block_h + d["bottom_margin"] <= max_height or len(sentences) == 1:
            break
        sentences.pop()

    ctx.set_source_rgb(*bg)
    rounded_rect(ctx, x, y, width, block_h, r=d["border_radius"])
    ctx.fill()

    ctx.set_source_rgb(*border)
    ctx.rectangle(x, y, bar_w, block_h)
    ctx.fill()

    ctx.set_source_rgb(*border)
    ctx.move_to(text_x, y + v_pad)
    PangoCairo.show_layout(ctx, label_layout)

    # Body (right of label on first line)
    ctx.set_source_rgb(*text_color)
    ctx.move_to(text_x + label_w, y + v_pad)
    PangoCairo.show_layout(ctx, body_layout)

    ground_truth = f"**{label}:** {body_text}"
    return BlockResult(
        height=block_h + d["bottom_margin"],
        text=ground_truth,
        data={"kind": kind_name, "label": label, "body": body_text},
    )
