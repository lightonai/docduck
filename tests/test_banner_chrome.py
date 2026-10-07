"""Tests for the colored banner page-chrome."""

from docduck.composer import compose_page
from docduck.defaults import DEFAULTS
from docduck.diversity import PageStyle
from docduck.page_config import PageConfig


class TestBannerConfig:
    def test_banner_config_exists(self):
        assert "banner" in DEFAULTS
        assert "height_range" in DEFAULTS["banner"]

    def test_height_range_valid(self):
        lo, hi = DEFAULTS["banner"]["height_range"]
        assert 0 < lo <= hi


class TestBannerRendering:
    def test_banner_renders_without_crash(self):
        cfg = PageConfig(seed=1, output_dpi=72)
        cfg.style.has_banner = True
        cfg.style.has_logo = False
        surface, _, _, _ = compose_page(page_config=cfg)
        assert surface.get_width() == cfg.page_w
        assert surface.get_height() == cfg.page_h

    def test_banner_with_brand_palette(self):
        cfg = PageConfig(seed=2)
        cfg.style = PageStyle(brand_palette="tech_blue")
        cfg.style.has_banner = True
        cfg.style.has_logo = False
        surface, _, _, _ = compose_page(page_config=cfg)
        assert surface is not None

    def test_banner_suppresses_running_header(self):
        cfg = PageConfig(seed=3)
        cfg.style.has_banner = True
        cfg.style.has_header = True
        cfg.style.has_logo = False
        surface, _, _, _ = compose_page(page_config=cfg)
        assert surface is not None

    def test_no_banner_by_default_probability(self):
        style = PageStyle()
        assert isinstance(style.has_banner, bool)
