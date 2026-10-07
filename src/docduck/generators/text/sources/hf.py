"""HuggingFace-dataset text source.

Pulls real text out of any `datasets`-compatible dataset, splits each
example into sentences, caches the pool in memory, and samples from it.
The `datasets` library is an optional dependency: `pip install datasets`
or install with the `[hf]` extra.

Usage:
    from docduck.generators import text as text_gen
    text_gen.set_text_source(
        "hf",
        dataset="acme/corpus",
        config="2024.en",
        split="train",
        column="text",
        n_samples=2000,
    )
    text_gen.gen_paragraph(lang="en")  # now comes from the dataset

Or parse a single colon-separated spec via `HFSource.from_spec("id:config:split:column")`.
"""

import random
import re

from ._base import TextSource, register_text_source

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_DEFAULT_N_SAMPLES = 2000
_MIN_SENT_LEN = 20
_MAX_SENT_LEN = 280


@register_text_source("hf")
class HFSource(TextSource):
    def __init__(
        self,
        dataset: str,
        config: str | None = None,
        split: str = "train",
        column: str = "text",
        n_samples: int = _DEFAULT_N_SAMPLES,
        seed: int | None = None,
    ):
        try:
            from datasets import load_dataset
        except ImportError as e:
            raise ImportError(
                "The 'datasets' package is required for HFSource. "
                'Install with: pip install datasets (or `pip install -e ".[hf]"`)'
            ) from e

        self.spec = (dataset, config, split, column)
        self._rng = random.Random(seed)
        ds = load_dataset(dataset, config, split=split)
        if column not in ds.column_names:
            raise KeyError(
                f"column {column!r} not in dataset {dataset}; available: {ds.column_names}"
            )

        n = min(n_samples, len(ds))
        idx = self._rng.sample(range(len(ds)), n) if n < len(ds) else list(range(len(ds)))
        rows = ds.select(idx)[column]

        sentences: list[str] = []
        for text in rows:
            if not isinstance(text, str):
                continue
            for s in _SENT_SPLIT.split(text):
                s = s.strip()
                if _MIN_SENT_LEN <= len(s) <= _MAX_SENT_LEN:
                    sentences.append(s)
        if not sentences:
            raise ValueError(
                f"no sentences harvested from {dataset}:{config or '_'}:{split}:{column}; "
                f"sampled {n} rows but every example was filtered out (length bounds: "
                f"{_MIN_SENT_LEN}..{_MAX_SENT_LEN} chars)"
            )
        self._sentences = sentences

    @classmethod
    def from_spec(cls, spec: str, **kwargs) -> "HFSource":
        """Parse `dataset[:config[:split[:column]]]` into HFSource(...)."""
        parts = spec.split(":")
        dataset = parts[0]
        config = parts[1] if len(parts) > 1 and parts[1] else None
        split = parts[2] if len(parts) > 2 and parts[2] else "train"
        column = parts[3] if len(parts) > 3 and parts[3] else "text"
        return cls(dataset=dataset, config=config, split=split, column=column, **kwargs)

    def sentence(self, lang: str | None) -> str:
        return self._rng.choice(self._sentences)

    def short(self, lang: str | None, max_words: int = 12) -> str | None:
        s = self._rng.choice(self._sentences).rstrip(".").rstrip(",")
        words = s.split()
        if len(words) > max_words:
            s = " ".join(words[:max_words])
        return s
