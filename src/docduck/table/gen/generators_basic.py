"""Generators for the flat / single-header-row table shapes:
simple, standard, wide, tall, sparse, single_column, key_value, indexed."""

import random

from .headers import _sample_header
from .types import _ALL_TYPES, _TEXT_TYPES, HeaderCell, TableSpec
from .words import (
    _CELL_GENERATORS,
    _gen_float,
    _gen_int,
    _gen_label,
    _gen_money,
    _gen_percent,
    _gen_word,
    _gen_year,
    _sample_phrase,
)


def _pick_column_types(n_cols):
    """Pick n_cols column types, with the first typically text-like."""
    types = []
    if random.random() < 0.8:
        types.append(random.choice(_TEXT_TYPES))
    else:
        types.append(random.choice(_ALL_TYPES))
    for _ in range(n_cols - 1):
        types.append(random.choice(_ALL_TYPES))
    return types


def _build_columns(lang, col_types):
    """Build (headers, generators) from a list of column types."""
    headers = [_sample_header(lang, ct) for ct in col_types]
    generators = [_CELL_GENERATORS[ct] for ct in col_types]
    return headers, generators


def gen_simple_table(lang=None) -> TableSpec:
    """Simple flat table: 1-3 columns, 1-5 rows."""
    n_cols = random.randint(1, 3)
    n_rows = random.randint(1, 5)
    col_types = _pick_column_types(n_cols)
    headers, generators = _build_columns(lang, col_types)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=[[gen(lang) for gen in generators] for _ in range(n_rows)],
        n_cols=n_cols,
    )


def gen_standard_table(lang=None) -> TableSpec:
    """Standard table: 3-6 columns, 4-12 rows. May have empty cells."""
    n_cols = random.randint(3, 6)
    n_rows = random.randint(4, 12)
    col_types = _pick_column_types(n_cols)
    headers, generators = _build_columns(lang, col_types)
    empty_prob = random.uniform(0, 0.15)

    data_rows = []
    for _ in range(n_rows):
        row = []
        for gen in generators:
            if random.random() < empty_prob:
                row.append(random.choice(["", "—", "N/A"]))
            else:
                row.append(gen(lang))
        data_rows.append(row)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=random.random() < 0.3,
    )


def gen_wide_table(lang=None) -> TableSpec:
    """Wide table: 6-10 columns, 3-8 rows. Compact numeric data."""
    n_cols = random.randint(6, 10)
    n_rows = random.randint(3, 8)
    col_types = _pick_column_types(n_cols)
    headers, generators = _build_columns(lang, col_types)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=[[gen(lang) for gen in generators] for _ in range(n_rows)],
        n_cols=n_cols,
    )


def gen_tall_table(lang=None) -> TableSpec:
    """Tall table: 2-4 columns, 10-20 rows."""
    n_cols = random.randint(2, 4)
    n_rows = random.randint(10, 20)
    col_types = _pick_column_types(n_cols)
    headers, generators = _build_columns(lang, col_types)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=[[gen(lang) for gen in generators] for _ in range(n_rows)],
        n_cols=n_cols,
        has_row_headers=True,
    )


def gen_sparse_table(lang=None) -> TableSpec:
    """Table with many empty cells (sparse data)."""
    n_cols = random.randint(3, 7)
    n_rows = random.randint(5, 12)
    col_types = _pick_column_types(n_cols)
    headers, generators = _build_columns(lang, col_types)
    empty_prob = random.uniform(0.2, 0.5)

    data_rows = []
    for _ in range(n_rows):
        # Build a row; ensure at least one non-empty cell so the row is visible
        # (fully-empty rows are indistinguishable from row padding and break
        # image/GT fidelity).
        row = []
        for ci, gen in enumerate(generators):
            if ci == 0:
                row.append(gen(lang))
            elif random.random() < empty_prob:
                row.append(random.choice(["", "—", "…"]))
            else:
                row.append(gen(lang))
        data_rows.append(row)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=data_rows,
        n_cols=n_cols,
    )


def gen_single_column_table(lang=None) -> TableSpec:
    """Single-column list-like table."""
    n_rows = random.randint(3, 10)
    ct = random.choice(_TEXT_TYPES)
    header = _sample_header(lang, ct)
    gen = _CELL_GENERATORS[ct]

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(header)]],
        data_rows=[[gen(lang)] for _ in range(n_rows)],
        n_cols=1,
    )


def gen_key_value_table(lang=None) -> TableSpec:
    """Two-column key-value table (like a specification sheet)."""
    n_rows = random.randint(4, 12)

    # Keys come from Markov; values mix different generators
    keys = [_gen_label(lang) for _ in range(n_rows)]
    value_pool = [_gen_float, _gen_int, _gen_percent, _gen_year, _gen_money, _gen_word]
    data_rows = [[k, random.choice(value_pool)(lang)] for k in keys]

    # "Property" / "Value" headers in target lang
    key_header = _sample_phrase(lang, n_words=1, max_chars=15) or "Property"
    val_header = _sample_phrase(lang, n_words=1, max_chars=15) or "Value"

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(key_header), HeaderCell(val_header)]],
        data_rows=data_rows,
        n_cols=2,
        has_row_headers=True,
    )


def gen_indexed_table(lang=None) -> TableSpec:
    """Table with a numeric/hierarchical index as the first column.

    Uses hierarchical numbering like 1., 1.1, 1.2, 2., 2.1, ... so the
    index column reads like a TOC/outline.
    """
    n_cols = random.randint(2, 5)
    n_sections = random.randint(2, 4)
    subs_per_section = random.randint(2, 4)

    # Data columns after the index
    data_types = [random.choice(_ALL_TYPES) for _ in range(n_cols - 1)]
    data_generators = [_CELL_GENERATORS[ct] for ct in data_types]

    index_header = _sample_phrase(lang, n_words=1, max_chars=8) or "§"
    data_headers = [_sample_header(lang, ct) for ct in data_types]
    header_cells = [HeaderCell(index_header)] + [HeaderCell(h) for h in data_headers]

    data_rows = []
    for s in range(1, n_sections + 1):
        # Section row
        data_rows.append([f"{s}.", _gen_label(lang)] + [gen(lang) for gen in data_generators[1:]])
        for sub in range(1, subs_per_section + 1):
            row_values = [gen(lang) for gen in data_generators]
            data_rows.append([f"{s}.{sub}"] + row_values)

    return TableSpec(
        caption="",
        header_rows=[header_cells],
        data_rows=data_rows,
        n_cols=n_cols,
    )
