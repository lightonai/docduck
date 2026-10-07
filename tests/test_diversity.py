"""Tests for docduck.diversity."""

import random

from docduck.defaults import DEFAULTS
from docduck.diversity import BatchDiversityTracker, LayoutPlanner, PageStyle

STYLE = DEFAULTS["style"]


class TestPageStyle:
    def test_init(self):
        style = PageStyle()
        assert style.paper_name in STYLE["papers"]
        assert style.text_name in STYLE["text_colors"]
        # accent may come from palette or accent pool
        assert (
            style.accent_name in STYLE["accents"] or style.accent_name in DEFAULTS["brand_palettes"]
        )
        assert style.margin_name in STYLE["margin_presets"]

    def test_paper_color_matches_name(self):
        style = PageStyle()
        assert style.paper_color == STYLE["papers"][style.paper_name]

    def test_text_color_matches_name(self):
        style = PageStyle()
        assert style.text_color == STYLE["text_colors"][style.text_name]

    def test_accent_color_is_tuple(self):
        style = PageStyle()
        assert isinstance(style.accent_color, tuple)
        assert len(style.accent_color) == 3

    def test_margins_dict(self):
        style = PageStyle()
        assert "top" in style.margins
        assert "bottom" in style.margins
        assert "left" in style.margins
        assert "right" in style.margins
        for v in style.margins.values():
            assert isinstance(v, (int, float))
            assert v > 0

    def test_body_size_positive(self):
        for _ in range(20):
            style = PageStyle()
            assert style.body_size > 0
            assert style.heading_size > style.body_size
            assert style.tiny_size < style.body_size
            assert style.tiny_size >= 4

    def test_line_spacing_range(self):
        for _ in range(20):
            style = PageStyle()
            assert 1.5 <= style.line_spacing <= 4.0

    def test_boolean_flags(self):
        style = PageStyle()
        assert isinstance(style.justify, bool)
        assert isinstance(style.has_header, bool)
        assert isinstance(style.has_page_number, bool)
        assert isinstance(style.has_page_border, bool)
        assert isinstance(style.has_edge_shadow, bool)

    def test_signature_is_hashable(self):
        style = PageStyle()
        sig = style.signature()
        assert isinstance(sig, tuple)
        assert len(sig) == 4
        hash(sig)
        {sig: True}

    def test_variety_across_instances(self):
        random.seed(42)
        styles = [PageStyle() for _ in range(30)]
        papers = {s.paper_name for s in styles}
        accents = {s.accent_name for s in styles}
        assert len(papers) >= 3, f"Only {len(papers)} paper colors in 30 instances"
        assert len(accents) >= 3, f"Only {len(accents)} accents in 30 instances"


class TestLayoutPlanner:
    def test_init_defaults(self):
        lp = LayoutPlanner()
        assert lp.min_blocks == 3
        assert lp.max_blocks == 7
        assert lp.min_distinct == 3

    def test_plan_returns_list(self):
        lp = LayoutPlanner()
        result = lp.plan()
        assert isinstance(result, list)
        assert len(result) >= 2  # at least heading + 1 block

    def test_starts_with_heading(self):
        lp = LayoutPlanner()
        for _ in range(20):
            result = lp.plan()
            assert result[0] == "heading"

    def test_no_back_to_back_repeats_except_allowed(self):
        allowed_repeats = {"prose", "form"}
        lp = LayoutPlanner()
        for _ in range(50):
            result = lp.plan()
            for i in range(1, len(result)):
                if result[i] == result[i - 1]:
                    assert result[i] in allowed_repeats, (
                        f"Back-to-back repeat of '{result[i]}' at positions {i - 1},{i}"
                    )

    def test_tiny_text_at_end(self):
        lp = LayoutPlanner()
        for _ in range(50):
            result = lp.plan()
            if "tiny_text" in result:
                assert result[-1] == "tiny_text"

    def test_valid_block_types(self):
        lp = LayoutPlanner()
        valid = set(DEFAULTS["planner"]["block_weights"].keys()) | {"heading", "tiny_text"}
        for _ in range(30):
            result = lp.plan()
            for block in result:
                assert block in valid, f"Unknown block type: {block}"

    def test_min_distinct_types(self):
        lp = LayoutPlanner(min_blocks=5, max_blocks=7, min_distinct=3)
        # Run many times: this is probabilistic but should almost always pass
        successes = 0
        for _ in range(50):
            result = lp.plan()
            distinct = len(set(result))
            if distinct >= 3:
                successes += 1
        # Allow some slack for randomness
        assert successes >= 40, f"Only {successes}/50 plans had >= 3 distinct types"

    def test_custom_bounds(self):
        lp = LayoutPlanner(min_blocks=2, max_blocks=3, min_distinct=2)
        for _ in range(20):
            result = lp.plan()
            # heading + 2-3 blocks, possibly + tiny_text
            assert len(result) >= 3  # heading + at least 2


class TestBatchDiversityTracker:
    def test_init(self):
        tracker = BatchDiversityTracker()
        assert tracker.total_pages == 0
        assert len(tracker.layout_hashes) == 0

    def test_record_page(self):
        tracker = BatchDiversityTracker()
        style = PageStyle()
        tracker.record_page(style, ["heading", "prose", "table"])
        assert tracker.total_pages == 1
        assert tracker.block_type_counts["heading"] == 1
        assert tracker.block_type_counts["prose"] == 1
        assert tracker.block_type_counts["table"] == 1

    def test_record_multiple_pages(self):
        tracker = BatchDiversityTracker()
        for _ in range(5):
            style = PageStyle()
            tracker.record_page(style, ["heading", "prose"])
        assert tracker.total_pages == 5
        assert tracker.block_type_counts["heading"] == 5
        assert tracker.block_type_counts["prose"] == 5

    def test_unique_layouts_tracked(self):
        tracker = BatchDiversityTracker()
        style = PageStyle()
        tracker.record_page(style, ["heading", "prose", "table"])
        tracker.record_page(style, ["heading", "code", "math"])
        tracker.record_page(style, ["heading", "prose", "table"])  # duplicate
        assert len(tracker.layout_hashes) == 2

    def test_suggest_overrides_empty_for_few_pages(self):
        tracker = BatchDiversityTracker()
        result = tracker.suggest_style_overrides()
        assert isinstance(result, dict)
        # With 0 pages, no strong overrides expected
        assert len(result) == 0  # needs >= 2 pages

    def test_suggest_overrides_after_pages(self):
        tracker = BatchDiversityTracker()
        for _ in range(5):
            style = PageStyle()
            # Force same paper/accent to trigger override suggestions
            style.paper_name = "cream"
            style.accent_name = "red"
            tracker.record_page(style, ["heading", "prose"])

        result = tracker.suggest_style_overrides()
        # Should suggest unused papers/accents
        if "preferred_paper" in result:
            assert result["preferred_paper"] != "cream"
        if "preferred_accent" in result:
            assert result["preferred_accent"] != "red"

    def test_report_structure(self):
        tracker = BatchDiversityTracker()
        style = PageStyle()
        tracker.record_page(style, ["heading", "prose"])

        report = tracker.report()
        assert "total_pages" in report
        assert "unique_layouts" in report
        assert "style_distribution" in report
        assert "block_type_counts" in report
        assert report["total_pages"] == 1
        assert report["unique_layouts"] == 1

    def test_report_json_serializable(self):
        import json

        tracker = BatchDiversityTracker()
        for _ in range(5):
            style = PageStyle()
            tracker.record_page(style, ["heading", "prose", "table"])
        report = tracker.report()
        # This should not raise
        json.dumps(report)
