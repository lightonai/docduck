"""Image / figure block: real matplotlib plot or geometric pattern fallback."""

import math
import random

import cairo
import numpy as np
from gi.repository import Pango, PangoCairo

from ..block_result import BlockResult
from ..defaults import DEFAULTS as D
from ..generators import text as text_gen
from ._helpers import layout_height, pango_layout
from ._registry import register_block


def _draw_caption(ctx, img_x, img_y, img_w, img_h, text_color, fonts, style, lang):
    d = D["image"]
    caption = text_gen.gen_heading(lang=lang)
    cap_size = style.tiny_size + d["caption_size_offset"] if style else 8
    cap_font = (
        fonts.get("serif", cap_size, italic=True) if fonts else f"DejaVu Serif Italic {cap_size}"
    )
    ctx.move_to(img_x, img_y + img_h + 6)
    layout = pango_layout(ctx, caption, cap_font, img_w, alignment=Pango.Alignment.CENTER)
    ctx.set_source_rgb(*text_color)
    PangoCairo.show_layout(ctx, layout)
    return caption, layout_height(layout)


def _draw_pattern(ctx, pattern_type, img_x, img_y, img_w, img_h, accent_color):
    """Geometric pattern fallback when matplotlib isn't available."""
    d = D["image"]
    if pattern_type == "gradient":
        c1 = [random.uniform(*d["gradient_color_range"]) for _ in range(3)]
        c2 = [random.uniform(*d["gradient_color_range"]) for _ in range(3)]
        angle = random.choice(["horizontal", "vertical", "diagonal"])
        if angle == "horizontal":
            grad = cairo.LinearGradient(img_x, img_y, img_x + img_w, img_y)
        elif angle == "vertical":
            grad = cairo.LinearGradient(img_x, img_y, img_x, img_y + img_h)
        else:
            grad = cairo.LinearGradient(img_x, img_y, img_x + img_w, img_y + img_h)
        grad.add_color_stop_rgb(0, *c1)
        grad.add_color_stop_rgb(1, *c2)
        ctx.set_source(grad)
        ctx.rectangle(img_x, img_y, img_w, img_h)
        ctx.fill()

    elif pattern_type == "noise":
        noise_w, noise_h = max(1, img_w // 4), max(1, img_h // 4)
        noise_lo, noise_hi = d["noise_brightness_range"]
        noise_data = np.random.randint(noise_lo, noise_hi, (noise_h, noise_w, 4), dtype=np.uint8)
        noise_data[:, :, 3] = 255
        noise_surface = cairo.ImageSurface.create_for_data(
            noise_data, cairo.FORMAT_ARGB32, noise_w, noise_h
        )
        ctx.save()
        ctx.translate(img_x, img_y)
        ctx.scale(img_w / noise_w, img_h / noise_h)
        pat = cairo.SurfacePattern(noise_surface)
        pat.set_filter(cairo.FILTER_NEAREST)
        ctx.set_source(pat)
        ctx.rectangle(0, 0, noise_w, noise_h)
        ctx.fill()
        ctx.restore()

    elif pattern_type == "circles":
        ctx.set_source_rgb(0.92, 0.91, 0.88)
        ctx.rectangle(img_x, img_y, img_w, img_h)
        ctx.fill()
        for _ in range(random.randint(*d["circles_count_range"])):
            cx = img_x + random.uniform(0, img_w)
            cy = img_y + random.uniform(0, img_h)
            cr = random.uniform(*d["circles_radius_range"])
            ctx.arc(cx, cy, cr, 0, 2 * math.pi)
            ctx.set_source_rgba(
                random.uniform(0.2, 0.8),
                random.uniform(0.2, 0.8),
                random.uniform(0.2, 0.8),
                random.uniform(0.15, 0.5),
            )
            ctx.fill()

    elif pattern_type == "grid":
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(img_x, img_y, img_w, img_h)
        ctx.fill()
        step = random.randint(*d["grid_step_range"])
        ctx.set_source_rgba(0.7, 0.7, 0.7, 0.5)
        ctx.set_line_width(0.5)
        for gx in range(0, img_w, step):
            ctx.move_to(img_x + gx, img_y)
            ctx.line_to(img_x + gx, img_y + img_h)
        for gy in range(0, img_h, step):
            ctx.move_to(img_x, img_y + gy)
            ctx.line_to(img_x + img_w, img_y + gy)
        ctx.stroke()
        ctx.set_source_rgb(*accent_color)
        for _ in range(random.randint(*d["grid_dot_count_range"])):
            dx = img_x + random.uniform(5, img_w - 5)
            dy = img_y + random.uniform(5, img_h - 5)
            ctx.arc(dx, dy, random.uniform(1.5, 3), 0, 2 * math.pi)
            ctx.fill()

    elif pattern_type == "bars":
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(img_x, img_y, img_w, img_h)
        ctx.fill()
        n_bars = random.randint(5, 15)
        bar_w = (img_w - 20) / n_bars
        for i in range(n_bars):
            bh = random.uniform(0.2, 0.95) * (img_h - 20)
            bx = img_x + 10 + i * bar_w
            by = img_y + img_h - 10 - bh
            ctx.set_source_rgba(*accent_color, random.uniform(0.4, 0.9))
            ctx.rectangle(bx + 2, by, bar_w - 4, bh)
            ctx.fill()

    elif pattern_type == "radial":
        grad = cairo.RadialGradient(
            img_x + img_w / 2,
            img_y + img_h / 2,
            10,
            img_x + img_w / 2,
            img_y + img_h / 2,
            max(img_w, img_h) / 2,
        )
        c = [random.uniform(0.3, 0.7) for _ in range(3)]
        grad.add_color_stop_rgb(0, *[min(1, v + 0.3) for v in c])
        grad.add_color_stop_rgb(1, *c)
        ctx.set_source(grad)
        ctx.rectangle(img_x, img_y, img_w, img_h)
        ctx.fill()

    else:  # checker
        sq = random.randint(10, 25)
        c1 = [random.uniform(0.8, 0.95) for _ in range(3)]
        c2 = [random.uniform(0.6, 0.85) for _ in range(3)]
        for iy in range(0, img_h, sq):
            for ix in range(0, img_w, sq):
                c = c1 if (ix // sq + iy // sq) % 2 == 0 else c2
                ctx.set_source_rgb(*c)
                ctx.rectangle(img_x + ix, img_y + iy, sq, sq)
                ctx.fill()


@register_block("image", weight=12)
def draw_image_placeholder(
    ctx, x, y, width, *, text_color, accent_color, style=None, fonts=None, max_height=None, **kw
):
    d = D["image"]
    img_h = random.randint(*d["height_range"])
    lo_frac, _ = d["width_fraction"]
    img_w = min(width, random.randint(int(width * lo_frac), width))
    img_x = x + (width - img_w) / 2

    # Shrink image height if the caller has limited space: reserve ~40px
    # for caption + bottom margin.
    if max_height is not None:
        budget = int(max_height) - 40
        min_h = d["height_range"][0]
        if budget < img_h:
            img_h = max(min_h, min(img_h, budget))

    if random.random() < 0.6:
        try:
            from ..generators import plot as plot_gen

            plot_surface, plot_type = plot_gen.gen_plot_surface(
                img_w, img_h, seed=random.randint(0, 2**31 - 1)
            )
            pw = plot_surface.get_width()
            ph = plot_surface.get_height()
            ctx.save()
            ctx.translate(img_x, y)
            ctx.scale(img_w / pw, img_h / ph)
            ctx.set_source_surface(plot_surface, 0, 0)
            ctx.paint()
            ctx.restore()

            lang = kw.get("lang")
            caption, cap_h = _draw_caption(
                ctx, img_x, y, img_w, img_h, text_color, fonts, style, lang
            )
            ground_truth = f"![image](image.png)\n\n*{caption}*"
            return BlockResult(
                height=img_h + cap_h + d["bottom_margin"],
                text=ground_truth,
                data={"caption": caption, "kind": "plot", "plot_type": plot_type},
            )
        except Exception as e:
            print(f"  Warning: plot_gen failed ({e!r}); falling back to pattern.")

    pattern_type = random.choice(d["pattern_types"])
    _draw_pattern(ctx, pattern_type, img_x, y, img_w, img_h, accent_color)

    if random.random() < d["border_probability"]:
        ctx.set_source_rgba(*text_color, d["border_opacity"])
        ctx.set_line_width(d["border_width"])
        ctx.rectangle(img_x, y, img_w, img_h)
        ctx.stroke()

    lang = kw.get("lang")
    caption, cap_h = _draw_caption(ctx, img_x, y, img_w, img_h, text_color, fonts, style, lang)
    ground_truth = f"![image](image.png)\n\n*{caption}*"
    return BlockResult(
        height=img_h + cap_h + d["bottom_margin"],
        text=ground_truth,
        data={"caption": caption, "kind": "pattern", "pattern_type": pattern_type},
    )
