"""Block registry. Blocks self-register via `@register_block(name, weight)`.

Signature:
    draw_xxx(ctx, x, y, width, *, text_color, accent_color, style, fonts,
             max_height, **kw) -> BlockResult
"""

from ..registry import Registry

blocks = Registry("block")


def register_block(name: str, weight: float = 1.0, measure=None):
    """Register a block renderer.

    `measure(content_w, **kwargs) -> float` is an optional fast-path height
    estimator. When provided, LayoutManager allocates a tighter scratch
    surface instead of its default `max(remaining, 400)` sizing.
    """
    inner = blocks.register(name, weight=weight)

    def wrapper(fn):
        if measure is not None:
            fn.measure = measure
        return inner(fn)

    return wrapper
