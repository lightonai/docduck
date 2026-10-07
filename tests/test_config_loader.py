"""Tests for the YAML config loader."""

import os
import tempfile

from docduck.config_loader import apply_defaults, deep_merge, load_config, load_yaml
from docduck.defaults import DEFAULTS, get_defaults
from docduck.page_config import PageConfig


class TestDeepMerge:
    def test_replaces_scalar(self):
        assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_merges_nested_dicts(self):
        base = {"style": {"papers": {"white": 1}, "margins": 5}}
        over = {"style": {"papers": {"cream": 2}}}
        result = deep_merge(base, over)
        assert result["style"]["papers"] == {"white": 1, "cream": 2}
        assert result["style"]["margins"] == 5

    def test_replaces_list(self):
        assert deep_merge({"x": [1, 2]}, {"x": [3]}) == {"x": [3]}

    def test_does_not_mutate_base(self):
        base = {"x": {"y": 1}}
        deep_merge(base, {"x": {"z": 2}})
        assert base == {"x": {"y": 1}}

    def test_empty_overrides_returns_copy(self):
        base = {"a": 1}
        result = deep_merge(base, {})
        assert result == base
        assert result is not base  # deep copy


class TestLoadYaml:
    def test_empty_file(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        f.write("")
        f.close()
        try:
            assert load_yaml(f.name) == {}
        finally:
            os.unlink(f.name)

    def test_loads_nested(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        f.write("foo:\n  bar: 42\n")
        f.close()
        try:
            assert load_yaml(f.name) == {"foo": {"bar": 42}}
        finally:
            os.unlink(f.name)


class TestLoadConfig:
    def _yaml(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_empty_config_gives_defaults(self):
        path = self._yaml("")
        try:
            cfg, defaults = load_config(path)
            assert isinstance(cfg, PageConfig)
            assert defaults == DEFAULTS
        finally:
            os.unlink(path)

    def test_page_fields_applied(self):
        path = self._yaml("lang: fr\ncomplexity: high\nseed: 123\nn_columns: 2\n")
        try:
            cfg, _ = load_config(path)
            assert cfg.lang == "fr"
            assert cfg.complexity == "high"
            assert cfg.seed == 123
            assert cfg.n_columns == 2
        finally:
            os.unlink(path)

    def test_explicit_blocks(self):
        path = self._yaml("blocks:\n  - heading\n  - prose\n  - callout\n")
        try:
            cfg, _ = load_config(path)
            assert cfg.blocks == ["heading", "prose", "callout"]
        finally:
            os.unlink(path)

    def test_defaults_override_merges(self):
        path = self._yaml(
            "defaults:\n"
            "  table:\n"
            "    stripe_probability: 1.0\n"
            "  style:\n"
            "    flag_probabilities:\n"
            "      has_logo: 1.0\n"
        )
        try:
            _, defaults = load_config(path)
            assert defaults["table"]["stripe_probability"] == 1.0
            assert defaults["style"]["flag_probabilities"]["has_logo"] == 1.0
            # Unrelated keys untouched
            assert (
                defaults["table"]["header_bg_probability"]
                == DEFAULTS["table"]["header_bg_probability"]
            )
            assert (
                defaults["style"]["flag_probabilities"]["justify"]
                == DEFAULTS["style"]["flag_probabilities"]["justify"]
            )
        finally:
            os.unlink(path)

    def test_brand_palette_override(self):
        path = self._yaml("seed: 99\nbrand_palette: tech_blue\n")
        try:
            cfg, _ = load_config(path)
            assert cfg.style.brand_palette_name == "tech_blue"
            assert cfg.style.primary_color == DEFAULTS["brand_palettes"]["tech_blue"]["primary"]
        finally:
            os.unlink(path)

    def test_features_and_output_dpi_are_explicit_page_fields(self):
        path = self._yaml(
            "output_dpi: 72\nfeatures:\n  content_mode: confusables\n  highlight_prose: 0.25\n"
        )
        try:
            cfg, _ = load_config(path)
            assert cfg.output_dpi == 72
            assert cfg.features.content_mode == "confusables"
            assert cfg.features.highlight_prose == 0.25
            assert "output_dpi" in cfg._yaml_explicit_fields
            assert "features" in cfg._yaml_explicit_fields
        finally:
            os.unlink(path)


class TestApplyDefaults:
    def test_mutates_in_place(self):
        original = DEFAULTS["table"]["stripe_probability"]
        try:
            custom = get_defaults()
            custom["table"]["stripe_probability"] = 0.99
            apply_defaults(custom)
            # Module-level reference: each block module reads DEFAULTS["table"]
            # via its own `D` alias. Verify the source dict was mutated.
            from docduck.defaults import DEFAULTS as live

            assert live["table"]["stripe_probability"] == 0.99
        finally:
            custom = get_defaults()
            custom["table"]["stripe_probability"] = original
            apply_defaults(custom)
