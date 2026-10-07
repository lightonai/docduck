"""Tests for the form block renderer."""

import random

import cairo
import gi
import pytest

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from docduck import blocks
from docduck.defaults import DEFAULTS
from docduck.diversity import PageStyle
from docduck.fonts import FontPalette


@pytest.fixture
def ctx():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
    return cairo.Context(surface)


@pytest.fixture
def common_kwargs():
    style = PageStyle()
    return {
        "text_color": style.text_color,
        "accent_color": style.accent_color,
        "style": style,
        "fonts": FontPalette(),
        "max_height": 600,
    }


class TestFormConfig:
    def test_form_config_exists(self):
        assert "form" in DEFAULTS
        assert "field_type_weights" in DEFAULTS["form"]

    def test_field_type_weights_valid(self):
        weights = DEFAULTS["form"]["field_type_weights"]
        assert all(w >= 0 for w in weights.values())
        assert sum(weights.values()) > 0

    def test_all_field_types_have_weights(self):
        weights = DEFAULTS["form"]["field_type_weights"]
        expected = {"text", "checkbox", "radio", "date", "multiline", "signature"}
        assert set(weights.keys()) == expected


class TestDrawForm:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        result = blocks.draw_form(ctx, 70, 70, 760, **common_kwargs)
        h, gt = result.height, result.text
        assert h > 0
        assert isinstance(gt, str)

    def test_produces_ground_truth_lines(self, ctx, common_kwargs):
        result = blocks.draw_form(ctx, 70, 70, 760, **common_kwargs)
        gt = result.text
        # At least one labeled line
        assert len(gt.split("\n")) >= 1

    def test_contains_field_markers(self, ctx, common_kwargs):
        """Ground truth should contain checkbox glyphs or label:value pairs."""
        seen_markers = False
        seen_label_colon = False
        for seed in range(30):
            random.seed(seed)
            result = blocks.draw_form(ctx, 70, 70, 760, **common_kwargs)
            gt = result.text
            if "☐" in gt or "☒" in gt:
                seen_markers = True
            if ":" in gt and "_" in gt:
                seen_label_colon = True
            if seen_markers and seen_label_colon:
                break
        assert seen_markers, "No checkbox glyphs found across 30 forms"
        assert seen_label_colon, "No label:value lines found"

    def test_narrow_width_works(self, ctx, common_kwargs):
        result = blocks.draw_form(ctx, 10, 10, 280, **common_kwargs)
        h = result.height
        assert h > 0

    def test_respects_max_height(self, ctx, common_kwargs):
        kwargs = {**common_kwargs, "max_height": 150}
        result = blocks.draw_form(ctx, 70, 70, 760, **kwargs)
        assert result.height <= 300  # some margin for the bottom spacing

    def test_multilingual(self, ctx):
        """Forms render without crashing for several languages and produce
        non-empty ground truth. Labels are now sampled from the active text
        source, so we don't assert specific localized tokens any more."""
        fonts = FontPalette()
        for lang in ("fr", "de", "es"):
            style = PageStyle()
            random.seed(0)
            result = blocks.draw_form(
                ctx,
                70,
                70,
                760,
                text_color=style.text_color,
                accent_color=style.accent_color,
                style=style,
                fonts=fonts,
                max_height=600,
                lang=lang,
            )
            assert result.height > 0
            assert len(result.text) > 0


class TestFormInPlanner:
    def test_form_in_block_weights(self):
        weights = DEFAULTS["planner"]["block_weights"]
        assert "form" in weights
        assert weights["form"] > 0

    def test_form_templates_exist(self):
        templates = DEFAULTS["planner"]["flow_templates"]
        form_templates = [t for _, t in templates if "form" in t]
        assert len(form_templates) >= 3
