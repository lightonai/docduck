"""Tests for pipeline.layout."""

import cairo

from docduck.block_result import BlockResult
from docduck.layout import LayoutManager


def make_layout_manager(page_w=900, page_h=1200, margin=70):
    return LayoutManager(page_w, page_h, margin, margin, margin, margin)


def make_result(height, text="", data=None):
    return BlockResult(height=height, text=text, data=data or {})


class TestLayoutManagerInit:
    def test_basic_init(self):
        lm = LayoutManager(900, 1200, 70, 70, 70, 70)
        assert lm.page_w == 900
        assert lm.page_h == 1200
        assert lm.content_w == 900 - 70 - 70
        assert lm.cursor_y == 70
        assert lm.max_y == 1200 - 70

    def test_asymmetric_margins(self):
        lm = LayoutManager(800, 1000, 50, 80, 100, 60)
        assert lm.content_w == 800 - 100 - 60
        assert lm.cursor_y == 50
        assert lm.max_y == 1000 - 80

    def test_initial_placed_blocks_empty(self):
        lm = make_layout_manager()
        assert lm.placed_blocks == []


class TestRemaining:
    def test_initial_remaining(self):
        lm = LayoutManager(900, 1200, 70, 70, 70, 70)
        assert lm.remaining == 1200 - 70 - 70

    def test_remaining_after_cursor_advance(self):
        lm = make_layout_manager()
        initial = lm.remaining
        lm.cursor_y += 100
        assert lm.remaining == initial - 100


class TestCanFit:
    def test_fits_when_enough_space(self):
        lm = make_layout_manager()
        assert lm.can_fit(100)

    def test_does_not_fit_when_full(self):
        lm = make_layout_manager()
        lm.cursor_y = lm.max_y
        assert not lm.can_fit(100)

    def test_fits_partial_with_min_useful(self):
        lm = make_layout_manager()
        lm.cursor_y = lm.max_y - 50
        assert lm.can_fit(200, min_useful=30)

    def test_does_not_fit_below_min_useful(self):
        lm = make_layout_manager()
        lm.cursor_y = lm.max_y - 10
        assert not lm.can_fit(200, min_useful=30)


class TestMeasureBlock:
    def test_measure_block_result(self):
        lm = make_layout_manager()

        def draw(ctx, x, y, width, **kw):
            return BlockResult(height=50.0, text="test text")

        scratch, result, err = lm.measure_block(draw)
        assert scratch is not None
        assert result.height == 50.0
        assert result.text == "test text"
        assert err is None

    def test_measure_does_not_advance_cursor(self):
        lm = make_layout_manager()
        initial_y = lm.cursor_y

        def draw(ctx, x, y, width, **kw):
            return BlockResult(height=50.0, text="text")

        lm.measure_block(draw)
        assert lm.cursor_y == initial_y

    def test_measure_failing_block(self):
        lm = make_layout_manager()

        def draw(ctx, x, y, width, **kw):
            raise ValueError("test error")

        scratch, result, err = lm.measure_block(draw)
        assert scratch is None
        assert result.height == 0
        assert "test error" in err

    def test_measure_passes_kwargs(self):
        lm = make_layout_manager()
        received = {}

        def draw(ctx, x, y, width, **kw):
            received.update(kw)
            return BlockResult(height=30.0, text="captured")

        lm.measure_block(draw, text_color=(1, 0, 0), extra="value")
        assert received["text_color"] == (1, 0, 0)
        assert received["extra"] == "value"


class TestPlaceBlock:
    def test_place_advances_cursor(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        initial_y = lm.cursor_y
        lm.place_block(ctx, scratch, make_result(80), block_name="test")
        assert lm.cursor_y == initial_y + 80

    def test_place_with_spacing(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        initial_y = lm.cursor_y
        lm.place_block(ctx, scratch, make_result(80), spacing=10)
        assert lm.cursor_y == initial_y + 80 + 10

    def test_place_records_block(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        lm.place_block(ctx, scratch, make_result(80, "hello world"), block_name="prose")
        assert len(lm.placed_blocks) == 1
        assert lm.placed_blocks[0].name == "prose"
        assert lm.placed_blocks[0].text == "hello world"

    def test_place_zero_height_block(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        initial_y = lm.cursor_y
        result = lm.place_block(ctx, scratch, make_result(0), block_name="empty")
        assert result == 0
        assert lm.cursor_y == initial_y

    def test_place_skips_when_doesnt_fit(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 2000)

        lm.cursor_y = lm.max_y - 50
        actual = lm.place_block(
            ctx, scratch, make_result(200, "should not appear"), block_name="overflow"
        )
        assert actual == 0
        assert len(lm.placed_blocks) == 0

    def test_place_fits_exactly(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        remaining = lm.remaining
        actual = lm.place_block(
            ctx, scratch, make_result(remaining, "fits exactly"), block_name="exact"
        )
        assert actual == remaining
        assert lm.placed_blocks[-1].text == "fits exactly"


class TestMeasureAndPlace:
    def test_measure_and_place_happy_path(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)

        def draw(ctx, x, y, width, **kw):
            return BlockResult(height=60.0, text="placed text")

        initial_y = lm.cursor_y
        result = lm.measure_and_place(ctx, draw, block_name="test")
        assert result > 0
        assert lm.cursor_y > initial_y
        assert lm.placed_blocks[-1].text == "placed text"

    def test_measure_and_place_skips_when_full(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)

        lm.cursor_y = lm.max_y - 10

        def draw(ctx, x, y, width, **kw):
            return BlockResult(height=60.0, text="text")

        result = lm.measure_and_place(ctx, draw, block_name="test")
        assert result == 0

    def test_measure_and_place_handles_error(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)

        def draw(ctx, x, y, width, **kw):
            raise RuntimeError("draw failed")

        result = lm.measure_and_place(ctx, draw, block_name="bad")
        assert result == 0


class TestGetAnnotations:
    def test_empty_annotations(self):
        lm = make_layout_manager()
        assert lm.get_annotations() == []

    def test_annotations_structure(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        lm.place_block(ctx, scratch, make_result(80, "Title"), block_name="heading")
        lm.place_block(ctx, scratch, make_result(120, "Body text"), block_name="prose")

        annotations = lm.get_annotations()
        assert len(annotations) == 2

        a = annotations[0]
        assert a["block_type"] == "heading"
        assert a["text"] == "Title"
        assert a["data"] == {}
        assert "bbox" in a
        assert "x" in a["bbox"]
        assert "y" in a["bbox"]
        assert "width" in a["bbox"]
        assert "height" in a["bbox"]

    def test_annotations_preserve_data(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        lm.place_block(
            ctx,
            scratch,
            make_result(80, "# Title", data={"level": 1, "title": "Title"}),
            block_name="heading",
        )
        assert lm.get_annotations()[0]["data"] == {"level": 1, "title": "Title"}

    def test_full_page_text(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        lm.place_block(ctx, scratch, make_result(80, "Title"), block_name="heading")
        lm.place_block(ctx, scratch, make_result(80, "---"), block_name="rule")
        lm.place_block(ctx, scratch, make_result(120, "Body text here."), block_name="prose")

        full = lm.get_full_page_text()
        assert "Title" in full
        assert "---" in full
        assert "Body text here." in full

    def test_full_page_text_empty_when_no_blocks(self):
        lm = make_layout_manager()
        assert lm.get_full_page_text() == ""

    def test_annotations_no_overlap(self):
        lm = make_layout_manager()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 100)

        lm.place_block(ctx, scratch, make_result(80), block_name="heading", spacing=5)
        lm.place_block(ctx, scratch, make_result(120), block_name="prose", spacing=5)
        lm.place_block(ctx, scratch, make_result(60), block_name="code", spacing=5)

        annotations = lm.get_annotations()
        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                a = annotations[i]["bbox"]
                b = annotations[j]["bbox"]
                a_bottom = a["y"] + a["height"]
                b_top = b["y"]
                assert a_bottom <= b_top, (
                    f"Block {i} ({annotations[i]['block_type']}) bottom={a_bottom} "
                    f"overlaps block {j} ({annotations[j]['block_type']}) top={b_top}"
                )
