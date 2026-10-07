"""Logo block: corporate/academic branding (geometric, monogram, wordmark)."""

import math
import random

from gi.repository import Pango, PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ._helpers import pango_layout, rounded_rect
from ._registry import register_block


def _measure_logo(content_w, **kw):
    d = D["logo"]
    return d["height"] + d["bottom_margin"]


def _gen_company_name() -> str:
    """Pick a company/organization name from the configured pools."""
    d = D["logo"]
    word = random.choice(d["company_words"])
    suffix = random.choice(d["company_suffixes"])
    return f"{word} {suffix}".strip() if suffix else word


def _draw_shape(ctx, shape, cx, cy, size, color):
    """Draw a logo shape at (cx, cy) with the given size and fill color."""
    ctx.set_source_rgb(*color)
    if shape == "square":
        ctx.rectangle(cx - size / 2, cy - size / 2, size, size)
        ctx.fill()
    elif shape == "rounded_square":
        r = size * 0.18
        rounded_rect(ctx, cx - size / 2, cy - size / 2, size, size, r=r)
        ctx.fill()
    elif shape == "circle":
        ctx.arc(cx, cy, size / 2, 0, 2 * math.pi)
        ctx.fill()
    elif shape == "triangle":
        ctx.move_to(cx, cy - size / 2)
        ctx.line_to(cx + size / 2, cy + size / 2)
        ctx.line_to(cx - size / 2, cy + size / 2)
        ctx.close_path()
        ctx.fill()
    elif shape == "stacked":
        half = size / 2
        ctx.rectangle(cx - half, cy - half, half, half)
        ctx.fill()
        lighter = tuple(min(1.0, c + 0.2) for c in color)
        ctx.set_source_rgb(*lighter)
        ctx.rectangle(cx, cy, half, half)
        ctx.fill()


@register_block("logo", weight=1, measure=_measure_logo)
def draw_logo(ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, **kw):
    """Render a corporate/organization logo at the top of the page."""
    d = D["logo"]
    style_kind = random.choice(d["styles"])
    company = _gen_company_name()

    primary = getattr(style, "primary_color", None) or accent_color
    sans_name = fonts.sans if fonts else "DejaVu Sans"
    text_size = d["text_size"]
    shape_size = d["shape_size"]
    pad = d["padding"]
    total_h = d["height"]

    cy = y + total_h / 2

    if style_kind == "geometric":
        shape = random.choice(d["shapes"])
        _draw_shape(ctx, shape, x + shape_size / 2, cy, shape_size, primary)
        font_str = f"{sans_name} Bold {text_size}"
        text_x = x + shape_size + pad
        ctx.move_to(text_x, cy - text_size * 0.7)
        layout = pango_layout(ctx, company, font_str, width - shape_size - pad)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, layout)

    elif style_kind == "monogram":
        initials = "".join(w[0] for w in company.split()[:2]).upper()
        _draw_shape(ctx, "rounded_square", x + shape_size / 2, cy, shape_size, primary)
        text_on = (
            style.text_on_primary
            if style and hasattr(style, "text_on_primary")
            else (1.0, 1.0, 1.0)
        )
        mono_font = f"{sans_name} Bold {int(shape_size * 0.55)}"
        ctx.set_source_rgb(*text_on)
        layout = pango_layout(
            ctx, initials, mono_font, shape_size, alignment=Pango.Alignment.CENTER
        )
        _, ext = layout.get_pixel_extents()
        ctx.move_to(x, cy - ext.height / 2)
        PangoCairo.show_layout(ctx, layout)
        font_str = f"{sans_name} {text_size}"
        ctx.set_source_rgb(*text_color)
        text_x = x + shape_size + pad
        ctx.move_to(text_x, cy - text_size * 0.7)
        layout = pango_layout(ctx, company, font_str, width - shape_size - pad)
        PangoCairo.show_layout(ctx, layout)

    else:  # wordmark: stylized text only
        font_str = f"{sans_name} Bold {text_size + 4}"
        ctx.move_to(x, cy - text_size)
        layout = pango_layout(ctx, company.upper(), font_str, width)
        ctx.set_source_rgb(*primary)
        PangoCairo.show_layout(ctx, layout)

    # GT reflects what's actually shown: wordmark renders uppercase.
    shown = company.upper() if style_kind == "wordmark" else company
    return BlockResult(
        height=total_h + d["bottom_margin"],
        text=f"**{shown}**",
        data={"company": company, "style": style_kind, "shown": shown},
    )
