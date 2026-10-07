"""Tests for docduck.cli.dedupe: MinHash + LSH near-duplicate filter."""

from __future__ import annotations

import json
from pathlib import Path

from docduck.cli import dedupe


def _fake_batch(tmp_path: Path, texts: list[str]) -> Path:
    """Write a batch dir with the given ground-truth texts."""
    pages = []
    for i, text in enumerate(texts):
        fname = f"page_{i:06d}.png"
        gt_fname = f"page_{i:06d}.md"
        (tmp_path / fname).write_bytes(b"\x89PNG\r\n\x1a\n")
        (tmp_path / gt_fname).write_text(text, encoding="utf-8")
        pages.append(
            {
                "filename": fname,
                "ground_truth_file": gt_fname,
                "lang": "en",
                "width": 1,
                "height": 1,
            }
        )
    meta = tmp_path / "metadata.json"
    meta.write_text(json.dumps({"pages": pages}), encoding="utf-8")
    return meta


def test_drops_exact_duplicates(tmp_path):
    body = "the quick brown fox jumps over the lazy dog " * 40
    meta = _fake_batch(tmp_path, [body, body, body, "a completely unrelated text " * 30])
    report = dedupe.dedupe(meta, threshold=0.8)
    assert report["input_pages"] == 4
    assert report["output_pages"] == 2
    assert report["dropped"] == 2


def test_keeps_unique_pages(tmp_path):
    texts = [
        "alpha beta gamma delta " * 40,
        "foo bar baz quux " * 40,
        "lorem ipsum dolor sit amet " * 40,
    ]
    meta = _fake_batch(tmp_path, texts)
    report = dedupe.dedupe(meta, threshold=0.7)
    assert report["output_pages"] == 3
    assert report["dropped"] == 0


def test_drops_near_duplicates(tmp_path):
    # Non-repeating base so shingle cardinality is high enough for Jaccard to be
    # dominated by shared content rather than a cycle's distinct shingle set.
    base = (
        "Among the notable findings of the recent study is the observation "
        "that the compound exhibits unusual stability under pressure, a result "
        "which bears on several downstream industrial processes examined "
        "during the investigation of related phenomena throughout the year."
    )
    near = base + " A short additional tail."
    unrelated = "Completely different material about astronomy, with entirely separate vocabulary."
    meta = _fake_batch(tmp_path, [base, near, unrelated])
    report = dedupe.dedupe(meta, threshold=0.8)
    assert report["output_pages"] == 2
    assert report["dropped"] == 1


def test_output_metadata_structure(tmp_path):
    meta = _fake_batch(tmp_path, ["same body " * 50, "same body " * 50])
    out = tmp_path / "out"
    dedupe.dedupe(meta, threshold=0.9, output_dir=out)
    result = json.loads((out / "metadata.json").read_text())
    assert result["total_pages"] == len(result["pages"])
    assert "dedup" in result
    assert result["dedup"]["original_pages"] == 2
    assert result["dedup"]["dropped"] == 1


def test_copy_pages_moves_survivors(tmp_path):
    meta = _fake_batch(tmp_path, ["unique a " * 40, "unique b " * 40])
    out = tmp_path / "out"
    dedupe.dedupe(meta, output_dir=out, copy_pages=True)
    # Both pages are unique -> both PNGs and .txts copied.
    files = sorted(p.name for p in out.iterdir())
    assert "page_000000.png" in files
    assert "page_000000.md" in files
    assert "page_000001.png" in files
    assert "page_000001.md" in files


def test_handles_empty_batch(tmp_path):
    meta = _fake_batch(tmp_path, [])
    report = dedupe.dedupe(meta)
    assert report["input_pages"] == 0
    assert report["output_pages"] == 0


def test_perms_must_divide_bands(tmp_path):
    meta = _fake_batch(tmp_path, ["a " * 20])
    try:
        dedupe.dedupe(meta, perms=100, bands=33)
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-divisible perms/bands")
