"""Tests for the form-field registry (extensibility)."""

import cairo

from docduck.blocks.form import FieldContext, fields
from docduck.defaults import DEFAULTS


def _fc(**overrides):
    """Minimal FieldContext for testing field renderers directly."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
    defaults = dict(
        ctx=cairo.Context(surface),
        x=70,
        y=70,
        width=500,
        field_h=22,
        row_spacing=8,
        label="Name",
        prefix="",
        field_style="boxed",
        text_color=(0, 0, 0),
        accent_color=(0, 0, 0),
        font="DejaVu Sans 10",
        label_w=175,
        field_w=311,
        lang="en",
        d=DEFAULTS["form"],
    )
    defaults.update(overrides)
    return FieldContext(**defaults)


class TestFieldRegistry:
    def test_builtin_fields_registered(self):
        expected = {"text", "date", "checkbox", "radio", "signature", "multiline"}
        assert expected.issubset(set(fields.names()))

    def test_sample_returns_registered_name(self):
        for _ in range(20):
            assert fields.sample() in fields

    def test_can_register_new_field_type(self):
        from docduck.blocks.form import register_field

        @register_field("dropdown", weight=0.05)
        def render_dropdown(fc):
            fc.ctx.set_source_rgb(*fc.text_color)
            fc.ctx.rectangle(fc.x + fc.label_w, fc.y, fc.field_w, fc.field_h)
            fc.ctx.stroke()
            return fc.field_h + fc.row_spacing, f"{fc.label}: [▾]"

        assert "dropdown" in fields
        fc = _fc(label="Choose one")
        advance, gt = render_dropdown(fc)
        assert advance > 0
        assert "[▾]" in gt

        fields.unregister("dropdown")


class TestBuiltinFieldRenderers:
    def test_checkbox_returns_box_glyph(self):
        fc = _fc(label="I agree")
        render = fields.get("checkbox")
        advance, gt = render(fc)
        assert advance > 0
        assert gt.startswith(("☐", "☒"))
        assert "I agree" in gt

    def test_radio_returns_circle_glyph(self):
        fc = _fc(label="Yes")
        render = fields.get("radio")
        advance, gt = render(fc)
        assert advance > 0
        assert gt.startswith(("○", "●"))

    def test_signature_uses_underline(self):
        fc = _fc(label="Signature")
        render = fields.get("signature")
        advance, gt = render(fc)
        assert advance > 0
        assert "___" in gt
        assert "Signature" in gt

    def test_text_field_labeled(self):
        fc = _fc(label="Full Name")
        render = fields.get("text")
        advance, gt = render(fc)
        assert advance > 0
        assert gt.startswith("Full Name: ")

    def test_date_field_format(self):
        import random

        random.seed(0)
        render = fields.get("date")
        gt = ""
        for _ in range(20):
            fc = _fc(label="DOB")
            _, gt = render(fc)
            if "/" in gt:
                break
        assert "DOB" in gt

    def test_multiline_consumes_more_height(self):
        fc = _fc(label="Notes")
        render = fields.get("multiline")
        advance, gt = render(fc)
        # Multiline advances more than a single-line field
        assert advance > fc.field_h + fc.row_spacing
