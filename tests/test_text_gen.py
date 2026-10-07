"""Tests for pipeline.text_gen."""

from docduck.generators import text as text_gen
from docduck.generators.text import _normalize_spacing

# --------------------------------------------------------------------------
# Punctuation-spacing normalization: removes NLTK tokenization artifacts
# --------------------------------------------------------------------------


def test_normalize_spacing_strips_pre_punctuation_whitespace():
    assert _normalize_spacing("Said Hal , the day .") == "Said Hal, the day."
    assert _normalize_spacing("one ; two : three ! four ?") == "one; two: three! four?"


def test_normalize_spacing_strips_whitespace_after_openers():
    assert _normalize_spacing("see ( note ) here") == "see (note) here"
    assert _normalize_spacing("item [ 1 ]") == "item [1]"


def test_normalize_spacing_collapses_multi_space_before_punct():
    assert _normalize_spacing("word   ,  word") == "word,  word"
    # Tabs and newlines count as whitespace too.
    assert _normalize_spacing("word\t,word") == "word,word"


def test_normalize_spacing_none_and_empty_passthrough():
    assert _normalize_spacing(None) is None
    assert _normalize_spacing("") == ""


def test_normalize_spacing_leaves_clean_text_alone():
    clean = "He said, 'Hello, world.' Then he left."
    assert _normalize_spacing(clean) == clean


def test_markov_output_has_no_pre_punct_spaces():
    """Integration: real Markov samples should carry no `word ,` artifacts."""
    # Sample enough to hit the punctuation-bearing paths.
    for _ in range(20):
        s = text_gen._markov_sentence(lang="en", max_words=20)
        if s:
            assert " ," not in s, s
            assert " ." not in s, s
            assert " ;" not in s, s
            assert " :" not in s, s
            assert " !" not in s, s
            assert " ?" not in s, s


class TestGenParagraph:
    def test_returns_string(self):
        result = text_gen.gen_paragraph()
        assert isinstance(result, str)
        assert len(result) > 20

    def test_ends_with_punctuation(self):
        # Markov-generated sentences usually end with punctuation;
        # test across multiple samples since Markov output is stochastic
        endings = [text_gen.gen_paragraph().rstrip()[-1] for _ in range(5)]
        assert any(c in ".!?;:,)" for c in endings)

    def test_min_max_sentences(self):
        result = text_gen.gen_paragraph(min_sentences=1, max_sentences=1)
        assert len(result) > 10

    def test_multiple_sentences(self):
        result = text_gen.gen_paragraph(min_sentences=5, max_sentences=5)
        # Should be substantially longer than a single sentence
        assert len(result) > 100


class TestGenParagraphs:
    def test_returns_string(self):
        result = text_gen.gen_paragraphs(count=2)
        assert isinstance(result, str)

    def test_paragraph_separator(self):
        result = text_gen.gen_paragraphs(count=3)
        # Should have double newlines between paragraphs
        assert "\n\n" in result

    def test_count_respected(self):
        result = text_gen.gen_paragraphs(count=4)
        paragraphs = result.split("\n\n")
        assert len(paragraphs) == 4

    def test_single_paragraph(self):
        result = text_gen.gen_paragraphs(count=1)
        assert "\n\n" not in result
        assert len(result) > 10


class TestGenTitle:
    def test_returns_string(self):
        result = text_gen.gen_title()
        assert isinstance(result, str)
        assert len(result) > 5

    def test_capitalized(self):
        result = text_gen.gen_title()
        assert result[0].isupper()

    def test_no_trailing_period(self):
        for _ in range(20):
            result = text_gen.gen_title()
            assert not result.endswith(".")


class TestGenHeading:
    def test_returns_string(self):
        result = text_gen.gen_heading()
        assert isinstance(result, str)
        assert len(result) > 3

    def test_no_trailing_period(self):
        for _ in range(20):
            result = text_gen.gen_heading()
            assert not result.endswith(".")


class TestGenTableData:
    def test_returns_tuple(self):
        result = text_gen.gen_table_data()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_headers_and_rows(self):
        headers, rows = text_gen.gen_table_data()
        assert isinstance(headers, list)
        assert isinstance(rows, list)
        assert len(headers) >= 3
        assert len(rows) >= 4

    def test_row_column_count_matches_headers(self):
        headers, rows = text_gen.gen_table_data()
        for row in rows:
            assert len(row) == len(headers)

    def test_custom_headers(self):
        custom = ["Name", "Value", "Unit"]
        headers, rows = text_gen.gen_table_data(headers=custom)
        assert headers == custom
        for row in rows:
            assert len(row) == 3

    def test_custom_n_rows(self):
        headers, rows = text_gen.gen_table_data(n_rows=7)
        assert len(rows) == 7

    def test_all_cells_are_strings(self):
        headers, rows = text_gen.gen_table_data()
        for row in rows:
            for cell in row:
                assert isinstance(cell, str)
                assert len(cell) > 0


class TestGenCodeSnippet:
    def test_returns_tuple(self):
        lang, code = text_gen.gen_code_snippet()
        assert isinstance(lang, str)
        assert isinstance(code, str)
        assert len(code) > 10
        assert lang in ("python", "sql", "rust", "javascript", "c", "go", "bash")

    def test_contains_newlines(self):
        # Code snippets should be multi-line
        _, code = text_gen.gen_code_snippet()
        assert "\n" in code


class TestGenFootnotes:
    def test_returns_string(self):
        result = text_gen.gen_footnotes()
        assert isinstance(result, str)

    def test_numbered(self):
        result = text_gen.gen_footnotes(n=3)
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_custom_count(self):
        result = text_gen.gen_footnotes(n=5)
        lines = result.strip().split("\n")
        assert len(lines) == 5

    def test_single_footnote(self):
        result = text_gen.gen_footnotes(n=1)
        assert result.startswith("1.")
        assert "\n" not in result.strip()
