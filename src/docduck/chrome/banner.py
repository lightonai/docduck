"""Banner chrome: full-width brand-colored strip at the top of the page."""

import random

from gi.repository import Pango, PangoCairo

from ..blocks import pango_layout
from ..defaults import DEFAULTS
from ..generators import text as text_gen
from ._registry import ChromeStage, record_chrome, register_chrome


@register_chrome("banner", stage=ChromeStage.BEFORE_BLOCKS)
def render_banner(ctx, *, style, fonts, page_w, page_h, lm, lang, chrome_state, **kw):
    if not getattr(style, "has_banner", False):
        return None

    bd = DEFAULTS["banner"]
    banner_h = random.randint(*bd["height_range"])
    banner_color = style.primary_color if hasattr(style, "primary_color") else style.accent_color
    text_on = style.text_on_primary if hasattr(style, "text_on_primary") else (1.0, 1.0, 1.0)
    m = style.margins

    ctx.set_source_rgb(*banner_color)
    ctx.rectangle(0, 0, page_w, banner_h)
    ctx.fill()

    title = text_gen.gen_title(lang=lang)
    title_size = int(style.heading_size * 0.65) + bd["title_size_offset"]
    title_font = fonts.get("sans", title_size, bold=True)
    inner_w = page_w - m["left"] - m["right"]
    ctx.move_to(m["left"], banner_h / 2 - title_size)
    layout = pango_layout(ctx, title, title_font, inner_w)
    # Clip to one line: wrapped text would spill out of the banner strip
    # and get overdrawn by subsequent blocks, breaking image/GT fidelity.
    layout.set_ellipsize(Pango.EllipsizeMode.END)
    ctx.set_source_rgb(*text_on)
    PangoCairo.show_layout(ctx, layout)

    # If Pango ellipsized, rebuild the visible prefix so GT matches the image.
    if layout.is_ellipsized():
        lo, hi = 0, len(title)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            probe = pango_layout(ctx, title[:mid] + "…", title_font, 9999)
            _, probe_ext = probe.get_pixel_extents()
            if probe_ext.width <= inner_w:
                lo = mid
            else:
                hi = mid - 1
        title = (title[:lo].rstrip() + "…") if lo > 0 else "…"

    if lm.cursor_y < banner_h + 10:
        lm.cursor_y = banner_h + 10

    record_chrome(chrome_state, "banner", 0, 0, page_w, banner_h, text=title)
    return {"banner_h": banner_h, "banner_title": title}
