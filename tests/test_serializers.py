"""Tests for the pluggable serializer registry."""

from docduck import serializers


def _ann(block_type, text, data=None):
    return {
        "block_type": block_type,
        "text": text,
        "data": data or {},
        "bbox": {"x": 0, "y": 0, "width": 100, "height": 20},
    }


class TestSerializers:
    def test_builtins_registered(self):
        names = set(serializers.serializers.as_dict().keys())
        assert {"plain", "markdown", "json"}.issubset(names)

    def test_plain_strips_headings(self):
        out = serializers.serialize("plain", [_ann("heading", "# Hello"), _ann("prose", "Body")])
        assert "Hello" in out
        assert "#" not in out

    def test_markdown_preserves_markup(self):
        out = serializers.serialize("markdown", [_ann("heading", "# Hello"), _ann("prose", "Body")])
        assert "# Hello" in out
        assert "Body" in out

    def test_markdown_includes_chrome(self):
        chrome = {"banner_title": "Banner", "header_title": "Header", "page_number": "42"}
        out = serializers.serialize("markdown", [], chrome_state=chrome)
        assert "# Banner" in out
        assert "Header" in out
        assert "42" in out

    def test_markdown_chrome_emitted_exactly_once(self):
        """Regression: composer prepends chrome annotations to the annotations
        list AND sets chrome_state.{banner_title,header_title,page_number}.
        The serializer must emit each chrome text exactly once."""
        anns = [
            _ann("chrome:running_header", "My Title"),
            _ann("chrome:page_number", "273"),
            _ann("heading", "# Body Heading"),
            _ann("prose", "Body paragraph."),
        ]
        chrome = {"header_title": "My Title", "page_number": "273"}
        out = serializers.serialize("markdown", anns, chrome_state=chrome)
        assert out.count("My Title") == 1, f"running header duplicated:\n{out}"
        assert out.count("273") == 1, f"page number duplicated:\n{out}"
        assert "# Body Heading" in out
        assert "Body paragraph." in out

    def test_plain_chrome_emitted_exactly_once(self):
        """Same regression for the plain serializer."""
        anns = [
            _ann("chrome:running_header", "My Title"),
            _ann("chrome:page_number", "273"),
            _ann("heading", "# Body Heading"),
        ]
        chrome = {"header_title": "My Title", "page_number": "273"}
        out = serializers.serialize("plain", anns, chrome_state=chrome)
        assert out.count("My Title") == 1, f"running header duplicated:\n{out}"
        assert out.count("273") == 1, f"page number duplicated:\n{out}"

    def test_markdown_numbers_image_refs_per_page(self):
        """Every ![image](image.png) gets a per-page 1-based index (image_1,
        image_2, …) to match Paradigm / LightOnOCR output convention."""
        anns = [
            _ann("heading", "# Title"),
            _ann("image", "![image](image.png)\n\n*Figure 1. First*"),
            _ann("prose", "Some prose."),
            _ann("image", "![image](image.png)\n\n*Figure 2. Second*"),
        ]
        out = serializers.serialize("markdown", anns)
        assert "![image](image_1.png)" in out
        assert "![image](image_2.png)" in out
        # Raw unnumbered form must not leak through
        assert "![image](image.png)" not in out

    def test_markdown_numbers_inline_image_refs_too(self):
        """Image refs can appear inline in prose (not just in image blocks).
        The counter is per-page, regardless of block boundary."""
        anns = [
            _ann("prose", "See ![image](image.png) for detail."),
            _ann("image", "![image](image.png)\n\n*Caption*"),
        ]
        out = serializers.serialize("markdown", anns)
        assert "![image](image_1.png)" in out
        assert "![image](image_2.png)" in out

    def test_json_returns_structured_dict(self):
        data = {"level": 2, "title": "H2"}
        out = serializers.serialize("json", [_ann("subheading", "## H2", data)])
        assert isinstance(out, dict)
        assert out["blocks"][0]["block_type"] == "subheading"
        assert out["blocks"][0]["data"] == data

    def test_custom_serializer_registers(self):
        @serializers.register_serializer("_uppercase")
        def upper(annotations, chrome_state=None):
            return " ".join(a["text"].upper() for a in annotations)

        try:
            out = serializers.serialize("_uppercase", [_ann("prose", "hello")])
            assert out == "HELLO"
        finally:
            serializers.serializers.unregister("_uppercase")
