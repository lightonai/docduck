"""Edge-shadow chrome: a soft gradient on the left edge simulating page shadow."""

import cairo

from ._registry import ChromeStage, record_chrome, register_chrome


@register_chrome("edge_shadow", stage=ChromeStage.BACKGROUND)
def render_edge_shadow(ctx, *, style, page_w, page_h, chrome_state, **kw):
    if not style.has_edge_shadow:
        return None
    grad = cairo.LinearGradient(0, 0, 12, 0)
    grad.add_color_stop_rgba(0, 0.5, 0.5, 0.5, 0.15)
    grad.add_color_stop_rgba(1, 0.5, 0.5, 0.5, 0.0)
    ctx.set_source(grad)
    ctx.rectangle(0, 0, 12, page_h)
    ctx.fill()
    record_chrome(chrome_state, "edge_shadow", 0, 0, 12, page_h)
    return None
