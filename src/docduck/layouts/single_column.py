"""Single-column layout: flow blocks top-to-bottom within page margins."""

import random

from .. import blocks as blocks_pkg
from ._base import LayoutStrategy, fill_remaining, register_layout


@register_layout("single_column")
class SingleColumnLayout(LayoutStrategy):
    """Place blocks sequentially in a single column under page margins."""

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
        placed = []
        for bi, name in enumerate(block_sequence):
            if lm.remaining < 30:
                break
            draw_fn = blocks_pkg.BLOCK_TYPES.get(name)
            if draw_fn is None:
                continue

            prev_state = random.getstate()
            random.seed(seeds[bi])
            try:
                height = lm.measure_and_place(
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

        fill_remaining(ctx, lm, style, fonts, lang, spacing, placed, enabled=fill_with_prose)
        return placed
