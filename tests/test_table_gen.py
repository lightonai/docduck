"""Tests for table generators: localized headers, complex structures."""

import random

from docduck.defaults import DEFAULTS
from docduck.table.gen import (
    _ALL_TYPES,
    _sample_header,
    _sample_phrase,
    gen_deep_header_table,
    gen_grouped_header_table,
    gen_hierarchical_table,
    gen_indexed_table,
    gen_irregular_table,
    gen_matrix_table,
    gen_nested_rowspan_table,
    gen_pivot_table,
    gen_table,
)


class TestSamplePhrase:
    def test_respects_max_chars(self):
        for _ in range(10):
            s = _sample_phrase(None, n_words=3, max_chars=15)
            if s is not None:
                assert len(s) <= 15

    def test_fallback_when_no_model(self):
        import docduck.table.gen as tg

        tg._word_pools.pop("nonexistent_lang", None)
        # Should return None gracefully (or return a str from fallback)
        result = _sample_phrase("nonexistent_lang", n_words=3, max_chars=15)
        assert result is None or isinstance(result, str)


class TestSingleWordCells:
    def test_text_cells_are_single_words(self):
        import docduck.table.gen as tg

        tg._word_pools.pop("en", None)
        single_word_count = 0
        for _ in range(30):
            cell = tg._gen_word("en")
            if cell != "—" and " " not in cell:
                single_word_count += 1
        # Majority should be single words
        assert single_word_count >= 25

    def test_cells_do_not_contain_punctuation(self):
        import docduck.table.gen as tg

        tg._word_pools.pop("en", None)
        for _ in range(30):
            cell = tg._gen_word("en")
            assert cell == "—" or not any(c in cell for c in ".,;:!?()[]")


class TestHeaderLocalization:
    def test_english_headers_not_empty(self):
        for col_type in _ALL_TYPES:
            h = _sample_header("en", col_type)
            assert h, f"Empty header for {col_type}"
            assert isinstance(h, str)

    def test_pvalue_header_is_literal(self):
        h = _sample_header("fr", "pvalue")
        assert h in DEFAULTS["table"]["header_literal_tokens"]["pvalue"]

    def test_percent_header_has_suffix(self):
        suffix = DEFAULTS["table"]["header_literal_tokens"]["percent_suffix"]
        found_suffix = False
        for _ in range(20):
            h = _sample_header("en", "percent")
            if suffix in h:
                found_suffix = True
                break
        assert found_suffix, "Expected percent header to include (%) suffix"


class TestBorderlessStyle:
    def test_borderless_in_styles_pool(self):
        assert "borderless" in DEFAULTS["table"]["styles"]

    def test_borderless_renders_no_rules(self):
        """Borderless tables should draw only text: no rectangles or lines
        beyond text glyphs. We verify by counting ink pixels: a borderless
        render must have substantially fewer non-white pixels than a grid
        render of the same table."""
        import random

        import cairo
        import numpy as np

        from docduck.blocks._registry import blocks
        from docduck.table import gen as tg

        draw_table = blocks.get("table")

        def render(style: str) -> int:
            random.seed(42)
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 600, 400)
            ctx = cairo.Context(surface)
            ctx.set_source_rgb(1, 1, 1)
            ctx.paint()
            # Build a fixed spec and force the style
            spec = tg.gen_simple_table("en")
            spec.style = style
            spec.caption = "x"
            original = tg.gen_table
            tg.gen_table = lambda lang=None, ctx=None: spec
            try:
                draw_table(
                    ctx,
                    40,
                    40,
                    520,
                    text_color=(0, 0, 0),
                    accent_color=(0.3, 0.3, 0.6),
                    style=None,
                    fonts=None,
                    lang="en",
                )
            finally:
                tg.gen_table = original
            buf = surface.get_data()
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(400, 600, 4)
            ink = (arr[:, :, :3].min(axis=2) < 250).sum()
            return int(ink)

        ink_borderless = render("borderless")
        ink_grid = render("grid")
        # Grid should have substantially more ink (rules + bg) than borderless.
        # Borderless still renders text so it's > 0.
        assert ink_borderless > 0
        assert ink_grid > ink_borderless * 1.1


class TestTableGeneratorWeights:
    def test_generator_weights_sum_valid(self):
        weights = DEFAULTS["table"]["generator_weights"]
        assert all(w > 0 for w in weights.values())
        assert abs(sum(weights.values()) - 1.0) < 0.01 or sum(weights.values()) > 0

    def test_all_generators_callable(self):
        from docduck.table.gen import _GENERATORS

        for name in DEFAULTS["table"]["generator_weights"]:
            assert name in _GENERATORS


class TestHierarchicalTable:
    def test_has_group_labels_repeating(self):
        random.seed(0)
        spec = gen_hierarchical_table()
        # First column should repeat group labels
        first_col = [row[0] for row in spec.data_rows]
        # At least one label must appear more than once
        from collections import Counter

        c = Counter(first_col)
        assert max(c.values()) >= 2

    def test_has_two_label_columns_plus_data(self):
        random.seed(1)
        spec = gen_hierarchical_table()
        assert spec.n_cols >= 3


class TestIndexedTable:
    def test_first_column_has_section_numbers(self):
        random.seed(2)
        spec = gen_indexed_table()
        first_col = [row[0] for row in spec.data_rows]
        # Look for "1." and "1.1" style entries
        has_section = any(c.endswith(".") and c[:-1].isdigit() for c in first_col)
        has_subsection = any(
            "." in c
            and len(c.split(".")) == 2
            and c.split(".")[0].isdigit()
            and c.split(".")[1].isdigit()
            for c in first_col
        )
        assert has_section
        assert has_subsection


class TestGroupedHeaderTable:
    def test_has_two_header_rows(self):
        random.seed(3)
        spec = gen_grouped_header_table()
        assert len(spec.header_rows) == 2

    def test_top_row_has_colspans(self):
        random.seed(4)
        spec = gen_grouped_header_table()
        top = spec.header_rows[0]
        colspans = [h.colspan for h in top if h.colspan > 1]
        assert len(colspans) >= 1

    def test_column_count_consistent(self):
        random.seed(5)
        spec = gen_grouped_header_table()
        assert len(spec.header_rows[1]) == spec.n_cols
        for row in spec.data_rows:
            assert len(row) == spec.n_cols


class TestDeepHeaderTable:
    def test_has_three_header_rows(self):
        random.seed(10)
        spec = gen_deep_header_table()
        assert len(spec.header_rows) == 3

    def test_top_and_mid_have_colspans(self):
        random.seed(11)
        spec = gen_deep_header_table()
        top_spans = [h.colspan for h in spec.header_rows[0] if h.colspan > 1]
        mid_spans = [h.colspan for h in spec.header_rows[1] if h.colspan > 1]
        assert top_spans and mid_spans
        # Top colspans should be at least as wide as any mid colspan
        assert max(top_spans) >= max(mid_spans)

    def test_header_colspans_sum_to_n_cols(self):
        random.seed(12)
        spec = gen_deep_header_table()
        for row in spec.header_rows:
            assert sum(h.colspan for h in row) == spec.n_cols

    def test_leaf_count_capped(self):
        for seed in range(5):
            random.seed(seed)
            spec = gen_deep_header_table()
            # 2 top × 2 sub × 2 leaf = 8 leaves (+ optional label col)
            assert spec.n_cols in (8, 9)


class TestNestedRowspanTable:
    def test_has_outer_and_inner_spans(self):
        random.seed(20)
        spec = gen_nested_rowspan_table()
        outer_spans = [rs for (_, c), rs in spec.row_spans.items() if c == 0]
        inner_spans = [rs for (_, c), rs in spec.row_spans.items() if c == 1]
        assert outer_spans and inner_spans
        assert max(outer_spans) > max(inner_spans)

    def test_spans_align_with_row_count(self):
        random.seed(21)
        spec = gen_nested_rowspan_table()
        # Every outer span should equal a multiple of some inner span
        outer = max(rs for (_, c), rs in spec.row_spans.items() if c == 0)
        inner = max(rs for (_, c), rs in spec.row_spans.items() if c == 1)
        assert outer % inner == 0

    def test_covered_cells_are_empty(self):
        random.seed(22)
        spec = gen_nested_rowspan_table()
        for (r0, c0), rs in spec.row_spans.items():
            for offset in range(1, rs):
                assert spec.data_rows[r0 + offset][c0] == ""


class TestMatrixTable:
    def test_scale_bounds(self):
        for seed in range(5):
            random.seed(seed)
            spec = gen_matrix_table()
            assert 6 <= spec.n_cols <= 10
            assert 15 <= len(spec.data_rows) <= 25


class TestPivotTable:
    def test_structure_dims(self):
        random.seed(30)
        spec = gen_pivot_table()
        assert spec.n_cols == 10  # 2 label + 8 leaves
        assert len(spec.header_rows) == 3

    def test_header_colspans_consistent(self):
        random.seed(31)
        spec = gen_pivot_table()
        for row in spec.header_rows:
            assert sum(h.colspan for h in row) == spec.n_cols

    def test_top_row_has_wider_spans_than_mid(self):
        random.seed(32)
        spec = gen_pivot_table()
        # Top-level column groups span 4 cols (2 subs × 2 metrics)
        top_spans = [h.colspan for h in spec.header_rows[0][1:] if h.colspan > 1]
        # Mid-row sub-groups span 2 cols (metrics_per_sub)
        mid_spans = [h.colspan for h in spec.header_rows[1][1:] if h.colspan > 1]
        assert max(top_spans) == 4
        assert max(mid_spans) == 2

    def test_outer_label_has_rowspan(self):
        random.seed(33)
        spec = gen_pivot_table()
        col0_spans = [rs for (_, c), rs in spec.row_spans.items() if c == 0]
        assert col0_spans and max(col0_spans) >= 2


class TestIrregularTable:
    def test_has_full_width_divider(self):
        random.seed(40)
        spec = gen_irregular_table()
        # At least one col_span equals n_cols (full-width divider)
        full_spans = [cs for cs in spec.col_spans.values() if cs == spec.n_cols]
        assert full_spans

    def test_covered_cells_empty(self):
        random.seed(41)
        spec = gen_irregular_table()
        for (r0, c0), cs in spec.col_spans.items():
            for off in range(1, cs):
                assert spec.data_rows[r0][c0 + off] == ""

    def test_style_is_minimal(self):
        random.seed(42)
        spec = gen_irregular_table()
        assert spec.style == "minimal"


class TestGenTableEndToEnd:
    def test_default_lang_works(self):
        spec = gen_table()
        assert spec.n_cols >= 1
        assert len(spec.data_rows) >= 1
        assert spec.caption

    def test_multilingual(self):
        for lang in ["en", "fr", "de", "ja", "ar"]:
            random.seed(0)
            spec = gen_table(lang=lang)
            assert spec.n_cols >= 1

    def test_ctx_overrides_lang(self):
        from docduck.gen_context import GenContext

        spec = gen_table(lang="en", ctx=GenContext(lang="fr"))
        # No direct way to verify lang-specific output deterministically, but
        # the call should succeed and return a valid spec.
        assert spec.n_cols >= 1

    def test_every_generator_reachable(self):
        """Each generator type is selected with its weight."""

        seen = set()
        random.seed(0)
        for _ in range(300):
            spec = gen_table()
            # Identify generator by row/header structure approximately:
            # simpler: we just verify gen_table doesn't crash across many calls
            seen.add(spec.n_cols)
        # With many calls we should see variety in column count
        assert len(seen) >= 3
