"""Top-level table generator: weighted dispatch over the per-shape generators,
plus optional summary-row augmentation and caption fill-in."""

import random

from ...defaults import DEFAULTS
from ...gen_context import GenContext
from .generators_basic import (
    gen_indexed_table,
    gen_key_value_table,
    gen_simple_table,
    gen_single_column_table,
    gen_sparse_table,
    gen_standard_table,
    gen_tall_table,
    gen_wide_table,
)
from .generators_complex import (
    gen_deep_header_table,
    gen_dense_table,
    gen_grouped_header_table,
    gen_hierarchical_table,
    gen_irregular_table,
    gen_matrix_table,
    gen_nested_rowspan_table,
    gen_pivot_table,
)
from .types import TableSpec
from .words import _sample_phrase


def _maybe_add_summary_row(lang, spec: TableSpec) -> TableSpec:
    """Append a totals/average row to spec.data_rows if the columns support it."""
    if not spec.data_rows or spec.n_cols < 2:
        return spec

    # Find a numeric-aggregatable column (skip index 0, usually text/label)
    summary_label = _sample_phrase(lang, n_words=1, max_chars=10) or "Total"
    new_row = [summary_label] + [""] * (spec.n_cols - 1)

    for ci in range(1, spec.n_cols):
        values = []
        for row in spec.data_rows:
            if ci < len(row):
                cell = row[ci]
                if not cell or cell in ("—", "…", "N/A"):
                    continue
                # Extract a number if present
                import re

                m = re.search(r"-?\d+\.?\d*", cell.replace(",", ""))
                if m:
                    try:
                        values.append(float(m.group()))
                    except ValueError:
                        pass
        if values:
            total = sum(values)
            # Format to match the first data cell's style
            sample = next(
                (
                    r[ci]
                    for r in spec.data_rows
                    if ci < len(r) and r[ci] not in ("", "—", "…", "N/A")
                ),
                "",
            )
            if "$" in sample:
                new_row[ci] = f"${total:,.0f}"
            elif "%" in sample:
                new_row[ci] = f"{total / len(values):.1f}%"
            elif "." in sample:
                new_row[ci] = f"{total:.2f}"
            else:
                new_row[ci] = str(int(total))

    spec.data_rows = list(spec.data_rows) + [new_row]
    return spec


_GENERATORS = {
    "simple": gen_simple_table,
    "standard": gen_standard_table,
    "wide": gen_wide_table,
    "tall": gen_tall_table,
    "grouped_header": gen_grouped_header_table,
    "sparse": gen_sparse_table,
    "single_column": gen_single_column_table,
    "key_value": gen_key_value_table,
    "hierarchical": gen_hierarchical_table,
    "indexed": gen_indexed_table,
    "deep_header": gen_deep_header_table,
    "nested_rowspan": gen_nested_rowspan_table,
    "matrix": gen_matrix_table,
    "pivot": gen_pivot_table,
    "irregular": gen_irregular_table,
    "dense": gen_dense_table,
}


def gen_table(lang: str = None, ctx: GenContext | None = None) -> TableSpec:
    """Generate a random table with structure drawn from configured weights.

    Either `lang` or `ctx` (a `GenContext`) may be provided; `ctx` wins if both.
    """
    if ctx is not None:
        lang = ctx.lang

    from ...generators import text as text_gen

    cfg = DEFAULTS["table"]
    weight_map = cfg["generator_weights"]
    names = list(weight_map.keys())
    weights = [weight_map[n] for n in names]
    gen_name = random.choices(names, weights=weights, k=1)[0]
    spec = _GENERATORS[gen_name](lang)

    # Optionally augment with a summary row (skip hierarchical/indexed to avoid confusion)
    if gen_name not in (
        "hierarchical",
        "indexed",
        "key_value",
        "single_column",
        "nested_rowspan",
        "pivot",
        "irregular",
        "dense",
    ):
        if random.random() < cfg["summary_row_probability"]:
            spec = _maybe_add_summary_row(lang, spec)

    if not spec.caption:
        spec.caption = text_gen.gen_heading(lang=lang)

    if spec.style is None:
        spec.style = random.choice(cfg["styles"])

    return spec
