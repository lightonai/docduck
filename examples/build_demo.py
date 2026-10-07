#!/usr/bin/env python3
"""Regenerate the demo images under examples/images/.

Two outputs, one PNG each (no grids, no post-processing):

- demo_page.png    a rendered page (2-column composition)
- demo_table.png   a rendered table block (dense, block-registry call)
"""

import io
import random
from pathlib import Path

import cairo
from PIL import Image

from docduck import fonts as fonts_mod
from docduck.table import gen as table_gen
from docduck.blocks._registry import blocks
from docduck.composer import compose_page
from docduck.page_config import PageConfig
from docduck.table.gen import (
    _CELL_GENERATORS,
    _NUMERIC_COMPACT,
    _distinct_label,
    _gen_label,
    _sample_short_header,
    HeaderCell,
    TableSpec,
)

OUT = Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

MAX_W = 1200


def save(surface, name):
    buf = io.BytesIO()
    surface.write_to_png(buf)
    buf.seek(0)
    pil = Image.open(buf).convert("RGB")
    if pil.width > MAX_W:
        pil = pil.resize((MAX_W, int(pil.height * MAX_W / pil.width)), Image.LANCZOS)
    path = OUT / name
    pil.save(path, optimize=True)
    return path


# 1. Rich 2-column composition
cfg = PageConfig(lang="en", complexity="high", seed=42, n_columns=2)
surface, *_ = compose_page(page_config=cfg)
save(surface, "demo_page.png")

# 2. Complex pivot: 2-level colspan headers + 2-level rowspan row-groups.
def big_pivot(lang="en") -> TableSpec:
    n_outer = 4               # outer row-groups (rowspan on col 0)
    inner_per_outer = 3       # inner row-groups per outer (rowspan on col 1)
    leaves_per_inner = 3      # leaf rows per inner → 36 data rows
    n_top_cols = 3            # top header groups (colspan on row 0)
    sub_per_top = 2           # sub-groups per top (colspan on row 1)
    metrics = 2               # leaf metrics per sub

    n_leaves = n_top_cols * sub_per_top * metrics  # 12 data columns
    n_cols = 2 + n_leaves

    top_row = [HeaderCell("", colspan=2)]
    for _ in range(n_top_cols):
        top_row.append(
            HeaderCell(_sample_short_header(lang, "label", max_chars=10),
                       colspan=sub_per_top * metrics)
        )

    mid_row = [HeaderCell("", colspan=2)]
    for _ in range(n_top_cols * sub_per_top):
        mid_row.append(
            HeaderCell(_sample_short_header(lang, "label", max_chars=8),
                       colspan=metrics)
        )

    metric_types = random.sample(_NUMERIC_COMPACT, metrics)
    leaf_headers = [_sample_short_header(lang, ct, max_chars=7) for ct in metric_types]
    bot_row = [
        HeaderCell(_sample_short_header(lang, "label", max_chars=10)),
        HeaderCell(_sample_short_header(lang, "label", max_chars=10)),
    ]
    generators = []
    for _ in range(n_top_cols * sub_per_top):
        for i, ct in enumerate(metric_types):
            bot_row.append(HeaderCell(leaf_headers[i]))
            generators.append(_CELL_GENERATORS[ct])

    data_rows = []
    row_spans = {}
    used_outer = set()
    for _ in range(n_outer):
        outer = _distinct_label(lang, used_outer); used_outer.add(outer)
        outer_start = len(data_rows)
        used_inner = set()
        for _ in range(inner_per_outer):
            inner = _distinct_label(lang, used_inner); used_inner.add(inner)
            inner_start = len(data_rows)
            for _ in range(leaves_per_inner):
                data_rows.append(["", "", *[g(lang) for g in generators]])
            data_rows[inner_start][1] = inner
            row_spans[(inner_start, 1)] = leaves_per_inner
        data_rows[outer_start][0] = outer
        row_spans[(outer_start, 0)] = inner_per_outer * leaves_per_inner

    return TableSpec(
        caption="",
        header_rows=[top_row, mid_row, bot_row],
        data_rows=data_rows,
        n_cols=n_cols,
        has_row_headers=True,
        row_spans=row_spans,
        style="grid",
    )


table_gen.gen_table = lambda lang=None: big_pivot(lang or "en")
random.seed(7)
W, H = 2000, 2200
table_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(table_surface)
ctx.set_source_rgb(1, 1, 1)
ctx.paint()
blocks.get("table")(
    ctx, x=60, y=60, width=W - 120,
    text_color=(0, 0, 0),
    accent_color=(0.3, 0.3, 0.6),
    style=None,
    fonts=fonts_mod.FontPalette(),
    lang="en",
)
save(table_surface, "demo_table.png")

for p in sorted(OUT.iterdir()):
    if p.suffix == ".png":
        print(f"{p.name:30s} {p.stat().st_size / 1024:6.0f} KB")
