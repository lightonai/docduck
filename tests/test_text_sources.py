"""Tests for the pluggable TextSource interface."""

import pytest

from docduck.generators import text as text_gen
from docduck.generators.text.sources import (
    TextSource,
    get_text_source,
    register_text_source,
    reset_text_source,
    set_text_source,
    text_sources,
)


@pytest.fixture(autouse=True)
def _restore_default_source():
    reset_text_source()
    yield
    reset_text_source()


class TestRegistry:
    def test_default_source_is_markov(self):
        assert type(get_text_source()).__name__ == "MarkovSource"

    def test_markov_and_hf_registered(self):
        names = set(text_sources.as_dict().keys())
        assert {"markov", "hf"}.issubset(names)

    def test_set_unknown_source_raises(self):
        with pytest.raises(KeyError):
            set_text_source("does_not_exist")

    def test_reset_returns_to_markov(self):
        @register_text_source("_tmp_reset")
        class _Tmp(TextSource):
            def sentence(self, lang):
                return "tmp"

            def short(self, lang, max_words=12):
                return "tmp"

        try:
            set_text_source("_tmp_reset")
            assert type(get_text_source()).__name__ == "_Tmp"
            reset_text_source()
            assert type(get_text_source()).__name__ == "MarkovSource"
        finally:
            text_sources.unregister("_tmp_reset")


class TestDispatch:
    """A custom source must be picked up by every gen_* entry point that
    sources text, with no edits to the block code."""

    def _install_marker(self):
        @register_text_source("_marker")
        class MarkerSource(TextSource):
            def sentence(self, lang):
                return "MARKER_SENTENCE_PROBE about quantum frogs."

            def short(self, lang, max_words=12):
                return "MARKER_SHORT"

        set_text_source("_marker")
        return "MARKER_SENTENCE_PROBE", "MARKER_SHORT"

    def teardown_method(self):
        if "_marker" in text_sources.as_dict():
            text_sources.unregister("_marker")

    def test_gen_paragraph_uses_active_source(self):
        sentinel, _ = self._install_marker()
        out = text_gen.gen_paragraph(lang="en")
        assert sentinel in out

    def test_gen_blockquote_uses_active_source(self):
        sentinel, _ = self._install_marker()
        out = text_gen.gen_blockquote(lang="en")
        assert sentinel in out

    def test_gen_list_items_uses_active_source(self):
        sentinel, _ = self._install_marker()
        items = text_gen.gen_list_items(n=3, lang="en")
        assert all(sentinel in s for s in items)

    def test_gen_title_uses_active_source(self):
        _, short = self._install_marker()
        # gen_title cleans/capitalizes the short phrase; the core token survives.
        out = text_gen.gen_title("en")
        assert "MARKER" in out

    def test_gen_heading_uses_active_source(self):
        _, short = self._install_marker()
        out = text_gen.gen_heading("en")
        assert "MARKER" in out

    def test_gen_definition_items_uses_active_source(self):
        sentinel, _ = self._install_marker()
        items = text_gen.gen_definition_items(n=2, lang="en")
        # Definition body is a sentence
        assert all(sentinel in defn for (_term, defn) in items)


class TestMarkovUnchanged:
    """The default Markov path keeps producing non-empty text for English."""

    def test_paragraph_nonempty(self):
        out = text_gen.gen_paragraph(lang="en")
        assert isinstance(out, str)
        assert len(out) > 20

    def test_title_nonempty(self):
        out = text_gen.gen_title("en")
        assert isinstance(out, str)
        assert len(out) > 0


class TestHFSpecParsing:
    """Verify the colon-separated spec parser without touching the network."""

    def test_from_spec_parts(self):
        from docduck.generators.text.sources.hf import HFSource

        # Stub `load_dataset` so we can assert the parsed args without a network call.
        captured = {}

        class _StubRow(dict):
            pass

        class _StubDS:
            column_names = ["text"]

            def __len__(self):
                return 1

            def select(self, idx):
                return {"text": ["This is a test sentence. " * 5]}

        def fake_load_dataset(dataset, config=None, split="train"):
            captured["args"] = (dataset, config, split)
            return _StubDS()

        # HFSource imports load_dataset lazily inside __init__, so patch
        # the `datasets` module attribute instead.
        import datasets
        import datasets as _datasets_mod  # noqa: F401  (only to verify monkeypatch target)

        orig_load = datasets.load_dataset
        datasets.load_dataset = fake_load_dataset
        try:
            HFSource.from_spec("acme/corpus::train:text")
            assert captured["args"] == ("acme/corpus", None, "train")
        finally:
            datasets.load_dataset = orig_load
