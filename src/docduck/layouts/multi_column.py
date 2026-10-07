"""Multi-column layout: split page into equal columns with thin separators."""

import random

from .. import blocks as blocks_pkg
from ..layout import LayoutManager
from ._base import LayoutStrategy, fill_remaining, register_layout


@register_layout("multi_column")
class MultiColumnLayout(LayoutStrategy):
    """Split the content area into `n_columns` equal columns with a gutter."""

    def __init__(self, n_columns: int = 2, gutter: int = 20):
        self.n_columns = n_columns
        self.gutter = gutter

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
        col_w = (lm.content_w - self.gutter * (self.n_columns - 1)) // self.n_columns
        col_managers = []
        for ci in range(self.n_columns):
            col_x = margins["left"] + ci * (col_w + self.gutter)
            col_lm = LayoutManager(
                page_w,
                page_h,
                margins["top"],
                margins["bottom"],
                col_x,
                page_w - col_x - col_w,
                dpi_scale=lm.dpi_scale,
            )
            col_managers.append(col_lm)

        for ci in range(1, self.n_columns):
            sep_x = margins["left"] + ci * (col_w + self.gutter) - self.gutter / 2
            ctx.set_source_rgba(*style.text_color, 0.15)
            ctx.set_line_width(0.5)
            ctx.move_to(sep_x, margins["top"])
            ctx.line_to(sep_x, page_h - margins["bottom"])
            ctx.stroke()

        placed = []
        col_idx = 0
        for bi, name in enumerate(block_sequence):
            if col_idx >= self.n_columns:
                break
            cur_lm = col_managers[col_idx]
            if cur_lm.remaining < 30:
                col_idx += 1
                if col_idx >= self.n_columns:
                    break
                cur_lm = col_managers[col_idx]

            draw_fn = blocks_pkg.BLOCK_TYPES.get(name)
            if draw_fn is None:
                continue

            prev_state = random.getstate()
            random.seed(seeds[bi])
            try:
                height = cur_lm.measure_and_place(
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

        for col_lm in col_managers:
            fill_remaining(
                ctx, col_lm, style, fonts, lang, spacing, placed, enabled=fill_with_prose
            )

        for col_lm in col_managers:
            lm.placed_blocks.extend(col_lm.placed_blocks)

        return placed
