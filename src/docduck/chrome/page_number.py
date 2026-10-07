"""Page-number chrome: small faded page number in the footer area."""

import random

from gi.repository import Pango, PangoCairo

from ..blocks import pango_layout
from ._registry import ChromeStage, record_chrome, register_chrome


@register_chrome("page_number", stage=ChromeStage.AFTER_BLOCKS)
def render_page_number(ctx, *, style, fonts, page_w, page_h, lm, chrome_state, **kw):
    if not style.has_page_number:
        return None
    num = str(random.randint(1, 300))
    m = style.margins
    pn_y = page_h - m["bottom"] + 20
    ctx.move_to(m["left"], pn_y)
    layout = pango_layout(
        ctx,
        num,
        fonts.get("serif", max(7, style.tiny_size + 2)),
        lm.content_w,
        alignment=random.choice([Pango.Alignment.CENTER, Pango.Alignment.RIGHT]),
    )
    ctx.set_source_rgba(*style.text_color, 0.4)
    PangoCairo.show_layout(ctx, layout)
    # Clamp height to the remaining space below pn_y so the bbox can't
    # report a region that extends past the page edge (rare on tight
    # margins where pn_y already sits in the bottom padding strip).
    pn_h = min(max(10, int(style.tiny_size + 2) + 4), max(0, page_h - pn_y))
    record_chrome(chrome_state, "page_number", m["left"], pn_y, lm.content_w, pn_h, text=num)
    return {"page_number": num}
