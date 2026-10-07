"""Unified page configuration.

A single PageConfig controls all generation parameters for a page:
language, fonts, visual style, layout structure, and content complexity.

Usage:
    # Random config (fully randomized)
    cfg = PageConfig()

    # Constrained (e.g., French, high complexity)
    cfg = PageConfig(lang="fr", complexity="high")

    # From a preset
    cfg = PageConfig.from_preset("academic_zh")

    # Pass to composer
    surface, annotations, blocks, text = compose_page(page_config=cfg)
"""

import random
from dataclasses import dataclass, field

from .diversity import PageStyle
from .fonts import FontPalette
from .generators import text as text_gen

# ---------------------------------------------------------------------------
# Complexity profiles
# ---------------------------------------------------------------------------

COMPLEXITY_PROFILES = {
    "low": {
        "min_blocks": 3,
        "max_blocks": 5,
        "min_distinct": 2,
        "min_sentences": 2,
        "max_sentences": 4,
    },
    "medium": {
        "min_blocks": 5,
        "max_blocks": 8,
        "min_distinct": 3,
        "min_sentences": 3,
        "max_sentences": 6,
    },
    "high": {
        "min_blocks": 7,
        "max_blocks": 12,
        "min_distinct": 4,
        "min_sentences": 4,
        "max_sentences": 8,
    },
}


@dataclass
class Features:
    """Opt-in rendering features: knobs that change how blocks render.

    Scoped to composition-time effects only. Post-processing (scan-artifact
    presets, JPEG recompression, rotation) stays outside in `docduck.artifacts`
    and is applied to the returned surface by the caller: mixing the two
    layers here blurred "what the page IS" with "what happens after".

    Each field defaults to off/no-op. Pass a `Features(...)` to `PageConfig`
    to enable one or more:

        PageConfig(features=Features(
            highlight_prose=0.08,
            highlight_table=0.04,
            content_mode="scrambled",
        ))

    `compose_page` reads this object and applies each feature in its own
    stage of the pipeline: adding a new feature means adding a field
    here and a single dispatch site in the composer.
    """

    # Inline marker-pen highlight (GT emits ==text==).
    highlight_prose: float = 0.0  # per-sentence probability (0 = off)
    highlight_table: float = 0.0  # per-cell probability     (0 = off)

    # Adversarial content for VLM faithfulness probing.
    # One of docduck.adversarial.VALID_MODES.
    content_mode: str = "natural"


@dataclass
class PageConfig:
    """Unified configuration for a single generated page.

    Controls language, visual style, font selection, layout structure,
    and content complexity from a single object.
    """

    # Language (ISO 639-1 code, or None for random)
    lang: str = None

    # Complexity level ("low", "medium", "high", or None for random)
    complexity: str = None

    # Visual style (PageStyle instance, or None to generate)
    style: PageStyle = None

    # Font palette (FontPalette instance, or None to auto-select)
    fonts: FontPalette = None

    # Page dimensions
    page_w: int = 900
    page_h: int = 1200

    # Seed for reproducibility (None = random)
    seed: int = None

    # Explicit block sequence (None = use LayoutPlanner)
    blocks: list = None

    # Page-level column layout (1 = single column, 2-4 = multi-column page)
    n_columns: int = 1

    # Named layout strategy ("single_column" | "multi_column" | "sidebar"),
    # overrides n_columns-based dispatch when set.
    layout: str | None = None

    # Output DPI: the Cairo surface is scaled by output_dpi/72 so text
    # renders at the target pixel density. When None, compose_page uses the
    # DOCDUCK_OUTPUT_DPI env var (default 200).
    output_dpi: int | None = None

    # Opt-in feature collection. All features default off; enable any subset
    # by passing a `Features(...)` instance. See the `Features` docstring.
    features: "Features" = field(default_factory=lambda: Features())

    _complexity_profile: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)

        if self.lang is None:
            available = text_gen.available_languages()
            if available:
                self.lang = random.choice(["en"] * 3 + available)
            else:
                self.lang = "en"

        if self.complexity is None:
            self.complexity = random.choice(["low", "medium", "medium", "high"])
        self._complexity_profile = COMPLEXITY_PROFILES[self.complexity]

        if self.style is None:
            self.style = PageStyle()

        if self.fonts is None:
            self.fonts = FontPalette()

    @property
    def min_blocks(self) -> int:
        return self._complexity_profile["min_blocks"]

    @property
    def max_blocks(self) -> int:
        return self._complexity_profile["max_blocks"]

    @property
    def min_distinct(self) -> int:
        return self._complexity_profile["min_distinct"]

    @property
    def min_sentences(self) -> int:
        return self._complexity_profile["min_sentences"]

    @property
    def max_sentences(self) -> int:
        return self._complexity_profile["max_sentences"]
