"""Tests for the HTML gallery visualizer."""

import json
import tempfile
from pathlib import Path

import cairo

from docduck.cli.visualize import _filter_pages, _sort_pages, build_html


def _make_fake_metadata(tmpdir, n_pages=3):
    """Create a fake metadata.json + PNG files in tmpdir."""
    pages = []
    for i in range(n_pages):
        fname = f"page_{i:06d}.png"
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        surface.write_to_png(str(Path(tmpdir) / fname))
        pages.append(
            {
                "filename": fname,
                "seed": 100 + i,
                "lang": ["en", "fr", "de"][i % 3],
                "complexity": "medium",
                "coverage": 0.5 + i * 0.1,
                "style": {"paper": "white", "accent": "navy"},
                "blocks": ["heading", "prose"],
                "annotations": [],
            }
        )
    meta_path = Path(tmpdir) / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump({"total_pages": n_pages, "pages": pages}, f)
    return meta_path


class TestFilterPages:
    def test_no_filter(self):
        pages = [{"lang": "en"}, {"lang": "fr"}]
        assert _filter_pages(pages, None) == pages
        assert _filter_pages(pages, "") == pages

    def test_filter_top_level_key(self):
        pages = [{"lang": "en"}, {"lang": "fr"}, {"lang": "en"}]
        assert _filter_pages(pages, "lang=en") == [{"lang": "en"}, {"lang": "en"}]

    def test_filter_nested_style_key(self):
        pages = [
            {"style": {"paper": "white"}},
            {"style": {"paper": "cream"}},
        ]
        result = _filter_pages(pages, "paper=white")
        assert result == [{"style": {"paper": "white"}}]


class TestSortPages:
    def test_no_sort(self):
        pages = [{"coverage": 0.3}, {"coverage": 0.1}]
        assert _sort_pages(pages, None) == pages

    def test_ascending(self):
        pages = [{"coverage": 0.3}, {"coverage": 0.1}, {"coverage": 0.5}]
        sorted_pages = _sort_pages(pages, "coverage")
        assert [p["coverage"] for p in sorted_pages] == [0.1, 0.3, 0.5]

    def test_descending(self):
        pages = [{"coverage": 0.3}, {"coverage": 0.1}, {"coverage": 0.5}]
        sorted_pages = _sort_pages(pages, "-coverage")
        assert [p["coverage"] for p in sorted_pages] == [0.5, 0.3, 0.1]


class TestBuildHtml:
    def test_produces_html_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=3)
            out = build_html(meta_path)
            assert out.exists()
            content = out.read_text()
            assert "<html" in content
            assert "</html>" in content

    def test_includes_all_pages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=3)
            out = build_html(meta_path)
            content = out.read_text()
            for i in range(3):
                assert f"page_{i:06d}.png" in content

    def test_filter_reduces_cards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=3)
            out = build_html(meta_path, filter_expr="lang=fr")
            content = out.read_text()
            # Only the French page's filename in card title
            assert content.count('class="card-title">page_') == 1

    def test_embeds_small_images_as_base64(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=1)
            out = build_html(meta_path, max_embed_bytes=1_000_000)
            content = out.read_text()
            assert "data:image/png;base64," in content

    def test_falls_back_to_filename_when_too_large(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=1)
            out = build_html(meta_path, max_embed_bytes=10)  # too small
            content = out.read_text()
            # Should reference filename, not embed
            assert 'src="page_000000.png"' in content

    def test_custom_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = _make_fake_metadata(tmpdir, n_pages=1)
            custom_out = Path(tmpdir) / "custom.html"
            out = build_html(meta_path, output_path=custom_out)
            assert out == custom_out
            assert custom_out.exists()
