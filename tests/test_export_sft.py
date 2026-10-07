"""Tests for docduck.cli.export_sft."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from docduck.cli import export_sft


def _fake_batch(tmp_path: Path, n: int = 4) -> Path:
    """Write a minimal synthetic batch directory that export_sft can consume."""
    pages = []
    for i in range(n):
        png = tmp_path / f"page_{i:04d}.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        gt = tmp_path / f"page_{i:04d}.md"
        gt.write_text(f"# Title {i}\n\nBody text for page {i}.\n", encoding="utf-8")
        pages.append(
            {
                "filename": png.name,
                "ground_truth_file": gt.name,
                "seed": 1000 + i,
                "lang": "en" if i % 2 == 0 else "fr",
                "complexity": "medium",
                "width": 900,
                "height": 1200,
                "coverage": 0.5 + 0.05 * i,
                "blocks": ["heading", "prose"],
                "style": {
                    "paper": "white",
                    "text_color": "near_black",
                    "accent": "navy",
                    "margins": "standard",
                    "body_size": 11.0,
                },
                "fonts": {"serif": "Merriweather", "sans": "Inter", "mono": "IBM Plex Mono"},
                "annotations": [],
            }
        )
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps({"pages": pages}), encoding="utf-8")
    return meta_path


def test_export_writes_parquet_and_sharded_tar(tmp_path):
    meta = _fake_batch(tmp_path, n=5)
    out = tmp_path / "dataset"

    # Small shard size to exercise the sharded path on tiny fixtures.
    report = export_sft.export(meta, out, val_frac=0.2, seed=0, files_per_shard=2)

    assert report["train_rows"] + report["val_rows"] == 5
    assert (out / "data" / "train-00000-of-00001.parquet").exists()
    assert (out / "data" / "validation-00000-of-00001.parquet").exists()
    # 5 pages / 2 per shard → 3 shards (2+2+1)
    assert report["n_tar_shards"] == 3
    for i in range(3):
        assert (out / "images" / f"pages-{i:05d}.tar").exists()


def test_monolithic_tar_when_files_per_shard_zero(tmp_path):
    """files_per_shard=0 preserves the legacy single pages.tar layout."""
    meta = _fake_batch(tmp_path, n=3)
    out = tmp_path / "dataset"
    report = export_sft.export(meta, out, val_frac=0, seed=0, files_per_shard=0)

    assert report["n_tar_shards"] == 1
    assert (out / "images" / "pages.tar").exists()
    with tarfile.open(out / "images" / "pages.tar") as tf:
        names = sorted(tf.getnames())
    assert names == ["pages/page_0000.png", "pages/page_0001.png", "pages/page_0002.png"]


def test_sharded_tars_cover_all_pages(tmp_path):
    """Across all shards, every page PNG appears exactly once."""
    meta = _fake_batch(tmp_path, n=7)
    out = tmp_path / "dataset"
    export_sft.export(meta, out, val_frac=0, seed=0, files_per_shard=3)

    all_names: list[str] = []
    for tar_path in sorted((out / "images").glob("pages-*.tar")):
        with tarfile.open(tar_path) as tf:
            all_names.extend(tf.getnames())
    assert sorted(all_names) == sorted(f"pages/page_{i:04d}.png" for i in range(7))


def test_row_schema_matches_lightocr_crops(tmp_path):
    """messages/images/key/metadata shape must match lightonai/lightocr-gpt4o-crops."""
    meta = _fake_batch(tmp_path, n=2)
    out = tmp_path / "dataset"
    export_sft.export(meta, out, val_frac=0, seed=0)

    t = pq.read_table(out / "data" / "train-00000-of-00001.parquet")
    names = set(t.schema.names)
    assert names == {"messages", "images", "key", "metadata"}

    rows = t.to_pylist()
    assert len(rows) == 2

    r = rows[0]
    assert r["messages"][0] == {"role": "user", "content": "<IMG_0>"}
    assert r["messages"][1]["role"] == "assistant"
    assert r["messages"][1]["content"].startswith("# Title")
    assert r["images"][0].startswith("pages/page_")
    assert r["key"].startswith("page_")
    assert r["metadata"]["image_height"] == 1200
    assert r["metadata"]["image_width"] == 900
    assert r["metadata"]["lang"] in ("en", "fr")


def test_metadata_preserves_all_fields(tmp_path):
    """All docduck page attrs (fonts, style, blocks, seed, coverage) land in metadata."""
    meta = _fake_batch(tmp_path, n=1)
    out = tmp_path / "dataset"
    export_sft.export(meta, out, val_frac=0, seed=0)

    t = pq.read_table(out / "data" / "train-00000-of-00001.parquet")
    row = t.to_pylist()[0]
    m = row["metadata"]
    assert m["fonts"] == {"serif": "Merriweather", "sans": "Inter", "mono": "IBM Plex Mono"}
    assert m["style"]["paper"] == "white"
    assert m["style"]["accent"] == "navy"
    assert m["style"]["body_size"] == 11.0
    assert m["blocks"] == ["heading", "prose"]
    assert m["complexity"] == "medium"
    assert m["seed"] == 1000
    assert m["coverage"] == pytest.approx(0.5)


def test_no_validation_when_val_frac_zero(tmp_path):
    meta = _fake_batch(tmp_path, n=3)
    out = tmp_path / "dataset"
    report = export_sft.export(meta, out, val_frac=0, seed=0)

    assert report["val_rows"] == 0
    assert not (out / "data" / "validation-00000-of-00001.parquet").exists()


def test_split_is_disjoint_and_covers_all(tmp_path):
    meta = _fake_batch(tmp_path, n=10)
    out = tmp_path / "dataset"
    export_sft.export(meta, out, val_frac=0.3, seed=42)

    train = pq.read_table(out / "data" / "train-00000-of-00001.parquet").to_pylist()
    val = pq.read_table(out / "data" / "validation-00000-of-00001.parquet").to_pylist()
    train_keys = {r["key"] for r in train}
    val_keys = {r["key"] for r in val}

    assert train_keys.isdisjoint(val_keys)
    assert len(train_keys) + len(val_keys) == 10
