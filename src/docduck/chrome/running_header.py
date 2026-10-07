"""Running-header chrome: faded title at the top of the page with a thin rule.

Suppressed automatically when a banner is already present (banner returns
'banner_h' in its result, which the composer passes along as context).
"""

from gi.repository import Pango, PangoCairo

from ..blocks import pango_layout
from ..generators import text as text_gen
from ._registry import ChromeStage, record_chrome, register_chrome


@register_chrome("running_header", stage=ChromeStage.BEFORE_BLOCKS)
def render_running_header(ctx, *, style, fonts, page_w, page_h, lm, lang, chrome_state, **kw):
    if not style.has_header:
        return None
    if chrome_state.get("banner_h"):
        return None

    m = style.margins
    title = text_gen.gen_title(lang=lang)
    header_font = fonts.get("serif", max(7, style.tiny_size + 1))
    header_y = m["top"] - 30
    ctx.move_to(m["left"], header_y)
    layout = pango_layout(ctx, title, header_font, lm.content_w, alignment=Pango.Alignment.CENTER)
    # Clip to one line: a wrapped header would overlap the rule/content below.
    layout.set_ellipsize(Pango.EllipsizeMode.END)
    ctx.set_source_rgba(*style.text_color, 0.4)
    PangoCairo.show_layout(ctx, layout)

    # Rebuild GT title to match the visible prefix.
    if layout.is_ellipsized():
        lo, hi = 0, len(title)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            probe = pango_layout(ctx, title[:mid] + "…", header_font, 9999)
            _, probe_ext = probe.get_pixel_extents()
            if probe_ext.width <= lm.content_w:
                lo = mid
            else:
                hi = mid - 1
        title = (title[:lo].rstrip() + "…") if lo > 0 else "…"

    ctx.set_source_rgba(*style.text_color, 0.15)
    ctx.set_line_width(0.5)
    ctx.move_to(m["left"], m["top"] - 12)
    ctx.line_to(page_w - m["right"], m["top"] - 12)
    ctx.stroke()

    header_h = max(12, int(style.tiny_size + 1) + 4)
    record_chrome(
        chrome_state,
        "running_header",
        m["left"],
        header_y,
        lm.content_w,
        header_h,
        text=title,
    )
    return {"header_title": title}
