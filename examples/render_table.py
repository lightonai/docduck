#!/usr/bin/env python3
"""Render a standalone complex table: colspan headers + rowspan row-groups.

Shows how to drive a single block from the registry instead of composing a
whole page, and how to pin a specific table structure. `table_gen` ships
~10 structure generators (dense, pivot, grouped_header, nested_rowspan,
deep_header, matrix, …); override `table_gen.gen_table` to choose one.
"""

import random
from pathlib import Path

import cairo

from docduck import fonts as fonts_mod
from docduck.table import gen as table_gen
from docduck.blocks._registry import blocks

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Pin the pivot generator: nested colspan headers + outer-row rowspan.
table_gen.gen_table = lambda lang=None: table_gen.gen_pivot_table(lang=lang)

random.seed(7)
W, H = 1700, 1400
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surface)
ctx.set_source_rgb(1, 1, 1); ctx.paint()

result = blocks.get("table")(
    ctx, x=60, y=60, width=W - 120,
    text_color=(0, 0, 0),
    accent_color=(0.3, 0.3, 0.6),
    style=None,
    fonts=fonts_mod.FontPalette(),
    lang="en",
)

surface.write_to_png(str(OUT / "table.png"))
(OUT / "table.gt.md").write_text(result.text)
print(f"table: height={result.height}px, <tr>={result.text.count('<tr>')}, gt_chars={len(result.text)}")
