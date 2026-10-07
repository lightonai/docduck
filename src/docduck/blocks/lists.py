"""List (bulleted/numbered/nested) and definition-list blocks."""

import random

from gi.repository import PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import layout_height, pango_layout
from ._registry import register_block


@register_block("list", weight=10)
def draw_list(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    d = D["list"]
    lang = kw.get("lang")
    items = text_gen.gen_list_items(random.randint(*d["item_count"]), lang=lang)
    size = style.body_size if style else random.choice(d["fallback_sizes"])
    spacing = style.line_spacing if style else 2.0
    font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"

    list_type = random.choice(d["list_types"])
    indent = d["indent"]
    bullet_indent = d["bullet_indent"]
    nested_prob = d["nested_probability"]
    cur_y = y
    gt_lines = []

    for i, item_text in enumerate(items):
        if max_height and (cur_y - y) > max_height - 30:
            break

        nest_level = 1 if i > 0 and random.random() < nested_prob else 0
        item_x = x + indent * nest_level
        item_w = width - indent * nest_level

        if list_type == "bullet":
            bullets = ["•", "◦", "▪", "–", "■", "▸"]
            bullet = bullets[nest_level % len(bullets)]
            gt_prefix = "  " * nest_level + "- "
        elif list_type == "numbered":
            bullet = f"{i + 1}."
            gt_prefix = "  " * nest_level + f"{i + 1}. "
        else:  # letter
            bullet = f"{chr(97 + i % 26)})"
            gt_prefix = "  " * nest_level + f"{chr(97 + i % 26)}) "

        ctx.move_to(item_x, cur_y)
        bullet_layout = pango_layout(ctx, bullet, font, bullet_indent)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, bullet_layout)

        text_x = item_x + bullet_indent
        text_w = item_w - bullet_indent
        ctx.move_to(text_x, cur_y)
        layout = pango_layout(ctx, item_text, font, text_w, justify=False, spacing=spacing)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, layout)

        item_h = layout_height(layout)
        cur_y += item_h + d["item_spacing"]
        gt_lines.append(f"{gt_prefix}{item_text}")

    total_h = cur_y - y + d["bottom_margin"]
    return BlockResult(
        height=total_h,
        text="\n".join(gt_lines),
        data={"list_type": list_type, "items": items},
    )


@register_block("definition_list", weight=4)
def draw_definition_list(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    d = D["definition_list"]
    lang = kw.get("lang")
    items = text_gen.gen_definition_items(random.randint(*d["item_count"]), lang=lang)
    size = style.body_size if style else random.choice(d["fallback_sizes"])
    spacing = style.line_spacing if style else 2.0
    term_font = fonts.get("sans", size, bold=True) if fonts else f"DejaVu Sans Bold {size}"
    defn_font = fonts.get("serif", size) if fonts else f"DejaVu Serif {size}"
    defn_indent = d["definition_indent"]

    cur_y = y
    gt_lines = []

    for term, defn in items:
        if max_height and (cur_y - y) > max_height - 40:
            break

        ctx.move_to(x, cur_y)
        term_layout = pango_layout(ctx, term, term_font, width)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, term_layout)
        cur_y += layout_height(term_layout) + 2

        ctx.move_to(x + defn_indent, cur_y)
        defn_layout = pango_layout(ctx, defn, defn_font, width - defn_indent, spacing=spacing)
        ctx.set_source_rgb(*text_color)
        PangoCairo.show_layout(ctx, defn_layout)
        cur_y += layout_height(defn_layout) + d["item_spacing"]

        gt_lines.append(f"**{term}**")
        gt_lines.append(f": {defn}")

    total_h = cur_y - y + d["bottom_margin"]
    return BlockResult(
        height=total_h,
        text="\n".join(gt_lines),
        data={"items": items},
    )
