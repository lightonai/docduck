"""Layout strategy base + registry.

A layout strategy owns how blocks are dispatched across the page area (flow,
parallel columns, sidebar, etc.). `render()` places each block and returns
the list of block names that landed (overflow-skipped blocks are omitted).
"""

import random
from abc import ABC, abstractmethod

from ..registry import Registry

layouts: Registry = Registry("layout")


def fill_remaining(
    ctx,
    column_lm,
    style,
    fonts,
    lang,
    spacing,
    placed: list[str],
    min_remaining: int = 150,
    max_fills: int = 6,
    enabled: bool = True,
):
    """Top up `column_lm` with prose blocks so columns don't bottom out.

    Set `enabled=False` when the caller passed an explicit `blocks` list:
    the user asked for exactly those block types, so synthesizing extra
    prose would contradict that intent.
    """
    if not enabled:
        return
    from .. import blocks as blocks_pkg

    draw_fn = blocks_pkg.BLOCK_TYPES.get("prose")
    if draw_fn is None:
        return

    fills = 0
    while column_lm.remaining > min_remaining and fills < max_fills:
        prev_state = random.getstate()
        random.seed(random.randint(0, 2**31))
        try:
            height = column_lm.measure_and_place(
                ctx,
                draw_fn,
                block_name="prose",
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
        placed.append("prose")
        fills += 1


class LayoutStrategy(ABC):
    @abstractmethod
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
        """Place blocks and return the sequence of placed block names.

        `fill_with_prose=False` disables the trailing-prose top-up; the
        composer sets this when the user passed an explicit `blocks` list.
        """


def register_layout(name: str, weight: float = 1.0):
    return layouts.register(name, weight=weight)
