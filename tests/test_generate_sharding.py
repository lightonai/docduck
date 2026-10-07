"""Tests for sharded/parallel docduck-generate runs.

These cover the flags needed to shard 1M-page runs across workers:
- ``--start-index`` shifts filenames so workers can share an output dir.
- ``--no-lock-genre`` / the ``lock_genre`` param toggles per-page genre locking
  (default is locked; the batch diversity tracker biases toward least-used
  English genre so coverage of the available en_* models catches up fast).
"""

from __future__ import annotations

import json
import os
import tempfile

from docduck.cli.generate import generate_batch
from docduck.generators import text as text_gen


def test_start_index_shifts_filenames():
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=2, seed=1, start_index=500)
        pngs = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        assert pngs == ["page_000500.png", "page_000501.png"]


def test_start_index_matches_metadata_filenames():
    with tempfile.TemporaryDirectory() as tmp:
        meta = generate_batch(tmp, n_pages=2, seed=1, start_index=42)
        assert meta[0]["filename"] == "page_000042.png"
        assert meta[0]["ground_truth_file"] == "page_000042.md"
        assert meta[1]["filename"] == "page_000043.png"


def test_disjoint_shards_do_not_collide():
    """Two workers writing to the same dir with disjoint index ranges
    produce a combined page set with no filename overlap."""
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=3, seed=1, start_index=0)
        generate_batch(tmp, n_pages=3, seed=2, start_index=3)
        pngs = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        assert pngs == [
            "page_000000.png",
            "page_000001.png",
            "page_000002.png",
            "page_000003.png",
            "page_000004.png",
            "page_000005.png",
        ]


def test_genre_is_recorded_in_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=3, seed=1, lock_genre=True, lang="en")
        meta = json.loads(open(os.path.join(tmp, "metadata.json")).read())
        for p in meta["pages"]:
            assert p.get("genre") is not None
            assert p["genre"].startswith("en_")


def test_genre_lock_biases_toward_least_used():
    """Across one page per available genre, each genre is used exactly once
    (least-used-first picking)."""
    genres = text_gen.english_genres()
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=len(genres), seed=1, lock_genre=True, lang="en")
        meta = json.loads(open(os.path.join(tmp, "metadata.json")).read())
        used = {p["genre"] for p in meta["pages"]}
        assert used == set(genres)


def test_genre_distribution_in_diversity_report():
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=5, seed=1, lock_genre=True, lang="en")
        meta = json.loads(open(os.path.join(tmp, "metadata.json")).read())
        dist = meta["diversity"].get("genre_distribution", {})
        assert sum(dist.values()) == 5
        # Least-used-first keeps the buckets within one of each other.
        assert max(dist.values()) - min(dist.values()) <= 1


def test_no_lock_genre_skips_recording():
    with tempfile.TemporaryDirectory() as tmp:
        generate_batch(tmp, n_pages=3, seed=1, lock_genre=False, lang="en")
        meta = json.loads(open(os.path.join(tmp, "metadata.json")).read())
        # Without the lock, no single genre is attached to a page.
        for p in meta["pages"]:
            assert p.get("genre") is None
