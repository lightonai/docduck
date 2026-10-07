"""Chrome registry: dispatch page-level features.

Chrome renderers run at one of four stages in the composer:
    BACKGROUND        - behind the content (edge shadows, watermarks)
    BEFORE_BLOCKS     - above the block flow (banner, running header)
    BLOCK_INJECTION   - mutates the block sequence before rendering (logo)
    AFTER_BLOCKS      - after the block flow (page number, footer)

Each renderer self-registers via `@register_chrome("name", stage=...)`.
"""

from enum import Enum

from ..registry import Registry


class ChromeStage(str, Enum):
    BACKGROUND = "background"
    BEFORE_BLOCKS = "before_blocks"
    BLOCK_INJECTION = "block_injection"
    AFTER_BLOCKS = "after_blocks"


# One registry per stage so composer can iterate them in deterministic order
_registries = {stage: Registry(f"chrome:{stage.value}") for stage in ChromeStage}


class chrome:  # noqa: N801: deliberately lowercase as a module-level facade
    """Facade exposing per-stage chrome lookups."""

    @staticmethod
    def for_stage(stage: ChromeStage):
        return _registries[stage]

    @staticmethod
    def all():
        """Iterate (stage, name, fn) across every registered chrome."""
        for stage in ChromeStage:
            for name, fn in _registries[stage].items():
                yield stage, name, fn


def register_chrome(name: str, stage: ChromeStage = ChromeStage.BEFORE_BLOCKS, weight: float = 1.0):
    """Decorator that registers a page-chrome renderer at a specific stage.

    Renderer signature:
        fn(ctx, *, style, fonts, page_w, page_h, lm, lang, **kw) -> dict
    The return dict may contain metadata that other stages use (e.g. the
    BEFORE_BLOCKS 'banner' returns {"banner_h": 45} so running_header knows
    to suppress itself). None is equivalent to {}.
    """
    return _registries[stage].register(name, weight=weight)


def record_chrome(chrome_state: dict, kind: str, x, y, width, height, text="", data=None):
    """Push a chrome bbox into `chrome_state["chrome_annotations"]`.

    Chrome renderers draw onto the surface but don't go through LayoutManager,
    so the composer needs a separate channel to surface their bboxes to the
    final `annotations` list. Each entry mirrors a LayoutManager-style
    annotation with block_type prefixed `chrome:<kind>`.
    """
    chrome_state.setdefault("chrome_annotations", []).append(
        {
            "block_type": f"chrome:{kind}",
            "text": text,
            "data": dict(data or {}),
            "bbox": {
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
            },
        }
    )
