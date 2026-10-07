"""Horizontal rule block: thin, thick, double, dashed, dotted, ornament."""

import random

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ._registry import register_block


def _measure_rule(content_w, **kw):
    return D["rule"]["height"]


@register_block("rule", weight=4, measure=_measure_rule)
def draw_rule(ctx, x, y, width, *, text_color, **kw):
    d = D["rule"]
    rule_style = random.choice(d["styles"])
    lo, hi = d["width_fraction"]
    rule_w = width * random.uniform(lo, hi)
    rx = x + (width - rule_w) / 2
    mid_y = 5

    ctx.set_source_rgba(*text_color, d["opacity"])

    if rule_style == "thin":
        ctx.set_line_width(d["thin_width"])
        ctx.move_to(rx, y + mid_y)
        ctx.line_to(rx + rule_w, y + mid_y)
        ctx.stroke()
    elif rule_style == "thick":
        ctx.set_line_width(d["thick_width"])
        ctx.move_to(rx, y + mid_y)
        ctx.line_to(rx + rule_w, y + mid_y)
        ctx.stroke()
    elif rule_style == "double":
        gap = d["double_gap"]
        ctx.set_line_width(d["double_width"])
        ctx.move_to(rx, y + mid_y - gap // 2)
        ctx.line_to(rx + rule_w, y + mid_y - gap // 2)
        ctx.move_to(rx, y + mid_y + gap // 2)
        ctx.line_to(rx + rule_w, y + mid_y + gap // 2)
        ctx.stroke()
    elif rule_style == "dashed":
        ctx.set_line_width(d["dashed_width"])
        ctx.set_dash(d["dashed_pattern"])
        ctx.move_to(rx, y + mid_y)
        ctx.line_to(rx + rule_w, y + mid_y)
        ctx.stroke()
        ctx.set_dash([])
    elif rule_style == "dots":
        ctx.set_line_width(d["dots_width"])
        ctx.set_dash(d["dots_pattern"])
        ctx.move_to(rx, y + mid_y)
        ctx.line_to(rx + rule_w, y + mid_y)
        ctx.stroke()
        ctx.set_dash([])
    else:  # ornament
        mid = rx + rule_w / 2
        gap = d["ornament_gap"]
        sz = d["ornament_size"]
        ctx.set_line_width(d["thin_width"])
        ctx.move_to(rx, y + mid_y)
        ctx.line_to(mid - gap, y + mid_y)
        ctx.stroke()
        ctx.move_to(mid + gap, y + mid_y)
        ctx.line_to(rx + rule_w, y + mid_y)
        ctx.stroke()
        ctx.move_to(mid, y + mid_y - sz + 1)
        ctx.line_to(mid + sz, y + mid_y)
        ctx.line_to(mid, y + mid_y + sz - 1)
        ctx.line_to(mid - sz, y + mid_y)
        ctx.close_path()
        ctx.fill()

    return BlockResult(height=d["height"], text="---")
