"""Math equation block: renders LaTeX via pdflatex (fallback: matplotlib mathtext)."""

import random

from gi.repository import Pango, PangoCairo

from .. import config
from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import math as math_gen
from ._helpers import composite_math_array, pango_layout, render_latex_line
from ._registry import register_block


@register_block("math", weight=10)
def draw_math(ctx, x, y, width, *, text_color, style=None, fonts=None, **kw):
    d = D["math"]
    is_multiline = random.random() < d["multiline_probability"] and config.MATH_EQUATIONS_MULTILINE
    label = f"({random.randint(*d['label_range'])})"
    fontsize = random.randint(*d["fontsize_range"])
    dpi = random.choice(d["dpi_choices"])

    if is_multiline:
        eq_lines = math_gen.gen_equation_multiline()
        total_h = 0
        line_spacing = random.randint(*d["multiline_spacing"])

        for i, line_tex in enumerate(eq_lines):
            arr, _ = render_latex_line(line_tex, color=text_color, dpi=dpi, fontsize=fontsize)
            _, line_h = composite_math_array(ctx, arr, x, y + total_h, width)
            total_h += line_h + line_spacing

        raw_tex = "\n".join(eq_lines)
    else:
        eq = math_gen.gen_equation()
        arr, _ = render_latex_line(eq, color=text_color, dpi=dpi, fontsize=fontsize)
        _, total_h = composite_math_array(ctx, arr, x, y, width)
        raw_tex = eq

    label_size = max(d["min_label_size"], (style.body_size if style else 9))
    label_font = fonts.get("serif", label_size) if fonts else f"DejaVu Serif {label_size}"
    label_y = y + total_h / 2 - label_size / 2 if not is_multiline else y + total_h - label_size - 4
    ctx.move_to(x, label_y)
    label_layout = pango_layout(ctx, label, label_font, width, alignment=Pango.Alignment.RIGHT)
    ctx.set_source_rgb(*text_color)
    PangoCairo.show_layout(ctx, label_layout)

    ground_truth = f"$$\n{raw_tex}\n\\quad {label}\n$$"
    return BlockResult(
        height=total_h + d["bottom_margin"],
        text=ground_truth,
        data={"latex": raw_tex, "label": label, "multiline": is_multiline},
    )
