"""Sanity tests for the scan-artifact presets."""

import cairo
import numpy as np
import pytest

from docduck.artifacts import _PRESETS, apply_artifacts


def _blank(w: int = 300, h: int = 400) -> cairo.ImageSurface:
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(s)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    # Draw one solid dark rectangle so pixel-difference measurements have
    # content to chew on (a pure white page would confound some effects).
    ctx.set_source_rgb(0.1, 0.1, 0.1)
    ctx.rectangle(30, 30, 240, 120)
    ctx.fill()
    return s


def _as_array(s: cairo.ImageSurface) -> np.ndarray:
    w, h = s.get_width(), s.get_height()
    buf = s.get_data()
    return np.frombuffer(buf, dtype=np.uint8).reshape(h, s.get_stride() // 4, 4)[:, :w, :3].copy()


def test_all_presets_callable():
    src = _blank()
    for preset in _PRESETS:
        out = apply_artifacts(src, intensity=1.0, seed=0, preset=preset)
        assert (out.get_width(), out.get_height()) == (src.get_width(), src.get_height())


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="unknown preset"):
        apply_artifacts(_blank(), preset="nope")


def test_determinism_via_seed():
    """Same seed + same input = byte-identical output (reproducible corpus)."""
    src = _blank()
    a = _as_array(apply_artifacts(src, intensity=1.0, seed=7, preset="fax"))
    b = _as_array(apply_artifacts(src, intensity=1.0, seed=7, preset="fax"))
    assert np.array_equal(a, b)


def test_preset_strength_orders_correctly():
    """Harder presets must perturb pixels more than milder ones."""
    src = _blank()
    base = _as_array(src)
    diffs = {}
    for preset in ("mild", "photocopy", "fax", "extreme"):
        out = _as_array(apply_artifacts(src, intensity=1.0, seed=0, preset=preset))
        diffs[preset] = np.abs(out.astype(int) - base.astype(int)).mean()
    assert diffs["mild"] < diffs["photocopy"] < diffs["fax"] < diffs["extreme"]
