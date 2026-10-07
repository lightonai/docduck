"""Code snippet block: colored background, optional border and accent bar."""

import random

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import layout_height, pango_layout, rounded_rect, show_text_layout
from ._registry import register_block


@register_block("code", weight=10)
def draw_code(
    ctx,
    x,
    y,
    width,
    *,
    text_color,
    accent_color=(0.3, 0.3, 0.8),
    style=None,
    fonts=None,
    max_height=None,
    **kw,
):
    d = D["code"]
    lang, code = text_gen.gen_code_snippet()
    font_size = min(style.body_size if style else 9, d["font_size_cap"])
    font = fonts.get("mono", font_size) if fonts else f"DejaVu Sans Mono {font_size}"

    # Downsize by dropping trailing lines until it fits.
    lines = code.split("\n")
    while lines:
        code = "\n".join(lines)
        layout = pango_layout(ctx, code, font, width - d["layout_width_pad"], spacing=2)
        code_h = layout_height(layout) + d["v_pad"] * 2
        if max_height is None or code_h + d["bottom_margin"] <= max_height or len(lines) == 1:
            break
        lines.pop()

    bg, is_dark = random.choice(d["bg_styles"])
    code_text_color = d["dark_text_color"] if is_dark else text_color

    radius = random.choice(d["border_radii"])
    if radius > 0:
        rounded_rect(ctx, x, y, width, code_h, radius)
    else:
        ctx.rectangle(x, y, width, code_h)
    ctx.set_source_rgb(*bg)
    ctx.fill()

    if random.random() < d["border_probability"]:
        if radius > 0:
            rounded_rect(ctx, x, y, width, code_h, radius)
        else:
            ctx.rectangle(x, y, width, code_h)
        ctx.set_source_rgba(*text_color, d["border_opacity"])
        ctx.set_line_width(d["border_width"])
        ctx.stroke()

    if random.random() < d["accent_bar_probability"]:
        ctx.set_source_rgba(*accent_color, 0.6)
        ctx.rectangle(x, y, d["accent_bar_width"], code_h)
        ctx.fill()

    ctx.move_to(x + d["h_pad"], y + d["v_pad"])
    layout = pango_layout(ctx, code, font, width - d["layout_width_pad"], spacing=2)
    show_text_layout(ctx, layout, code_text_color)

    return BlockResult(
        height=code_h + d["bottom_margin"],
        text=f"```{lang}\n{code}\n```",
        data={"language": lang, "code": code},
    )
