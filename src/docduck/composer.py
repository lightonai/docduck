"""Page composer: runs chrome stages + dispatches block rendering.

Chrome lifecycle: BACKGROUND → BEFORE_BLOCKS → BLOCK_INJECTION → AFTER_BLOCKS.
Adding a page-level feature is a `@register_chrome` decorator: no composer edit.
"""

import os
import random

import cairo

from . import chrome, layouts, serializers
from .chrome import ChromeStage
from .defaults import DEFAULTS
from .diversity import LayoutPlanner, PageStyle
from .fonts import FontPalette
from .generators import text as text_gen
from .layout import LayoutManager
from .page_config import Features

# Output resolution. 200 matches LightOnOCR's training distribution. Set
# DOCDUCK_OUTPUT_DPI=72 in the test suite to skip the 2.78× pixel blow-up.
DEFAULT_OUTPUT_DPI = int(os.environ.get("DOCDUCK_OUTPUT_DPI", "200"))


def compose_page(
    seed=None,
    page_w=900,
    page_h=1200,
    style=None,
    fonts=None,
    page_config=None,
    output_dpi=None,
):
    """Compose a single document page.

    `page_w`/`page_h` are logical pixel dimensions (unchanged from legacy
    callers); `output_dpi` scales the output surface so text renders at the
    DPI LightOnOCR was trained on (~200). Setting output_dpi=72 reverts to
    the legacy 1:1 rendering.

    Returns: (surface, annotations, block_sequence, full_page_text)
    """
    if page_config is not None:
        seed = page_config.seed
        page_w = page_config.page_w
        page_h = page_config.page_h
        style = page_config.style
        fonts = page_config.fonts
        lang = page_config.lang if page_config.lang != "en" else None
        if output_dpi is None and getattr(page_config, "output_dpi", None) is not None:
            output_dpi = page_config.output_dpi
        features = page_config.features
    else:
        lang = None
        features = Features()
    text_gen.set_content_mode(features.content_mode)
    # diverse_typos needs to know the page language to load the right dict
    # (so single-edit mutations of French words can be checked against a
    # French dict, not American English).
    from . import adversarial as _adv

    _adv.set_typo_lang(page_config.lang if page_config is not None else "en")

    if output_dpi is None:
        output_dpi = DEFAULT_OUTPUT_DPI

    if seed is not None:
        random.seed(seed)

    if style is None:
        style = PageStyle()
    if fonts is None:
        fonts = FontPalette()

    m = style.margins
    dpi_scale = output_dpi / 72.0
    lm = LayoutManager(
        page_w, page_h, m["top"], m["bottom"], m["left"], m["right"], dpi_scale=dpi_scale
    )

    # Scale output so text renders at the target DPI; drawing code below
    # keeps using logical coords.
    surface = cairo.ImageSurface(
        cairo.FORMAT_ARGB32, int(page_w * dpi_scale), int(page_h * dpi_scale)
    )
    ctx = cairo.Context(surface)
    ctx.scale(dpi_scale, dpi_scale)

    ctx.set_source_rgb(*style.paper_color)
    ctx.paint()

    # Install per-call feature flags into DEFAULTS for the duration of this
    # compose. Block renderers read DEFAULTS directly, so this is the single
    # seam where PageConfig.features → block behavior. Always restored.
    _saved_prose_h = DEFAULTS["prose"]["highlight_prob"]
    _saved_table_h = DEFAULTS["table"]["highlight_prob"]
    DEFAULTS["prose"]["highlight_prob"] = features.highlight_prose
    DEFAULTS["table"]["highlight_prob"] = features.highlight_table

    try:
        # Shared across chrome stages (e.g. banner writes banner_h so running_header
        # can suppress itself).
        chrome_state: dict = {}

        def run_stage(stage, **extra):
            """Run every registered chrome at `stage`, updating chrome_state."""
            for _name, fn in chrome.chrome.for_stage(stage).items():
                result = fn(
                    ctx,
                    style=style,
                    fonts=fonts,
                    page_w=page_w,
                    page_h=page_h,
                    lm=lm,
                    lang=lang,
                    page_config=page_config,
                    chrome_state=chrome_state,
                    **extra,
                )
                if result:
                    chrome_state.update(result)

        run_stage(ChromeStage.BACKGROUND)
        run_stage(ChromeStage.BEFORE_BLOCKS)

        n_columns = page_config.n_columns if page_config else 1
        layout_name = page_config.layout if page_config else None

        # Explicit blocks suppress fill_remaining() in the layout strategy
        # so `--blocks table` doesn't sneak in unrequested prose.
        explicit_blocks = page_config is not None and page_config.blocks is not None
        if explicit_blocks:
            block_sequence = list(page_config.blocks)
        elif page_config is not None:
            # Sidebar has two flow regions (main + aside); multi-column has n_columns.
            col_scale = 2 if layout_name == "sidebar" else max(1, n_columns)
            planner = LayoutPlanner(
                min_blocks=page_config.min_blocks * col_scale,
                max_blocks=page_config.max_blocks * col_scale,
                min_distinct=page_config.min_distinct,
            )
            block_sequence = planner.plan()
        else:
            planner = LayoutPlanner(min_blocks=3, max_blocks=7, min_distinct=3)
            block_sequence = planner.plan()

        run_stage(ChromeStage.BLOCK_INJECTION, block_sequence=block_sequence)

        block_spacing = random.uniform(4, 12)
        block_seeds = [random.randint(0, 2**31) for _ in block_sequence]
        strategy = layouts.for_page(n_columns, layout_name=layout_name)
        placed_sequence = strategy.render(
            ctx,
            lm,
            style,
            fonts,
            block_sequence,
            lang,
            block_seeds,
            block_spacing,
            page_w,
            page_h,
            m,
            fill_with_prose=not explicit_blocks,
        )

        run_stage(ChromeStage.AFTER_BLOCKS)
    finally:
        DEFAULTS["prose"]["highlight_prob"] = _saved_prose_h
        DEFAULTS["table"]["highlight_prob"] = _saved_table_h

    annotations = lm.get_annotations()
    chrome_annotations = chrome_state.get("chrome_annotations", [])
    if chrome_annotations:
        annotations = chrome_annotations + annotations
    full_page_text = serializers.serialize("markdown", annotations, chrome_state=chrome_state)
    return surface, annotations, placed_sequence, full_page_text
