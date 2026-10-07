"""Generators for the multi-header / span-heavy table shapes:
grouped_header, hierarchical, deep_header, nested_rowspan, matrix, pivot,
irregular, dense."""

import random

from .headers import _sample_header, _sample_short_header
from .types import _ALL_TYPES, _NUMERIC_COMPACT, _TEXT_TYPES, HeaderCell, TableSpec
from .words import (
    _CELL_GENERATORS,
    _distinct_label,
    _gen_label,
    _gen_short_label,
    _sample_phrase,
)


def gen_grouped_header_table(lang=None) -> TableSpec:
    """Table with multi-level headers (column groups spanning columns)."""
    n_groups = random.randint(2, 3)
    groups = []

    for _ in range(n_groups):
        # Group name sampled from Markov
        group_name = _sample_phrase(lang, n_words=2, max_chars=18) or "Group"
        n_sub = 2
        sub_types = random.sample(
            ["float", "percent", "int", "pvalue", "plusminus", "range", "money"],
            n_sub,
        )
        group_cols = [(ct, _sample_header(lang, ct), _CELL_GENERATORS[ct]) for ct in sub_types]
        groups.append((group_name, group_cols))

    # Optional leading text column
    has_label = random.random() < 0.7
    top_row, bottom_row, generators = [], [], []

    if has_label:
        label_type = random.choice(_TEXT_TYPES)
        top_row.append(HeaderCell("", colspan=1))
        bottom_row.append(HeaderCell(_sample_header(lang, label_type)))
        generators.append(_CELL_GENERATORS[label_type])

    for gname, gcols in groups:
        top_row.append(HeaderCell(gname, colspan=len(gcols)))
        for _, hdr, gen in gcols:
            bottom_row.append(HeaderCell(hdr))
            generators.append(gen)

    n_cols = len(bottom_row)
    n_rows = random.randint(4, 10)
    data_rows = [[gen(lang) for gen in generators] for _ in range(n_rows)]

    return TableSpec(
        caption="",
        header_rows=[top_row, bottom_row],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=has_label,
    )


def gen_hierarchical_table(lang=None) -> TableSpec:
    """Table with row groups: first column spans the group label with rowspan.

    Produces a visual hierarchy like:
        Group A | sub 1 | ...
                | sub 2 | ...
        Group B | sub 1 | ...
                | sub 2 | ...
    The group label cell has `rowspan=rows_per_group`; covered rows below
    are stored as empty strings and skipped by the renderer + GT emitter.
    """
    n_groups = random.randint(2, 4)
    rows_per_group = random.randint(2, 4)

    n_data_cols = random.randint(2, 4)
    data_col_types = [random.choice(_ALL_TYPES) for _ in range(n_data_cols)]
    data_generators = [_CELL_GENERATORS[ct] for ct in data_col_types]

    group_header = _sample_header(lang, "label")
    sub_header = _sample_header(lang, "label")
    data_headers = [_sample_header(lang, ct) for ct in data_col_types]

    header_cells = [HeaderCell(group_header), HeaderCell(sub_header)] + [
        HeaderCell(h) for h in data_headers
    ]

    data_rows: list[list[str]] = []
    row_spans: dict = {}
    used_groups: set[str] = set()
    for g in range(n_groups):
        group_label = _distinct_label(lang, used_groups)
        used_groups.add(group_label)
        group_start_row = len(data_rows)
        for i in range(rows_per_group):
            sub_label = _gen_label(lang)
            values = [gen(lang) for gen in data_generators]
            first_col = group_label if i == 0 else ""  # covered rows blank
            data_rows.append([first_col, sub_label] + values)
        row_spans[(group_start_row, 0)] = rows_per_group

    return TableSpec(
        caption="",
        header_rows=[header_cells],
        data_rows=data_rows,
        n_cols=2 + n_data_cols,
        has_row_headers=True,
        row_spans=row_spans,
        style="grid",
    )


def gen_deep_header_table(lang=None) -> TableSpec:
    """Three header rows: two levels of column grouping nested over leaves.

    N top-level groups × M sub-groups × 2 leaf columns. Uses compact numeric
    types (int/year/percent/pvalue) and single-word headers so cells stay
    legible at 6-9 columns wide.
    """
    # 2 top × 2 sub × 2 leaf = 8 columns: enough to show the nested structure
    # while leaving each column wide enough to avoid ellipsis at page width.
    n_top = 2
    subs_per_top = 2
    leaves_per_sub = 2

    top_row: list[HeaderCell] = []
    mid_row: list[HeaderCell] = []
    bot_row: list[HeaderCell] = []
    generators: list = []

    for _ in range(n_top):
        top_name = _sample_phrase(lang, n_words=1, max_chars=10) or "Group"
        top_row.append(HeaderCell(top_name, colspan=subs_per_top * leaves_per_sub))
        for _ in range(subs_per_top):
            sub_name = _sample_phrase(lang, n_words=1, max_chars=10) or "Sub"
            mid_row.append(HeaderCell(sub_name, colspan=leaves_per_sub))
            sub_types = random.sample(_NUMERIC_COMPACT, leaves_per_sub)
            for ct in sub_types:
                bot_row.append(HeaderCell(_sample_short_header(lang, ct, max_chars=8)))
                generators.append(_CELL_GENERATORS[ct])

    has_label = random.random() < 0.7
    if has_label:
        top_row.insert(0, HeaderCell("", colspan=1))
        mid_row.insert(0, HeaderCell("", colspan=1))
        bot_row.insert(0, HeaderCell(_sample_short_header(lang, "label", max_chars=10)))
        generators.insert(0, lambda lg: _gen_short_label(lg, max_chars=10))

    n_cols = len(bot_row)
    n_rows = random.randint(5, 10)
    data_rows = [[gen(lang) for gen in generators] for _ in range(n_rows)]

    return TableSpec(
        caption="",
        header_rows=[top_row, mid_row, bot_row],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=has_label,
    )


def gen_nested_rowspan_table(lang=None) -> TableSpec:
    """Two levels of row grouping: outer groups contain inner groups contain leaves.

    Column 0 holds the outer-group label (rowspan = inner_per_outer * leaves_per_inner).
    Column 1 holds the inner-group label (rowspan = leaves_per_inner).
    Column 2 holds the leaf label. Remaining columns are numeric data.
    """
    n_outer = random.randint(2, 3)
    inner_per_outer = random.randint(2, 3)
    leaves_per_inner = random.randint(2, 3)
    outer_span = inner_per_outer * leaves_per_inner

    n_data_cols = random.randint(2, 4)
    data_col_types = [random.choice(_NUMERIC_COMPACT) for _ in range(n_data_cols)]
    data_generators = [_CELL_GENERATORS[ct] for ct in data_col_types]

    outer_header = _sample_short_header(lang, "label", max_chars=12)
    inner_header = _sample_short_header(lang, "label", max_chars=12)
    leaf_header = _sample_short_header(lang, "label", max_chars=12)
    data_headers = [_sample_short_header(lang, ct, max_chars=10) for ct in data_col_types]
    header_cells = [
        HeaderCell(outer_header),
        HeaderCell(inner_header),
        HeaderCell(leaf_header),
    ] + [HeaderCell(h) for h in data_headers]

    data_rows: list[list[str]] = []
    row_spans: dict = {}

    used_outer: set[str] = set()
    for _ in range(n_outer):
        outer_label = _distinct_label(lang, used_outer)
        used_outer.add(outer_label)
        outer_start = len(data_rows)
        used_inner: set[str] = set()
        for j in range(inner_per_outer):
            inner_label = _distinct_label(lang, used_inner)
            used_inner.add(inner_label)
            inner_start = len(data_rows)
            for k in range(leaves_per_inner):
                leaf = _gen_label(lang)
                values = [gen(lang) for gen in data_generators]
                col0 = outer_label if (j == 0 and k == 0) else ""
                col1 = inner_label if k == 0 else ""
                data_rows.append([col0, col1, leaf] + values)
            row_spans[(inner_start, 1)] = leaves_per_inner
        row_spans[(outer_start, 0)] = outer_span

    return TableSpec(
        caption="",
        header_rows=[header_cells],
        data_rows=data_rows,
        n_cols=3 + n_data_cols,
        has_row_headers=True,
        row_spans=row_spans,
        # `grid` draws hlines between every data row: essential for nested
        # rowspans to read correctly (without it adjacent empty cells from
        # different row groups are visually indistinguishable).
        style="grid",
    )


def gen_dense_table(lang=None) -> TableSpec:
    """Dense table at ~200 cells: denser than `matrix` but within the OCR
    endpoint's output-token budget at 200 DPI.

    Earlier we ran 10-14 cols × 40-55 rows ≈ 540 cells; the Paradigm OCR
    endpoint capped at ~25 rows / ~7k chars regardless of how many we sent
    (VLM image×output context tradeoff, not structural difficulty). Scaled
    back to 8-11 cols × 20-26 rows ≈ 200 cells so the whole table fits in
    the budget and we actually measure reading quality, not truncation.
    """
    n_cols = random.randint(8, 11)
    n_rows = random.randint(20, 26)
    has_label = random.random() < 0.6
    # Narrowest types only: percent has a 4-char " (%)" suffix on the
    # header that busts the budget at 14 cols; skip it for dense.
    narrow_types = ["int", "year", "pvalue", "ratio"]
    first_type = "label" if has_label else random.choice(narrow_types)
    rest_types = [random.choice(narrow_types) for _ in range(n_cols - 1)]
    col_types = [first_type] + rest_types

    headers = [_sample_short_header(lang, ct, max_chars=6) for ct in col_types]
    generators = [
        (lambda lg: _gen_short_label(lg, max_chars=6)) if ct == "label" else _CELL_GENERATORS[ct]
        for ct in col_types
    ]

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=[[g(lang) for g in generators] for _ in range(n_rows)],
        n_cols=n_cols,
        has_row_headers=has_label,
        style="grid",
        compact_rows=True,
    )


def gen_matrix_table(lang=None) -> TableSpec:
    """Large plain grid: 6-10 columns, 15-25 rows.

    Uses compact numeric types + a label column so cells stay legible at scale.
    """
    n_cols = random.randint(6, 10)
    n_rows = random.randint(15, 25)
    has_label = random.random() < 0.7
    first_type = "label" if has_label else random.choice(_NUMERIC_COMPACT)
    rest_types = [random.choice(_NUMERIC_COMPACT) for _ in range(n_cols - 1)]
    col_types = [first_type] + rest_types

    headers = [_sample_short_header(lang, ct, max_chars=9) for ct in col_types]
    generators = [
        (lambda lg: _gen_short_label(lg, max_chars=10)) if ct == "label" else _CELL_GENERATORS[ct]
        for ct in col_types
    ]

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=[[gen(lang) for gen in generators] for _ in range(n_rows)],
        n_cols=n_cols,
        has_row_headers=has_label,
    )


def gen_irregular_table(lang=None) -> TableSpec:
    """Irregular table: breaks the rectangular-grid assumption on purpose.

    Combines three structural irregularities that commonly trip up OCR:
      1. Full-width section divider rows (colspan = n_cols).
      2. Subtotal rows with a partial colspan (col 0 spans 2-3 cols, then
         numeric cells fill the rest).
      3. An interior-column rowspan on col 1 (not col 0) covering 2 rows
         inside a section, creating a shared-value block not at the edge.

    Style is forced to `minimal` so only top/bottom rules exist; v-lines
    would have to constantly break around the colspans.
    """
    n_cols = random.randint(5, 6)
    col_types = (
        ["label"]
        + [random.choice(["label"] + _NUMERIC_COMPACT)]
        + [random.choice(_NUMERIC_COMPACT) for _ in range(n_cols - 2)]
    )
    headers = [_sample_short_header(lang, ct, max_chars=9) for ct in col_types]
    generators = [
        (lambda lg: _gen_short_label(lg, max_chars=11)) if ct == "label" else _CELL_GENERATORS[ct]
        for ct in col_types
    ]

    n_sections = random.randint(2, 3)
    rows_per_section = random.randint(3, 4)

    data_rows: list[list[str]] = []
    col_spans: dict = {}
    row_spans: dict = {}

    for s in range(n_sections):
        # 1) Full-width section divider
        divider = f"— {_gen_short_label(lang, max_chars=12).title()} —"
        col_spans[(len(data_rows), 0)] = n_cols
        data_rows.append([divider] + [""] * (n_cols - 1))

        # 2) Normal rows, with an interior rowspan on col 1 for the first
        #    two rows of every other section.
        section_start = len(data_rows)
        for i in range(rows_per_section):
            row = [g(lang) for g in generators]
            data_rows.append(row)

        if s % 2 == 0 and rows_per_section >= 2 and col_types[1] == "label":
            # Blank the 2nd row's col-1 cell; the 1st row's col-1 rowspans 2.
            row_spans[(section_start, 1)] = 2
            data_rows[section_start + 1][1] = ""

        # 3) Partial-width subtotal row: col 0 spans (n_cols - 2) cols
        #    with a label; remaining 2 cols carry numeric summaries.
        span = n_cols - 2
        label = _sample_phrase(lang, n_words=1, max_chars=10) or "Subtotal"
        sub_row: list[str] = [label] + [""] * (span - 1)
        for ct in col_types[span:]:
            sub_row.append(_CELL_GENERATORS[ct](lang))
        col_spans[(len(data_rows), 0)] = span
        data_rows.append(sub_row)

    return TableSpec(
        caption="",
        header_rows=[[HeaderCell(h) for h in headers]],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=True,
        row_spans=row_spans,
        col_spans=col_spans,
        style="minimal",
    )


def gen_pivot_table(lang=None) -> TableSpec:
    """Pivot table: 3 header rows × nested rowspan on outer-label column.

    Combines 2 levels of nested colspan (top groups → sub-groups → metrics)
    with rowspan on column 0 (outer row groups).

    Cols: 2 label + (2 top × 2 sub × 2 metrics) = 10.
    Rows: n_outer × inner_per_outer; outer col has rowspan=inner_per_outer.
    """
    n_outer_rows = 2
    inner_per_outer = random.randint(2, 3)
    n_top_cols = 2
    sub_per_top = 2
    metrics_per_sub = 2
    n_leaves = n_top_cols * sub_per_top * metrics_per_sub  # 8
    n_cols = 2 + n_leaves  # 10

    # Row 1: [blank spans label cols, top-1 (cs=4), top-2 (cs=4)]
    top_row: list[HeaderCell] = [HeaderCell("", colspan=2)]
    for _ in range(n_top_cols):
        top_row.append(
            HeaderCell(
                _sample_short_header(lang, "label", max_chars=10),
                colspan=sub_per_top * metrics_per_sub,
            )
        )

    # Row 2: [blank cs=2, sub × (n_top × sub_per_top)]
    mid_row: list[HeaderCell] = [HeaderCell("", colspan=2)]
    for _ in range(n_top_cols * sub_per_top):
        mid_row.append(
            HeaderCell(
                _sample_short_header(lang, "label", max_chars=8),
                colspan=metrics_per_sub,
            )
        )

    # Row 3: [row-outer, row-inner, leaf × n_leaves]
    bot_row: list[HeaderCell] = [
        HeaderCell(_sample_short_header(lang, "label", max_chars=10)),
        HeaderCell(_sample_short_header(lang, "label", max_chars=10)),
    ]
    metric_types = random.sample(_NUMERIC_COMPACT, metrics_per_sub)
    leaf_headers = [_sample_short_header(lang, ct, max_chars=7) for ct in metric_types]
    generators: list = []
    for _ in range(n_top_cols * sub_per_top):
        for i, ct in enumerate(metric_types):
            bot_row.append(HeaderCell(leaf_headers[i]))
            generators.append(_CELL_GENERATORS[ct])

    data_rows: list[list[str]] = []
    row_spans: dict = {}
    used_outer: set[str] = set()
    for _ in range(n_outer_rows):
        outer_label = _distinct_label(lang, used_outer)
        used_outer.add(outer_label)
        outer_start = len(data_rows)
        for i in range(inner_per_outer):
            inner_label = _gen_short_label(lang, max_chars=10)
            values = [g(lang) for g in generators]
            col0 = outer_label if i == 0 else ""
            data_rows.append([col0, inner_label] + values)
        row_spans[(outer_start, 0)] = inner_per_outer

    return TableSpec(
        caption="",
        header_rows=[top_row, mid_row, bot_row],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=True,
        row_spans=row_spans,
        style="grid",
    )
