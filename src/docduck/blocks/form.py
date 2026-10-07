"""Form block: fill-in fields, checkboxes, radios, dates, signatures.

Field types self-register via `@register_field("name", weight=N)`. Adding a
new field type (e.g. dropdown, slider, barcode) means adding one function
with the decorator: no edits to draw_form.
"""

import math
import random
from dataclasses import dataclass

from gi.repository import PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ..registry import Registry
from ._helpers import layout_height, pango_layout
from ._registry import register_block

# Field renderers self-register here; `draw_form` dispatches by type.
fields = Registry("form_field")


def register_field(name: str, weight: float = 1.0):
    """Decorator that registers a form-field renderer function.

    The decorated function must accept a FieldContext and return
    (advance_y, ground_truth_line). The renderer controls its own drawing
    within the allotted field area.
    """
    return fields.register(name, weight=weight)


@dataclass
class FieldContext:
    """All the state a field renderer needs to draw itself."""

    ctx: object
    x: float
    y: float
    width: float
    field_h: float
    row_spacing: float
    label: str
    prefix: str
    field_style: str  # "underline" | "boxed"
    text_color: tuple
    accent_color: tuple
    font: str
    label_w: int
    field_w: int
    lang: str | None
    d: dict  # DEFAULTS["form"]


def _draw_text_field(ctx, x, y, w, h, style_kind, d):
    """Draw an input field rectangle (boxed) or baseline (underline)."""
    if style_kind == "boxed":
        ctx.set_source_rgb(*d["boxed_field_bg"])
        ctx.rectangle(x, y, w, h)
        ctx.fill()
        ctx.set_source_rgb(*d["boxed_field_border"])
        ctx.set_line_width(d["boxed_field_border_width"])
        ctx.rectangle(x, y, w, h)
        ctx.stroke()
    else:
        ctx.set_source_rgb(*d["underline_color"])
        ctx.set_line_width(d["underline_width"])
        ctx.move_to(x, y + h - 2)
        ctx.line_to(x + w, y + h - 2)
        ctx.stroke()


def _draw_checkbox_glyph(ctx, x, y, size, checked, text_color, d):
    ctx.set_source_rgb(*text_color)
    ctx.set_line_width(d["checkbox_border_width"])
    ctx.rectangle(x, y, size, size)
    ctx.stroke()
    if checked:
        ctx.set_line_width(1.2)
        ctx.move_to(x + 2, y + 2)
        ctx.line_to(x + size - 2, y + size - 2)
        ctx.move_to(x + size - 2, y + 2)
        ctx.line_to(x + 2, y + size - 2)
        ctx.stroke()


def _draw_radio_glyph(ctx, cx, cy, size, selected, text_color):
    ctx.set_source_rgb(*text_color)
    ctx.set_line_width(0.8)
    ctx.new_sub_path()
    ctx.arc(cx, cy, size / 2, 0, 2 * math.pi)
    ctx.stroke()
    if selected:
        ctx.new_sub_path()
        ctx.arc(cx, cy, size / 4, 0, 2 * math.pi)
        ctx.fill()
    ctx.new_path()


def _draw_label(ctx, x, y, width, text, font, text_color):
    ctx.set_source_rgb(*text_color)
    ctx.move_to(x, y + 2)
    lbl = pango_layout(ctx, text, font, width)
    PangoCairo.show_layout(ctx, lbl)


def _sample_date() -> str:
    mm = random.randint(1, 12)
    dd = random.randint(1, 28)
    yyyy = random.randint(1980, 2024)
    return f"{mm:02d} / {dd:02d} / {yyyy}"


def _sample_text_fill(lang):
    from ..table import gen as table_gen

    pool = table_gen._get_word_pool(lang)
    if pool and random.random() < 0.5:
        n = 2 if random.random() < 0.5 else 1
        if len(pool) >= n:
            return " ".join(random.sample(pool, n))
    s = text_gen._markov_short(lang, max_words=3)
    if s:
        return s.rstrip(".,;:!?")[:25].strip()
    return "Sample"


@register_field("checkbox", weight=0.25)
def render_checkbox(fc: FieldContext) -> tuple[float, str]:
    box_size = fc.d["checkbox_size"]
    box_y = fc.y + (fc.field_h - box_size) // 2
    checked = random.random() < fc.d["check_probability"]
    _draw_checkbox_glyph(fc.ctx, fc.x, box_y, box_size, checked, fc.text_color, fc.d)
    _draw_label(
        fc.ctx,
        fc.x + box_size + 8,
        fc.y,
        fc.width - box_size - 8,
        fc.prefix + fc.label,
        fc.font,
        fc.text_color,
    )
    mark = "☒" if checked else "☐"
    return fc.field_h + fc.row_spacing, f"{mark} {fc.prefix}{fc.label}"


@register_field("radio", weight=0.10)
def render_radio(fc: FieldContext) -> tuple[float, str]:
    box_size = fc.d["checkbox_size"]
    box_y = fc.y + (fc.field_h - box_size) // 2
    selected = random.random() < fc.d["check_probability"]
    _draw_radio_glyph(
        fc.ctx, fc.x + box_size / 2, box_y + box_size / 2, box_size, selected, fc.text_color
    )
    _draw_label(
        fc.ctx,
        fc.x + box_size + 8,
        fc.y,
        fc.width - box_size - 8,
        fc.prefix + fc.label,
        fc.font,
        fc.text_color,
    )
    mark = "●" if selected else "○"
    return fc.field_h + fc.row_spacing, f"{mark} {fc.prefix}{fc.label}"


@register_field("signature", weight=0.07)
def render_signature(fc: FieldContext) -> tuple[float, str]:
    sig_line_w = int(fc.width * 0.55)
    sig_x = fc.x + 10
    fc.ctx.set_source_rgb(*fc.d["underline_color"])
    fc.ctx.set_line_width(fc.d["underline_width"])
    fc.ctx.move_to(sig_x, fc.y + fc.field_h - 4)
    fc.ctx.line_to(sig_x + sig_line_w, fc.y + fc.field_h - 4)
    fc.ctx.stroke()
    _draw_label(
        fc.ctx,
        sig_x + sig_line_w + 10,
        fc.y,
        fc.width - sig_line_w - 20,
        fc.prefix + fc.label,
        fc.font,
        fc.text_color,
    )
    return fc.field_h + fc.row_spacing, f"{fc.prefix}{fc.label}: _________________"


def _render_labeled_input(fc: FieldContext, fill_text: str | None, extra_h: float = 0.0):
    """Shared renderer for labeled fields (text, date, multiline)."""
    _draw_label(
        fc.ctx,
        fc.x,
        fc.y,
        fc.label_w - 6,
        fc.prefix + fc.label + ":",
        fc.font,
        fc.text_color,
    )
    fx = fc.x + fc.label_w
    fh = fc.field_h + extra_h
    _draw_text_field(fc.ctx, fx, fc.y, fc.field_w, fh, fc.field_style, fc.d)
    if fill_text:
        fc.ctx.set_source_rgb(*fc.text_color)
        fc.ctx.move_to(fx + 6, fc.y + 3)
        layout = pango_layout(fc.ctx, fill_text, fc.font, fc.field_w - 12)
        PangoCairo.show_layout(fc.ctx, layout)

    value = fill_text or "_____"
    advance = fh + fc.row_spacing
    return advance, f"{fc.prefix}{fc.label}: {value}"


@register_field("text", weight=0.40)
def render_text_field(fc: FieldContext) -> tuple[float, str]:
    fill = None
    if random.random() < fc.d["fill_probability"]:
        fill = _sample_text_fill(fc.lang)
    return _render_labeled_input(fc, fill)


@register_field("date", weight=0.10)
def render_date_field(fc: FieldContext) -> tuple[float, str]:
    fill = _sample_date() if random.random() < fc.d["fill_probability"] else None
    return _render_labeled_input(fc, fill)


@register_field("multiline", weight=0.08)
def render_multiline_field(fc: FieldContext) -> tuple[float, str]:
    fill = None
    if random.random() < fc.d["fill_probability"]:
        s = text_gen._markov_short(fc.lang, max_words=15)
        if s:
            fill = s.strip()[:80]
    return _render_labeled_input(fc, fill, extra_h=fc.field_h)


def _pick_field_type():
    """Sample a field type name by weight from the registry, seeded from defaults."""
    d = D["form"]
    weights_override = d.get("field_type_weights", {})
    # Re-apply in case defaults changed at runtime
    if weights_override:
        fields.set_weights(weights_override)
    return fields.sample()


def _pick_field_style(d):
    probs = d["field_style_probabilities"]
    styles = list(probs.keys())
    return random.choices(styles, weights=[probs[s] for s in styles], k=1)[0]


def _pick_form_label(field_type, lang):
    s = text_gen._markov_short(lang, max_words=3)
    if s:
        cleaned = s.rstrip(".,;:!?")[:25].strip()
        if cleaned:
            return cleaned
    return field_type.capitalize()


@register_block("form", weight=5)
def draw_form(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    """Render a form section with labels, input fields, checkboxes, etc."""
    d = D["form"]
    lang = kw.get("lang")

    size = style.body_size if style else random.choice(d["fallback_sizes"])
    font = fonts.get("sans", size) if fonts else f"DejaVu Sans {size}"
    bold_font = fonts.get("sans", size, bold=True) if fonts else f"DejaVu Sans Bold {size}"

    field_style = _pick_field_style(d)
    n_fields = random.randint(*d["n_fields"])
    number_fields = random.random() < d["number_fields_probability"]
    has_border = random.random() < d["section_border_probability"]
    header_bg = random.random() < d["section_header_bg_probability"]

    section_title = None
    cur_y = y
    if random.random() < d["section_title_probability"]:
        section_title = text_gen.gen_heading(lang=lang)
        if header_bg:
            title_h = size + 8
            ctx.set_source_rgba(*accent_color, d["section_header_bg_opacity"])
            ctx.rectangle(x, cur_y, width, title_h)
            ctx.fill()
        ctx.set_source_rgb(*text_color)
        ctx.move_to(x + 8, cur_y + 2)
        title_layout = pango_layout(ctx, section_title, bold_font, width - 16)
        PangoCairo.show_layout(ctx, title_layout)
        cur_y += layout_height(title_layout) + 8

    label_w = int(width * d["label_width_fraction"])
    field_w = width - label_w - 14
    field_h = d["field_height"]
    row_spacing = d["row_spacing"]

    gt_lines = []
    fields_out = []
    if section_title:
        gt_lines.append(f"**{section_title}**")

    for i in range(n_fields):
        if max_height is not None and (cur_y - y) + field_h + row_spacing > max_height:
            break

        ftype = _pick_field_type()
        label = _pick_form_label(ftype, lang)
        prefix = f"{i + 1}. " if number_fields else ""

        fc = FieldContext(
            ctx=ctx,
            x=x,
            y=cur_y,
            width=width,
            field_h=field_h,
            row_spacing=row_spacing,
            label=label,
            prefix=prefix,
            field_style=field_style,
            text_color=text_color,
            accent_color=accent_color,
            font=font,
            label_w=label_w,
            field_w=field_w,
            lang=lang,
            d=d,
        )
        renderer = fields.get(ftype)
        assert renderer is not None, f"form field type {ftype!r} not registered"
        advance, gt_line = renderer(fc)
        gt_lines.append(gt_line)
        fields_out.append({"type": ftype, "label": label, "gt": gt_line})
        cur_y += advance

    if has_border:
        ctx.set_source_rgba(*text_color, d["section_border_opacity"])
        ctx.set_line_width(0.6)
        ctx.rectangle(x - 4, y - 4, width + 8, cur_y - y + 4)
        ctx.stroke()

    ground_truth = "\n".join(gt_lines)
    return BlockResult(
        height=cur_y - y + d["bottom_margin"],
        text=ground_truth,
        data={"section_title": section_title, "fields": fields_out},
    )
