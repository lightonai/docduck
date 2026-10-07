"""Logo injection chrome: prepends a 'logo' block to the sequence if style.has_logo.

Runs at BLOCK_INJECTION stage (before the block loop). Doesn't draw anything
itself: just mutates the block sequence via the state dict.
"""

from ._registry import ChromeStage, register_chrome


@register_chrome("logo_inject", stage=ChromeStage.BLOCK_INJECTION)
def inject_logo(ctx, *, style, page_config, block_sequence, **kw):
    """Prepend 'logo' to the block sequence if enabled."""
    wants_logo = getattr(style, "has_logo", False) and (
        page_config is None or page_config.blocks is None
    )
    if not wants_logo:
        return None
    if not block_sequence or block_sequence[0] != "logo":
        block_sequence.insert(0, "logo")
    return None
