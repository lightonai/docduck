"""Tests for pipeline.generate: end-to-end batch generation."""

import hashlib
import json
import os
import tempfile

import pytest

from docduck.cli.generate import generate_batch
from docduck.page_config import Features


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestGenerateBatch:
    def test_creates_output_dir(self):
        with tempfile.TemporaryDirectory() as parent:
            out = os.path.join(parent, "subdir", "output")
            generate_batch(out, n_pages=1, seed=42)
            assert os.path.isdir(out)

    def test_generates_correct_number_of_pages(self, output_dir):
        generate_batch(output_dir, n_pages=5, seed=42)
        pngs = [f for f in os.listdir(output_dir) if f.endswith(".png")]
        assert len(pngs) == 5

    def test_filenames_sequential(self, output_dir):
        generate_batch(output_dir, n_pages=3, seed=42)
        for i in range(3):
            assert os.path.exists(os.path.join(output_dir, f"page_{i:06d}.png"))

    def test_metadata_json_created(self, output_dir):
        generate_batch(output_dir, n_pages=2, seed=42)
        meta_path = os.path.join(output_dir, "metadata.json")
        assert os.path.exists(meta_path)

    def test_metadata_structure(self, output_dir):
        generate_batch(output_dir, n_pages=3, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        assert meta["total_pages"] == 3
        assert "generation_time_s" in meta
        assert meta["generation_time_s"] > 0
        assert "diversity" in meta
        assert "pages" in meta
        assert len(meta["pages"]) == 3

    def test_page_metadata_fields(self, output_dir):
        generate_batch(output_dir, n_pages=2, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        page = meta["pages"][0]
        assert "filename" in page
        assert "seed" in page
        assert "width" in page
        assert "height" in page
        assert "style" in page
        assert "fonts" in page
        assert "blocks" in page
        assert "annotations" in page

    def test_style_metadata(self, output_dir):
        generate_batch(output_dir, n_pages=1, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        style = meta["pages"][0]["style"]
        assert "paper" in style
        assert "text_color" in style
        assert "accent" in style
        assert "margins" in style
        assert "body_size" in style

    def test_fonts_metadata(self, output_dir):
        generate_batch(output_dir, n_pages=1, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        fonts = meta["pages"][0]["fonts"]
        assert "serif" in fonts
        assert "sans" in fonts
        assert "mono" in fonts

    def test_annotations_in_metadata(self, output_dir):
        generate_batch(output_dir, n_pages=1, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        annotations = meta["pages"][0]["annotations"]
        assert isinstance(annotations, list)
        assert len(annotations) > 0
        for ann in annotations:
            assert "block_type" in ann
            assert "bbox" in ann

    def test_diversity_report(self, output_dir):
        generate_batch(output_dir, n_pages=5, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)

        div = meta["diversity"]
        assert div["total_pages"] == 5
        assert div["unique_layouts"] >= 1
        assert "block_type_counts" in div
        assert "style_distribution" in div

    def test_custom_dimensions(self, output_dir):
        generate_batch(output_dir, n_pages=1, seed=42, page_w=600, page_h=800)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)
        assert meta["pages"][0]["width"] == 600
        assert meta["pages"][0]["height"] == 800

    def test_returns_metadata_list(self, output_dir):
        result = generate_batch(output_dir, n_pages=3, seed=42)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_png_files_nonzero_size(self, output_dir):
        generate_batch(output_dir, n_pages=3, seed=42)
        for i in range(3):
            fpath = os.path.join(output_dir, f"page_{i:06d}.png")
            assert os.path.getsize(fpath) > 1000, f"{fpath} is suspiciously small"

    def test_reproducible_with_seed(self, output_dir):
        with tempfile.TemporaryDirectory() as dir2:
            meta1 = generate_batch(output_dir, n_pages=3, seed=123)
            meta2 = generate_batch(dir2, n_pages=3, seed=123)

            for m1, m2 in zip(meta1, meta2):
                assert m1["seed"] == m2["seed"]
                assert m1["blocks"] == m2["blocks"]

    def test_reproducible_ground_truth_text(self, output_dir):
        """Same seed → identical per-page .md ground truth (what SFT export ships)."""
        with tempfile.TemporaryDirectory() as dir2:
            generate_batch(output_dir, n_pages=3, seed=321)
            generate_batch(dir2, n_pages=3, seed=321)
            for i in range(3):
                t1 = open(os.path.join(output_dir, f"page_{i:06d}.md"), encoding="utf-8").read()
                t2 = open(os.path.join(dir2, f"page_{i:06d}.md"), encoding="utf-8").read()
                assert t1 == t2, f"page_{i:06d}.md drifted across runs with same seed"

    def test_reproducible_annotations(self, output_dir):
        """Same seed → identical annotations (block_type, text, bbox) per page."""
        with tempfile.TemporaryDirectory() as dir2:
            meta1 = generate_batch(output_dir, n_pages=3, seed=321)
            meta2 = generate_batch(dir2, n_pages=3, seed=321)
            for m1, m2 in zip(meta1, meta2):
                assert m1["annotations"] == m2["annotations"], (
                    f"annotations drifted at seed={m1['seed']}"
                )

    def test_reproducible_png_bytes(self, output_dir):
        """Same seed → byte-identical PNG output (catches non-threaded randomness)."""
        with tempfile.TemporaryDirectory() as dir2:
            generate_batch(output_dir, n_pages=2, seed=321)
            generate_batch(dir2, n_pages=2, seed=321)
            for i in range(2):
                h1 = hashlib.sha256(
                    open(os.path.join(output_dir, f"page_{i:06d}.png"), "rb").read()
                ).hexdigest()
                h2 = hashlib.sha256(
                    open(os.path.join(dir2, f"page_{i:06d}.png"), "rb").read()
                ).hexdigest()
                assert h1 == h2, f"page_{i:06d}.png bytes drifted (sha256 {h1} != {h2})"

    def test_reproducible_cross_process(self, output_dir):
        """Cross-process: two fresh interpreters (each with its own randomized
        PYTHONHASHSEED) must still produce byte-identical PNGs from the same
        --seed. In-process determinism is not enough: any code that derives a
        seed from ``hash(str)`` would appear stable within one pytest run but
        drift when users actually invoke the CLI twice."""
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as dir2:
            code1 = (
                "from docduck.cli.generate import generate_batch; "
                f"generate_batch({output_dir!r}, n_pages=2, seed=321)"
            )
            code2 = (
                "from docduck.cli.generate import generate_batch; "
                f"generate_batch({dir2!r}, n_pages=2, seed=321)"
            )
            subprocess.run([sys.executable, "-c", code1], check=True, capture_output=True)
            subprocess.run([sys.executable, "-c", code2], check=True, capture_output=True)
            for i in range(2):
                h1 = hashlib.sha256(
                    open(os.path.join(output_dir, f"page_{i:06d}.png"), "rb").read()
                ).hexdigest()
                h2 = hashlib.sha256(
                    open(os.path.join(dir2, f"page_{i:06d}.png"), "rb").read()
                ).hexdigest()
                assert h1 == h2, (
                    f"page_{i:06d}.png drifted cross-process (sha256 {h1} != {h2}) — "
                    "look for hash(str) being used to derive a deterministic seed"
                )

    def test_single_page(self, output_dir):
        generate_batch(output_dir, n_pages=1, seed=42)
        pngs = [f for f in os.listdir(output_dir) if f.endswith(".png")]
        assert len(pngs) == 1

    def test_metadata_json_valid(self, output_dir):
        generate_batch(output_dir, n_pages=5, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)
        # Re-serialize to verify all values are JSON-safe
        json.dumps(meta)

    def test_ground_truth_files_created(self, output_dir):
        generate_batch(output_dir, n_pages=3, seed=42)
        for i in range(3):
            txt_path = os.path.join(output_dir, f"page_{i:06d}.md")
            assert os.path.exists(txt_path), f"Missing ground truth: {txt_path}"

    def test_ground_truth_files_nonempty(self, output_dir):
        generate_batch(output_dir, n_pages=3, seed=42)
        for i in range(3):
            txt_path = os.path.join(output_dir, f"page_{i:06d}.md")
            size = os.path.getsize(txt_path)
            assert size > 10, f"Ground truth file too small: {txt_path} ({size} bytes)"

    def test_ground_truth_file_referenced_in_metadata(self, output_dir):
        generate_batch(output_dir, n_pages=2, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)
        for page in meta["pages"]:
            assert "ground_truth_file" in page
            gt_path = os.path.join(output_dir, page["ground_truth_file"])
            assert os.path.exists(gt_path)

    def test_ground_truth_is_utf8(self, output_dir):
        generate_batch(output_dir, n_pages=2, seed=42)
        for i in range(2):
            txt_path = os.path.join(output_dir, f"page_{i:06d}.md")
            with open(txt_path, encoding="utf-8") as f:
                text = f.read()
            assert isinstance(text, str)

    def test_annotations_have_text(self, output_dir):
        generate_batch(output_dir, n_pages=2, seed=42)
        with open(os.path.join(output_dir, "metadata.json")) as f:
            meta = json.load(f)
        for page in meta["pages"]:
            for ann in page["annotations"]:
                assert "text" in ann
                assert isinstance(ann["text"], str)

    def test_image_text_pairing(self, output_dir):
        generate_batch(output_dir, n_pages=5, seed=42)
        pngs = sorted(f for f in os.listdir(output_dir) if f.endswith(".png"))
        txts = sorted(f for f in os.listdir(output_dir) if f.endswith(".md"))
        assert len(pngs) == len(txts)
        for png, txt in zip(pngs, txts):
            assert png.replace(".png", "") == txt.replace(".md", "")

    def test_generate_batch_applies_features(self, output_dir):
        with tempfile.TemporaryDirectory() as dir2:
            kwargs = {
                "n_pages": 1,
                "seed": 123,
                "blocks": ["heading", "prose"],
                "lang": "en",
                "output_dpi": 72,
            }
            generate_batch(output_dir, **kwargs)
            generate_batch(dir2, **kwargs, features=Features(content_mode="gibberish"))

            natural = open(os.path.join(output_dir, "page_000000.md"), encoding="utf-8").read()
            gibberish = open(os.path.join(dir2, "page_000000.md"), encoding="utf-8").read()
            assert natural != gibberish
