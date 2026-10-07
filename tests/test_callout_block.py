"""Tests for the callout/info-box block renderer."""

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
        "max_height": 400,
    }


class TestDrawCallout:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        result = blocks.draw_callout(ctx, 70, 70, 760, **common_kwargs)
        h, gt = result.height, result.text
        assert h > 0
        assert len(gt) > 10

    def test_ground_truth_has_bold_label_and_colon(self, ctx, common_kwargs):
        result = blocks.draw_callout(ctx, 70, 70, 760, **common_kwargs)
        gt = result.text
        assert gt.startswith("**")
        # "**Label:** body text"
        assert ":**" in gt

    def test_label_is_sampled_short_phrase(self, ctx, common_kwargs):
        """Labels are sampled from the active TextSource so they vary per
        render. Two callouts on different seeds rarely share a label."""
        seen = set()
        for seed in range(20):
            random.seed(seed)
            result = blocks.draw_callout(ctx, 70, 70, 760, **common_kwargs)
            label = result.text.split(":")[0].strip("*").strip()
            assert label, "empty callout label"
            # Label was capped at ~label_max_words words
            assert len(label.split()) <= DEFAULTS["callout"].get("label_max_words", 2) + 1
            seen.add(label)
        # Across 20 random seeds we expect more than just a handful of labels.
        assert len(seen) >= 5, f"labels feel templated, only saw {seen}"

    def test_narrow_width_handled(self, ctx, common_kwargs):
        result = blocks.draw_callout(ctx, 10, 10, 250, **common_kwargs)
        assert result.height > 0

    def test_all_kinds_render(self, ctx, common_kwargs):
        """Each callout kind (note/warning/danger/tip/info) renders with its
        configured background and border colors, regardless of the sampled
        label. The data dict surfaces the kind name."""
        for kind_name in DEFAULTS["callout"]["kinds"]:
            orig = random.choice

            def make_choice(target):
                def choice(seq):
                    if isinstance(seq, list) and target in seq:
                        return target
                    return orig(seq)

                return choice

            try:
                random.choice = make_choice(kind_name)
                result = blocks.draw_callout(ctx, 70, 70, 760, **common_kwargs)
                assert result.height > 0
                assert result.data["kind"] == kind_name
            finally:
                random.choice = orig
