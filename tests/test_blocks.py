"""Tests for pipeline.blocks: ensure every block renderer works,
returns a BlockResult, and doesn't crash."""

import random

import cairo
import gi
import pytest

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from docduck import blocks
from docduck.block_result import BlockResult
from docduck.diversity import PageStyle
from docduck.fonts import FontPalette

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unpack(result):
    """Normalize block return (BlockResult) into (height, text)."""
    assert isinstance(result, BlockResult), f"Block should return BlockResult, got {type(result)}"
    h, gt = result.height, result.text
    assert isinstance(h, (int, float)), f"Height should be numeric, got {type(h)}"
    assert isinstance(gt, str), f"Ground truth should be str, got {type(gt)}"
    return h, gt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
    return cairo.Context(surface)


@pytest.fixture
def style():
    random.seed(42)
    return PageStyle()


@pytest.fixture
def fonts():
    return FontPalette(serif="DejaVu Serif", sans="DejaVu Sans", mono="DejaVu Sans Mono")


@pytest.fixture
def common_kwargs(style, fonts):
    return dict(
        text_color=style.text_color,
        accent_color=style.accent_color,
        style=style,
        fonts=fonts,
        max_height=800,
    )


# ---------------------------------------------------------------------------
# Test each block type
# ---------------------------------------------------------------------------


class TestDrawHeading:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_heading(ctx, 70, 70, 760, **common_kwargs))
        assert h > 0
        assert len(gt) > 0

    def test_reasonable_height(self, ctx, common_kwargs):
        h, _ = _unpack(blocks.draw_heading(ctx, 70, 70, 760, **common_kwargs))
        assert h < 200

    def test_all_heading_styles(self, ctx, common_kwargs):
        for seed in range(20):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_heading(ctx, 70, 70, 760, **common_kwargs))
            assert h > 0
            assert len(gt) > 0


class TestDrawProse:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_prose(ctx, 70, 70, 760, **common_kwargs))
        assert h > 0
        assert len(gt) > 20  # should be multiple sentences

    def test_respects_max_height(self, ctx, common_kwargs):
        common_kwargs["max_height"] = 100
        h, _ = _unpack(blocks.draw_prose(ctx, 70, 70, 760, **common_kwargs))
        assert h < 300

    def test_without_style(self, ctx):
        h, gt = _unpack(blocks.draw_prose(ctx, 70, 70, 760, text_color=(0, 0, 0)))
        assert h > 0
        assert len(gt) > 0

    def test_ground_truth_has_paragraphs(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_prose(ctx, 70, 70, 760, **common_kwargs))
        # Should end with a period (sentence terminator)
        assert gt.rstrip().endswith(".")


class TestDrawTinyText:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_tiny_text(ctx, 70, 700, 760, **common_kwargs))
        assert h > 0
        assert "1." in gt  # footnotes are numbered

    def test_small_height(self, ctx, common_kwargs):
        h, _ = _unpack(blocks.draw_tiny_text(ctx, 70, 700, 760, **common_kwargs))
        assert h < 400


class TestDrawMulticolumn:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_multicolumn(ctx, 70, 70, 760, **common_kwargs))
        assert h > 0
        assert len(gt) > 50  # multi-paragraph text

    def test_respects_max_height(self, ctx, common_kwargs):
        common_kwargs["max_height"] = 200
        h, _ = _unpack(blocks.draw_multicolumn(ctx, 70, 70, 760, **common_kwargs))
        # Column height is capped at min(max_height, 400), but total block height
        # depends on text length and number of columns
        assert h <= 600


class TestDrawTable:
    def test_returns_height_and_html(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_table(ctx, 70, 70, 760, **common_kwargs))
        assert h > 0
        assert "<table>" in gt
        assert "</table>" in gt

    def test_ground_truth_has_headers_and_rows(self, ctx, common_kwargs):
        random.seed(42)
        h, gt = _unpack(blocks.draw_table(ctx, 70, 70, 760, **common_kwargs))
        assert gt.startswith("## "), f"Table caption should be a level-2 heading: {gt[:80]!r}"
        assert "<thead>" in gt
        assert "<th>" in gt
        assert "<tbody>" in gt
        assert "<td>" in gt

    def test_all_table_styles(self, ctx, common_kwargs):
        for seed in range(20):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_table(ctx, 70, 70, 760, **common_kwargs))
            assert h > 0
            assert len(gt) > 0


class TestDrawMath:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_math(ctx, 70, 300, 760, **common_kwargs))
        assert h > 0
        assert "$" in gt  # LaTeX equation
        assert "(" in gt  # equation label

    def test_reasonable_height(self, ctx, common_kwargs):
        h, _ = _unpack(blocks.draw_math(ctx, 70, 300, 760, **common_kwargs))
        assert h < 300

    def test_procedural_equations(self, ctx, common_kwargs):
        for seed in range(30):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_math(ctx, 70, 300, 760, **common_kwargs))
            assert h > 0, f"Equation failed to render at seed {seed}"
            assert "$$" in gt


class TestDrawCode:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_code(ctx, 70, 300, 760, **common_kwargs))
        assert h > 0
        assert "\n" in gt  # multi-line code

    def test_all_code_styles(self, ctx, common_kwargs):
        for seed in range(20):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_code(ctx, 70, 300, 760, **common_kwargs))
            assert h > 0
            assert len(gt) > 0


class TestDrawImagePlaceholder:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_image_placeholder(ctx, 70, 200, 760, **common_kwargs))
        assert h > 0
        assert "![image]" in gt
        assert "*" in gt  # italic-wrapped caption

    def test_all_pattern_types(self, ctx, common_kwargs):
        for seed in range(30):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_image_placeholder(ctx, 70, 200, 760, **common_kwargs))
            assert h > 0


class TestDrawRule:
    def test_returns_height_and_rule_marker(self, ctx, common_kwargs):
        h, gt = _unpack(blocks.draw_rule(ctx, 70, 400, 760, **common_kwargs))
        assert h > 0
        assert gt == "---"

    def test_fixed_small_height(self, ctx, common_kwargs):
        h, _ = _unpack(blocks.draw_rule(ctx, 70, 400, 760, **common_kwargs))
        assert h == 18

    def test_all_rule_styles(self, ctx, common_kwargs):
        for seed in range(30):
            random.seed(seed)
            h, gt = _unpack(blocks.draw_rule(ctx, 70, 400, 760, **common_kwargs))
            assert h == 18
            assert gt == "---"


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestBlockRegistry:
    def test_all_types_registered(self):
        expected = {
            "heading",
            "subheading",
            "prose",
            "list",
            "blockquote",
            "definition_list",
            "tiny_text",
            "multicolumn",
            "table",
            "math",
            "code",
            "image",
            "rule",
            "logo",
            "callout",
            "form",
        }
        assert set(blocks.BLOCK_TYPES.keys()) == expected

    def test_all_registered_functions_callable(self):
        for name, fn in blocks.BLOCK_TYPES.items():
            assert callable(fn), f"Block '{name}' is not callable"

    def test_all_blocks_return_blockresult(self, ctx, common_kwargs):
        random.seed(42)
        for name, fn in blocks.BLOCK_TYPES.items():
            result = fn(ctx, 70, 70, 760, **common_kwargs)
            h, gt = _unpack(result)
            assert h > 0, f"Block '{name}' returned height {h}"

    def test_narrow_width(self, ctx, common_kwargs):
        for name, fn in blocks.BLOCK_TYPES.items():
            random.seed(42)
            h, gt = _unpack(fn(ctx, 10, 10, 200, **common_kwargs))
            assert h > 0, f"Block '{name}' failed with narrow width"

    def test_ground_truth_types(self, ctx, common_kwargs):
        random.seed(42)
        for name, fn in blocks.BLOCK_TYPES.items():
            _, gt = _unpack(fn(ctx, 70, 70, 760, **common_kwargs))
            assert gt is not None, f"Block '{name}' returned None ground truth"
