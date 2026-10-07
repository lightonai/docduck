"""YAML config loader for docduck.

A YAML file can override any value in DEFAULTS and/or specify PageConfig fields.

Schema:
    # Page-level settings (applied to PageConfig)
    lang: en                        # ISO 639-1 code or null for random
    complexity: high                 # low | medium | high
    seed: 42                         # int or null
    page_w: 900
    page_h: 1200
    n_columns: 1                     # 1-4 for multi-column page layout
    blocks:                          # explicit block sequence (optional)
      - heading
      - prose
      - callout
      - table

    # Style overrides: any key here deep-merges into DEFAULTS
    defaults:
      style:
        flag_probabilities:
          has_logo: 1.0              # always include a logo
          has_banner: 1.0            # always include a banner
      brand_palette_probability: 1.0 # always use a brand palette
      heading:
        styles: ["plain", "accent_bg"]
      table:
        stripe_probability: 1.0

    # Force a specific brand palette (overrides random selection)
    brand_palette: tech_blue         # tech_blue | legal_navy | medical_teal | ...

Usage:
    from docduck.config_loader import load_config
    cfg, defaults = load_config("page.yaml")
    # cfg is a PageConfig, defaults is a merged DEFAULTS dict
"""

import copy

import yaml

from .defaults import DEFAULTS


def deep_merge(base: dict, overrides: dict) -> dict:
    """Deep-merge `overrides` into `base`, returning a new dict.

    Dicts merge recursively. Other values (lists, scalars, tuples) are replaced.
    """
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_yaml(path) -> dict:
    """Load a YAML file and return the parsed dict (empty dict if file is empty)."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or {}


_PAGE_CONFIG_FIELDS = (
    "lang",
    "complexity",
    "seed",
    "page_w",
    "page_h",
    "n_columns",
    "blocks",
    "layout",
    "output_dpi",
)


def load_config(path):
    """Load a YAML config file and build (PageConfig, merged_defaults).

    Returns:
        (page_config, merged_defaults): a PageConfig instance and the merged
        DEFAULTS dict. The caller should pass `merged_defaults` to any
        component that reads DEFAULTS, or monkey-patch DEFAULTS globally
        before rendering.

    The returned PageConfig records which fields were explicitly set in YAML
    on its ``_yaml_explicit_fields`` attr. Callers that generate a batch of
    pages should only forward these explicit fields and leave the rest to
    per-page randomization: otherwise ``PageConfig.__post_init__`` resolves
    defaults *once* (e.g. picks a random complexity) and pins that one value
    across the whole batch.
    """
    from .page_config import PageConfig

    data = load_yaml(path)

    merged = deep_merge(DEFAULTS, data.get("defaults", {}))

    page_fields = {}
    for field in _PAGE_CONFIG_FIELDS:
        if field in data:
            page_fields[field] = data[field]

    # Features block: {highlight_prose, highlight_table, content_mode,
    # artifact_preset, artifact_intensity}. YAML callers declare opt-in
    # features under `features:` same as the Python API.
    if "features" in data:
        from .page_config import Features

        page_fields["features"] = Features(**data["features"])

    cfg = PageConfig(**page_fields)
    # Record the set of fields YAML explicitly declared: callers that span a
    # batch need this to avoid pinning __post_init__ defaults across pages.
    cfg._yaml_explicit_fields = frozenset(page_fields.keys())

    if "brand_palette" in data:
        from .diversity import PageStyle

        cfg.style = PageStyle(defaults=merged, brand_palette=data["brand_palette"])

    return cfg, merged


def apply_defaults(merged: dict) -> None:
    """Monkey-patch the module-level DEFAULTS with the merged config.

    This is needed for blocks that read DEFAULTS at render time via `D = DEFAULTS`.
    Call this before `compose_page` if you want YAML defaults to take effect.
    """
    DEFAULTS.clear()
    DEFAULTS.update(merged)
