"""Procedural table data generator.

Produces diverse table structures with Markov-sampled localized headers
and cell text. Everything configurable lives in defaults["table"].

Generator types:
    simple, standard, wide, tall, grouped_header, sparse,
    single_column, key_value, hierarchical, indexed, deep_header,
    nested_rowspan, matrix, pivot, irregular, dense
"""

from .dispatch import _GENERATORS, _maybe_add_summary_row, gen_table
from .generators_basic import (
    _build_columns,
    _pick_column_types,
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
from .headers import _sample_header, _sample_short_header
from .types import (
    _ALL_TYPES,
    _NUMERIC_AGGREGATABLE,
    _NUMERIC_COMPACT,
    _NUMERIC_TYPES,
    _TEXT_TYPES,
    HeaderCell,
    TableSpec,
)
from .words import (
    _CELL_GENERATORS,
    _STOPWORDS,
    _distinct_label,
    _gen_float,
    _gen_int,
    _gen_label,
    _gen_money,
    _gen_percent,
    _gen_plusminus,
    _gen_pvalue,
    _gen_range,
    _gen_ratio,
    _gen_short_label,
    _gen_word,
    _gen_year,
    _get_word_pool,
    _sample_phrase,
    _sample_word,
    _word_pools,
)

__all__ = [
    # Types
    "HeaderCell",
    "TableSpec",
    "_ALL_TYPES",
    "_TEXT_TYPES",
    "_NUMERIC_TYPES",
    "_NUMERIC_AGGREGATABLE",
    "_NUMERIC_COMPACT",
    # Words
    "_STOPWORDS",
    "_word_pools",
    "_get_word_pool",
    "_sample_word",
    "_sample_phrase",
    "_gen_word",
    "_gen_label",
    "_gen_short_label",
    "_distinct_label",
    "_gen_int",
    "_gen_float",
    "_gen_percent",
    "_gen_pvalue",
    "_gen_year",
    "_gen_money",
    "_gen_range",
    "_gen_plusminus",
    "_gen_ratio",
    "_CELL_GENERATORS",
    # Headers
    "_sample_header",
    "_sample_short_header",
    # Generators
    "_pick_column_types",
    "_build_columns",
    "gen_simple_table",
    "gen_standard_table",
    "gen_wide_table",
    "gen_tall_table",
    "gen_sparse_table",
    "gen_single_column_table",
    "gen_key_value_table",
    "gen_indexed_table",
    "gen_grouped_header_table",
    "gen_hierarchical_table",
    "gen_deep_header_table",
    "gen_nested_rowspan_table",
    "gen_matrix_table",
    "gen_pivot_table",
    "gen_irregular_table",
    "gen_dense_table",
    # Dispatch
    "_GENERATORS",
    "_maybe_add_summary_row",
    "gen_table",
]
