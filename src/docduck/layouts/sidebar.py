"""Sidebar layout: main column on the left + narrower aside column on the right.

Blocks with "sidebar-friendly" types (callout, blockquote, tiny_text, logo, image)
flow into the aside column; everything else stays in the main column. Each
column tracks its own vertical cursor, and a thin separator is drawn between.
"""

import random

from .. import blocks as blocks_pkg
from ..layout import LayoutManager
from ._base import LayoutStrategy, fill_remaining, register_layout

# Block types that prefer the narrower sidebar column.
_SIDEBAR_TYPES = {"callout", "blockquote", "tiny_text", "logo", "image"}


@register_layout("sidebar")
class SidebarLayout(LayoutStrategy):
    """Split content area into a main column + a narrower aside column.

    Routing: blocks whose type is in `sidebar_types` go to the aside column;
    all other blocks flow in the main column. When a column fills up, its
    blocks simply stop being placed (standard LayoutManager skip-on-overflow).
    """

    def __init__(
        self,
        main_fraction: float = 0.68,
        gutter: int = 24,
        sidebar_types: set[str] | None = None,
        sidebar_side: str = "right",
    ):
        self.main_fraction = main_fraction
        self.gutter = gutter
        self.sidebar_types = sidebar_types or _SIDEBAR_TYPES
        self.sidebar_side = sidebar_side  # "right" or "left"

    def render(
        self,
        ctx,
        lm,
        style,
        fonts,
        block_sequence,
        lang,
        seeds,
        spacing,
        page_w,
        page_h,
        margins,
        fill_with_prose: bool = True,
    ) -> list[str]:
        total_w = lm.content_w - self.gutter
        main_w = int(total_w * self.main_fraction)
        side_w = total_w - main_w

        if self.sidebar_side == "right":
            main_x = margins["left"]
            side_x = main_x + main_w + self.gutter
        else:
            side_x = margins["left"]
            main_x = side_x + side_w + self.gutter

        main_lm = LayoutManager(
            page_w,
            page_h,
            margins["top"],
            margins["bottom"],
            main_x,
            page_w - main_x - main_w,
            dpi_scale=lm.dpi_scale,
        )
        side_lm = LayoutManager(
            page_w,
            page_h,
            margins["top"],
            margins["bottom"],
            side_x,
            page_w - side_x - side_w,
            dpi_scale=lm.dpi_scale,
        )

        sep_x = (
            (main_x + main_w + self.gutter / 2)
            if self.sidebar_side == "right"
            else (side_x + side_w + self.gutter / 2)
        )
        ctx.set_source_rgba(*style.text_color, 0.12)
        ctx.set_line_width(0.5)
        ctx.move_to(sep_x, margins["top"])
        ctx.line_to(sep_x, page_h - margins["bottom"])
        ctx.stroke()

        placed: list[str] = []
        for bi, name in enumerate(block_sequence):
            target_lm = side_lm if name in self.sidebar_types else main_lm
            if target_lm.remaining < 30:
                # If the preferred column is full, fall through to the other.
                alt = main_lm if target_lm is side_lm else side_lm
                if alt.remaining < 30:
                    continue
                target_lm = alt

            draw_fn = blocks_pkg.BLOCK_TYPES.get(name)
            if draw_fn is None:
                continue

            prev_state = random.getstate()
            random.seed(seeds[bi])
            try:
                height = target_lm.measure_and_place(
                    ctx,
                    draw_fn,
                    block_name=name,
                    spacing=spacing,
                    text_color=style.text_color,
                    accent_color=style.accent_color,
                    style=style,
                    fonts=fonts,
                    lang=lang,
                )
            finally:
                random.setstate(prev_state)

            if height > 0:
                placed.append(name)

        fill_remaining(ctx, main_lm, style, fonts, lang, spacing, placed, enabled=fill_with_prose)
        if fill_with_prose:
            self._fill_sidebar(ctx, side_lm, style, fonts, lang, spacing, placed)

        lm.placed_blocks.extend(main_lm.placed_blocks)
        lm.placed_blocks.extend(side_lm.placed_blocks)
        return placed

    @staticmethod
    def _fill_sidebar(ctx, col_lm, style, fonts, lang, spacing, placed, max_fills=4):
        """Fill the sidebar column with tiny_text / blockquote / callout fillers."""
        candidates = ["tiny_text", "blockquote", "callout"]
        fills = 0
        while col_lm.remaining > 120 and fills < max_fills:
            name = random.choice(candidates)
            draw_fn = blocks_pkg.BLOCK_TYPES.get(name)
            if draw_fn is None:
                break
            prev_state = random.getstate()
            random.seed(random.randint(0, 2**31))
            try:
                height = col_lm.measure_and_place(
                    ctx,
                    draw_fn,
                    block_name=name,
                    spacing=spacing,
                    text_color=style.text_color,
                    accent_color=style.accent_color,
                    style=style,
                    fonts=fonts,
                    lang=lang,
                )
            finally:
                random.setstate(prev_state)
            if height <= 0:
                break
            placed.append(name)
            fills += 1
