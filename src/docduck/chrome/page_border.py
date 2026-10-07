"""Page-border chrome: thin inset border around the content area."""

from ._registry import ChromeStage, record_chrome, register_chrome


@register_chrome("page_border", stage=ChromeStage.BACKGROUND)
def render_page_border(ctx, *, style, page_w, page_h, chrome_state, **kw):
    if not style.has_page_border:
        return None
    m = style.margins
    bx = m["left"] - 10
    by = m["top"] - 10
    bw = page_w - m["left"] - m["right"] + 20
    bh = page_h - m["top"] - m["bottom"] + 20
    ctx.set_source_rgba(*style.text_color, 0.15)
    ctx.set_line_width(0.8)
    ctx.rectangle(bx, by, bw, bh)
    ctx.stroke()
    record_chrome(chrome_state, "page_border", bx, by, bw, bh)
    return None
