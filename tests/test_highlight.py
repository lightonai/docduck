"""Tests for the inline highlight markup (==text== in GT, span in render)."""

import random

import cairo

from docduck import fonts as fonts_mod
from docduck.blocks._helpers import pango_to_markdown
from docduck.blocks._registry import blocks
from docduck.defaults import DEFAULTS
from docduck.generators import text as tg


def test_pango_to_markdown_converts_span_to_double_equals():
    assert pango_to_markdown('<span bgcolor="yellow">3.5%</span>') == "==3.5%=="
    assert pango_to_markdown('<span background="#fff176">hit</span>') == "==hit=="


def test_pango_to_markdown_preserves_surrounding_text():
    md = pango_to_markdown('deposits totalled <span bgcolor="yellow">$12,540</span> today')
    assert md == "deposits totalled ==$12,540== today"


def test_pango_to_markdown_mixed_markup():
    md = pango_to_markdown(
        'See <b>Table 3</b> — row <span bgcolor="yellow">17</span> is outlier<sup>2</sup>.'
    )
    assert md == "See **Table 3** — row ==17== is outlier^2^."


def test_table_highlight_produces_gt_markers():
    """With highlight_prob forced high, the rendered table GT contains
    ==value== markers and the cell values survive the conversion."""
    prev = DEFAULTS["table"]["highlight_prob"]
    DEFAULTS["table"]["highlight_prob"] = 0.9
    try:
        random.seed(42)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        result = blocks.get("table")(
            ctx,
            40,
            60,
            820,
            text_color=(0, 0, 0),
            accent_color=(0.3, 0.3, 0.6),
            style=None,
            fonts=fonts_mod.FontPalette(),
            lang="en",
        )
    finally:
        DEFAULTS["table"]["highlight_prob"] = prev
    # At prob=0.9 we expect many highlighted cells → plenty of == markers.
    assert result.text.count("==") >= 4
    # No raw Pango span tags leak into GT.
    assert "<span" not in result.text


def test_prose_highlight_emits_double_equals():
    """Prose GT contains ==phrase== when the highlight feature is enabled
    and the random branch selector lands in the highlight band."""
    prev = DEFAULTS["prose"]["highlight_prob"]
    DEFAULTS["prose"]["highlight_prob"] = 0.5
    rnd = random.Random(0)
    calls = {"n": 0}

    def biased():
        calls["n"] += 1
        # Force the branch-selector call into the highlight band.
        return 0.01 if calls["n"] % 3 == 1 else rnd.random()

    orig = random.random
    random.random = biased
    try:
        random.seed(1)
        para = tg.gen_paragraph(min_sentences=3, max_sentences=3, lang="en", markup=True)
    finally:
        random.random = orig
        DEFAULTS["prose"]["highlight_prob"] = prev
    md = pango_to_markdown(para)
    assert "==" in md, f"expected highlight marker in markdown, got: {md!r}"


def test_prose_highlight_off_by_default():
    """With the default `highlight_prob=0`, prose never emits highlight spans."""
    assert DEFAULTS["prose"]["highlight_prob"] == 0.0
    random.seed(2)
    # Run enough paragraphs that a non-zero probability would almost
    # certainly produce at least one span.
    for _ in range(20):
        para = tg.gen_paragraph(min_sentences=4, max_sentences=6, lang="en", markup=True)
        assert "<span" not in para, f"unexpected highlight span: {para!r}"


def test_table_highlight_off_by_default():
    """Default table rendering produces no highlight markers in the GT."""
    assert DEFAULTS["table"]["highlight_prob"] == 0.0
    random.seed(3)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 900, 1200)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    result = blocks.get("table")(
        ctx,
        40,
        60,
        820,
        text_color=(0, 0, 0),
        accent_color=(0.3, 0.3, 0.6),
        style=None,
        fonts=fonts_mod.FontPalette(),
        lang="en",
    )
    assert "==" not in result.text
    assert "<span" not in result.text
