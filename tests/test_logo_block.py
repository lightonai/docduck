"""Tests for the logo block renderer."""

import random

import cairo
import gi
import pytest

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from docduck import blocks
from docduck.composer import compose_page
from docduck.defaults import DEFAULTS
from docduck.diversity import PageStyle
from docduck.fonts import FontPalette
from docduck.page_config import PageConfig


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


class TestDrawLogo:
    def test_returns_height_and_text(self, ctx, common_kwargs):
        result = blocks.draw_logo(ctx, 70, 70, 760, **common_kwargs)
        h, gt = result.height, result.text
        assert h > 0
        assert len(gt) > 0

    def test_ground_truth_is_bold_company_name(self, ctx, common_kwargs):
        random.seed(0)
        result = blocks.draw_logo(ctx, 70, 70, 760, **common_kwargs)
        gt = result.text
        assert gt.startswith("**")
        assert gt.endswith("**")
        # Company name should use words from the configured pool
        name = gt.strip("*")
        first_word = name.split()[0]
        assert first_word in DEFAULTS["logo"]["company_words"]

    def test_renders_all_styles_without_crash(self, ctx, common_kwargs):
        # Drive every style and shape by controlling the random seed
        for seed in range(30):
            random.seed(seed)
            result = blocks.draw_logo(ctx, 70, 70, 760, **common_kwargs)
            assert result.height > 0


class TestLogoInjection:
    def test_logo_injected_when_has_logo_flag(self):
        cfg = PageConfig(seed=42)
        cfg.style.has_logo = True
        cfg.style.has_banner = False
        _, _, placed, _ = compose_page(page_config=cfg)
        assert "logo" in placed

    def test_logo_not_injected_when_flag_off(self):
        cfg = PageConfig(seed=42)
        cfg.style.has_logo = False
        cfg.style.has_banner = False
        _, _, placed, _ = compose_page(page_config=cfg)
        # Logo should only appear if random planner picked it by other means
        # (planner doesn't include 'logo' in block_weights, so it shouldn't)
        assert "logo" not in placed

    def test_logo_is_first_block_when_injected(self):
        cfg = PageConfig(seed=7)
        cfg.style.has_logo = True
        cfg.style.has_banner = False
        _, _, placed, _ = compose_page(page_config=cfg)
        if "logo" in placed:
            assert placed[0] == "logo"
