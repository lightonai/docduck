"""Vertical-cursor block placer. Measures blocks on a scratch surface and only
composites them onto the page if they fully fit: overflowing blocks are
skipped (never clipped) so the ground truth always matches what's rendered.
"""

from typing import NamedTuple

import cairo

# PyGObject Pango/PangoCairo versions are pinned in docduck/__init__.py.
from .block_result import BlockResult


class PlacedBlock(NamedTuple):
    """Bounding box + content of a block actually placed on the page.

    Each block carries its own (x, width) so that when child LayoutManagers
    (one per column in multi_column / sidebar layouts) flush their
    placed_blocks into a parent lm, the column-correct x is preserved:
    the parent's margin_left can't be used as a fallback.
    """

    x: int
    y: int
    width: int
    height: int
    name: str
    text: str
    data: dict


class LayoutManager:
    def __init__(
        self,
        page_w,
        page_h,
        margin_top,
        margin_bottom,
        margin_left,
        margin_right,
        dpi_scale: float = 1.0,
    ):
        self.page_w = page_w
        self.page_h = page_h
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.content_w = page_w - margin_left - margin_right
        self.cursor_y = margin_top
        self.max_y = page_h - margin_bottom
        # Scratches render at this pixel density so compositing onto the
        # destination ctx is 1:1 (no resampling).
        self.dpi_scale = dpi_scale
        self.placed_blocks = []

    @property
    def remaining(self):
        return self.max_y - self.cursor_y

    def can_fit(self, height, min_useful=30):
        """Check if a block of given height fits, or at least min_useful pixels."""
        return self.remaining >= min(height, min_useful)

    def measure_block(self, draw_fn, **kwargs):
        """Render a block to a scratch surface.

        Passes max_height=self.remaining to the draw function so it can
        self-limit its content (e.g., fewer paragraphs, fewer table rows).

        If `draw_fn` has a `measure(content_w, **kwargs) -> float` attribute,
        it's used to pick a tighter scratch-surface height (saves allocation
        for deterministic-height blocks like `rule`, `logo`).

        Returns: (scratch_surface, BlockResult, error_string)
        """
        measure_fn = getattr(draw_fn, "measure", None)
        if measure_fn is not None:
            try:
                hint = float(measure_fn(self.content_w, **kwargs))
                scratch_h = max(int(hint) + 4, 80)
            except Exception as e:
                print(
                    f"  Warning: measure() failed for {draw_fn.__name__}: {e!r}"
                    "; falling back to full-surface scratch."
                )
                scratch_h = max(self.remaining, 400)
        else:
            scratch_h = max(self.remaining, 400)
        scratch = cairo.ImageSurface(
            cairo.FORMAT_ARGB32,
            int(self.page_w * self.dpi_scale),
            int(scratch_h * self.dpi_scale),
        )
        scratch_ctx = cairo.Context(scratch)
        if self.dpi_scale != 1.0:
            scratch_ctx.scale(self.dpi_scale, self.dpi_scale)

        # Transparent background so we can composite later
        scratch_ctx.set_operator(cairo.OPERATOR_CLEAR)
        scratch_ctx.paint()
        scratch_ctx.set_operator(cairo.OPERATOR_OVER)

        try:
            result = draw_fn(
                scratch_ctx,
                self.margin_left,
                0,
                self.content_w,
                max_height=self.remaining,
                **kwargs,
            )
        except Exception as e:
            return None, BlockResult(height=0), str(e)

        result.height = max(0, result.height)
        return scratch, result, None

    def place_block(self, page_ctx, scratch_surface, result: BlockResult, block_name="", spacing=0):
        """Composite a measured block onto the page at the current cursor.

        If the block doesn't fully fit, it is SKIPPED to avoid partial
        rendering that would mismatch the ground truth.
        """
        height = result.height
        if height <= 0:
            return 0

        if height > self.remaining:
            return 0

        # Drop the page_ctx scale so the scratch maps 1:1 onto the destination.
        page_ctx.save()
        page_ctx.identity_matrix()
        page_ctx.set_source_surface(scratch_surface, 0, self.cursor_y * self.dpi_scale)
        page_ctx.paint()
        page_ctx.restore()

        self.placed_blocks.append(
            PlacedBlock(
                x=self.margin_left,
                y=self.cursor_y,
                width=self.content_w,
                height=height,
                name=block_name,
                text=result.text,
                data=dict(result.data),
            )
        )
        self.cursor_y += height + spacing

        return height

    def measure_and_place(self, page_ctx, draw_fn, block_name="", spacing=0, **kwargs):
        """Convenience: measure, check fit, place. Returns height or 0 if skipped."""
        if self.remaining < 30:
            return 0

        scratch, result, err = self.measure_block(draw_fn, **kwargs)
        if err:
            print(f"  Warning: block '{block_name}' failed: {err}")
            return 0
        if result.height <= 0:
            return 0

        return self.place_block(page_ctx, scratch, result, block_name, spacing)

    def get_annotations(self):
        """Return bounding box annotations with text + structured data."""
        return [
            {
                "block_type": b.name,
                "text": b.text,
                "data": b.data,
                "bbox": {"x": b.x, "y": b.y, "width": b.width, "height": b.height},
            }
            for b in self.placed_blocks
        ]

    def get_full_page_text(self):
        """Return concatenated ground truth text for the entire page."""
        return "\n\n".join(b.text for b in self.placed_blocks if b.text)
