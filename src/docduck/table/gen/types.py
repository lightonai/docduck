"""Table specification dataclasses and column-type constants."""

from dataclasses import dataclass


@dataclass
class HeaderCell:
    """A header cell, optionally spanning multiple columns."""

    text: str
    colspan: int = 1


@dataclass
class TableSpec:
    """Complete table specification for the renderer."""

    caption: str
    header_rows: list[list[HeaderCell]]
    data_rows: list[list[str]]
    n_cols: int
    col_widths: list[float] | None = None
    has_row_headers: bool = False
    style: str = None
    # Data-cell rowspans. Maps (row_idx, col_idx) -> rowspan. Cells covered
    # by a span (rows below a spanned top cell) still appear in `data_rows`
    # with empty text; the renderer skips drawing and the GT emitter skips
    # emitting <td> for them.
    row_spans: dict = None
    # Data-cell colspans. Maps (row_idx, col_idx) -> colspan. Cells covered
    # to the right of a spanned anchor stay in `data_rows` with empty text;
    # they're skipped by the renderer and GT emitter.
    col_spans: dict = None
    # Compact mode: use tighter row heights so more rows fit per page.
    # Used by dense/full-page tables.
    compact_rows: bool = False

    def __post_init__(self):
        if self.row_spans is None:
            self.row_spans = {}
        if self.col_spans is None:
            self.col_spans = {}


_TEXT_TYPES = ["text", "label"]
_NUMERIC_TYPES = [
    "int",
    "float",
    "percent",
    "pvalue",
    "year",
    "money",
    "range",
    "plusminus",
    "ratio",
]
_ALL_TYPES = _TEXT_TYPES + _NUMERIC_TYPES
_NUMERIC_AGGREGATABLE = {"int", "float", "percent", "money"}
# Short cell renders (≤6 chars): used in wide tables to avoid ellipsis.
_NUMERIC_COMPACT = ["int", "year", "percent", "pvalue", "ratio"]
