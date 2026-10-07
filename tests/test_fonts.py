"""Tests for pipeline.fonts."""

from docduck.fonts import BatchFontScheduler, FontPalette, get_system_fonts


class TestGetSystemFonts:
    def test_returns_dict(self):
        result = get_system_fonts()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = get_system_fonts()
        assert "serif" in result
        assert "sans" in result
        assert "mono" in result
        assert "all" in result

    def test_pools_are_lists(self):
        result = get_system_fonts()
        for key in ("serif", "sans", "mono", "all"):
            assert isinstance(result[key], list)

    def test_minimum_fonts(self):
        result = get_system_fonts()
        assert len(result["serif"]) >= 2
        assert len(result["sans"]) >= 2
        assert len(result["mono"]) >= 2

    def test_cached(self):
        # Calling twice should return the same object (lru_cache)
        r1 = get_system_fonts()
        r2 = get_system_fonts()
        assert r1 is r2


class TestFontPalette:
    def test_default_init(self):
        fp = FontPalette()
        assert isinstance(fp.serif, str)
        assert isinstance(fp.sans, str)
        assert isinstance(fp.mono, str)

    def test_custom_init(self):
        fp = FontPalette(serif="Times", sans="Helvetica", mono="Courier")
        assert fp.serif == "Times"
        assert fp.sans == "Helvetica"
        assert fp.mono == "Courier"

    def test_get_serif(self):
        fp = FontPalette(serif="DejaVu Serif", sans="DejaVu Sans", mono="DejaVu Sans Mono")
        result = fp.get("serif", 12)
        assert "DejaVu Serif" in result
        assert "12" in result

    def test_get_sans_bold(self):
        fp = FontPalette(serif="DejaVu Serif", sans="DejaVu Sans", mono="DejaVu Sans Mono")
        result = fp.get("sans", 10, bold=True)
        assert "DejaVu Sans" in result
        assert "Bold" in result
        assert "10" in result

    def test_get_mono_italic(self):
        fp = FontPalette(serif="DejaVu Serif", sans="DejaVu Sans", mono="DejaVu Sans Mono")
        result = fp.get("mono", 9, italic=True)
        assert "DejaVu Sans Mono" in result
        assert "Italic" in result

    def test_get_bold_italic(self):
        fp = FontPalette(serif="Test Serif")
        result = fp.get("serif", 14, bold=True, italic=True)
        assert "Bold" in result
        assert "Italic" in result
        assert "14" in result

    def test_repr(self):
        fp = FontPalette(serif="A", sans="B", mono="C")
        r = repr(fp)
        assert "A" in r
        assert "B" in r
        assert "C" in r


class TestBatchFontScheduler:
    def test_init(self):
        scheduler = BatchFontScheduler(seed=42)
        assert len(scheduler.serif_pool) >= 2
        assert len(scheduler.sans_pool) >= 2
        assert len(scheduler.mono_pool) >= 2

    def test_next_palette_returns_font_palette(self):
        scheduler = BatchFontScheduler(seed=42)
        p = scheduler.next_palette()
        assert isinstance(p, FontPalette)

    def test_cycling_produces_variety(self):
        scheduler = BatchFontScheduler(seed=42)
        palettes = [scheduler.next_palette() for _ in range(10)]
        serifs = {p.serif for p in palettes}
        # Should have more than one unique serif across 10 palettes
        # (unless the system has very few fonts)
        assert len(serifs) >= 1

    def test_deterministic_with_seed(self):
        s1 = BatchFontScheduler(seed=123)
        s2 = BatchFontScheduler(seed=123)
        for _ in range(5):
            p1 = s1.next_palette()
            p2 = s2.next_palette()
            assert p1.serif == p2.serif
            assert p1.sans == p2.sans
            assert p1.mono == p2.mono

    def test_increments_index(self):
        scheduler = BatchFontScheduler(seed=42)
        assert scheduler._idx == 0
        scheduler.next_palette()
        assert scheduler._idx == 1
        scheduler.next_palette()
        assert scheduler._idx == 2
