"""Tests for brand palette support in PageStyle."""

from docduck.defaults import DEFAULTS, get_defaults
from docduck.diversity import PageStyle


class TestBrandPalettesDefined:
    def test_palettes_have_required_keys(self):
        for name, palette in DEFAULTS["brand_palettes"].items():
            for key in ("primary", "secondary", "accent", "text_on_primary"):
                assert key in palette, f"{name} missing {key}"
                color = palette[key]
                assert isinstance(color, tuple) and len(color) == 3
                for c in color:
                    assert 0 <= c <= 1

    def test_palette_primaries_are_distinct(self):
        primaries = {name: p["primary"] for name, p in DEFAULTS["brand_palettes"].items()}
        assert len(set(primaries.values())) == len(primaries)


class TestPageStyleBrandPalette:
    def test_explicit_palette_applied(self):
        style = PageStyle(brand_palette="tech_blue")
        assert style.brand_palette_name == "tech_blue"
        assert style.accent_color == DEFAULTS["brand_palettes"]["tech_blue"]["accent"]
        assert style.primary_color == DEFAULTS["brand_palettes"]["tech_blue"]["primary"]
        assert style.text_on_primary == DEFAULTS["brand_palettes"]["tech_blue"]["text_on_primary"]

    def test_invalid_palette_falls_back_to_random(self):
        style = PageStyle(brand_palette="does_not_exist")
        assert style.brand_palette is None
        assert style.accent_name in DEFAULTS["style"]["accents"]

    def test_style_without_palette_has_defaults(self):
        custom = get_defaults()
        custom["brand_palette_probability"] = 0.0
        style = PageStyle(defaults=custom)
        assert style.brand_palette is None
        assert style.primary_color == style.accent_color

    def test_palette_probability_always_uses_one(self):
        custom = get_defaults()
        custom["brand_palette_probability"] = 1.0
        for _ in range(5):
            style = PageStyle(defaults=custom)
            assert style.brand_palette is not None
            assert style.brand_palette_name in custom["brand_palettes"]
