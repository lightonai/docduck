"""Features composition tests.

Every opt-in rendering feature lives on `PageConfig.features: Features`.
These tests assert that:
  1. Each feature has no effect when disabled (default).
  2. Each feature has its effect when enabled in isolation.
  3. Multiple features combine freely: enabling two never disables a third.
  4. Feature flags don't leak out of the compose call (DEFAULTS is restored).

Scope: composition-time features only. Scan-artifact post-processing lives
outside in `docduck.artifacts` and is tested in tests/test_artifacts.py.
"""

from docduck.composer import compose_page
from docduck.defaults import DEFAULTS
from docduck.page_config import Features, PageConfig


def _render(**feature_kwargs):
    """Render a fixed-seed page with a specific feature config."""
    cfg = PageConfig(
        lang="en",
        complexity="low",
        seed=123,
        page_w=600,
        page_h=800,
        output_dpi=72,
        features=Features(**feature_kwargs),
    )
    surface, _, _, text = compose_page(page_config=cfg)
    return surface, text


# ---------------------------------------------------------------------------
# 1. Defaults → no feature takes effect.
# ---------------------------------------------------------------------------


def test_defaults_no_highlights():
    _, text = _render()
    assert "==" not in text
    assert "<span" not in text


def test_defaults_preserve_global_state():
    """A compose call must not leak feature flags into DEFAULTS."""
    prev_prose = DEFAULTS["prose"]["highlight_prob"]
    prev_table = DEFAULTS["table"]["highlight_prob"]
    _render(highlight_prose=0.5, highlight_table=0.5)
    assert DEFAULTS["prose"]["highlight_prob"] == prev_prose
    assert DEFAULTS["table"]["highlight_prob"] == prev_table


def test_defaults_restore_on_exception():
    """Even if compose raises, DEFAULTS is restored."""
    prev_prose = DEFAULTS["prose"]["highlight_prob"]
    prev_table = DEFAULTS["table"]["highlight_prob"]
    bad = PageConfig(
        seed=1,
        page_w=600,
        page_h=800,
        output_dpi=72,
        features=Features(highlight_prose=0.5, highlight_table=0.5),
        blocks=["__does_not_exist__"],
    )
    try:
        compose_page(page_config=bad)
    except Exception:
        pass
    assert DEFAULTS["prose"]["highlight_prob"] == prev_prose
    assert DEFAULTS["table"]["highlight_prob"] == prev_table


# ---------------------------------------------------------------------------
# 2. Each feature in isolation.
# ---------------------------------------------------------------------------


def test_highlight_prose_alone():
    _, text = _render(highlight_prose=1.0)
    assert "==" in text
    assert "<span" not in text  # always mapped through pango_to_markdown


def test_highlight_table_alone():
    cfg = PageConfig(
        lang="en",
        seed=42,
        page_w=800,
        page_h=1000,
        output_dpi=72,
        blocks=["heading", "table"],
        features=Features(highlight_table=1.0),
    )
    _, _, _, text = compose_page(page_config=cfg)
    assert text.count("==") >= 4  # many table cells → many markers
    assert "<span" not in text


def test_content_mode_alone():
    """content_mode=scrambled produces different text than natural at same seed."""
    _, t_natural = _render()
    _, t_scrambled = _render(content_mode="scrambled")
    assert t_natural != t_scrambled


# ---------------------------------------------------------------------------
# 3. Features combine freely.
# ---------------------------------------------------------------------------


def test_highlight_prose_plus_table():
    _, text = _render(highlight_prose=1.0, highlight_table=1.0)
    assert "==" in text
    # Both sources should contribute: very rough lower bound.
    assert text.count("==") >= 6


def test_all_features_together():
    """Every Features field on at once still yields a valid page."""
    cfg = PageConfig(
        lang="en",
        seed=7,
        page_w=600,
        page_h=800,
        output_dpi=72,
        features=Features(
            highlight_prose=0.5,
            highlight_table=0.5,
            content_mode="scrambled",
        ),
    )
    surface, _, _, text = compose_page(page_config=cfg)
    assert surface is not None
    assert text  # non-empty
