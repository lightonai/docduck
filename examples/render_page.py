#!/usr/bin/env python3
"""Generate a full training sample: page PNG + markdown GT + bbox JSON.

This is the core output docduck produces: a rendered page paired with
both a text transcript and per-block bounding boxes. Batch this at scale
with `python3 -m docduck.cli.generate -n 1000 -o output/`.
"""

import json
from pathlib import Path

from docduck.composer import compose_page
from docduck.page_config import PageConfig

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

cfg = PageConfig(lang="en", complexity="medium", seed=42)
surface, annotations, _, text = compose_page(page_config=cfg)

surface.write_to_png(str(OUT / "page.png"))
(OUT / "page.gt.md").write_text(text)
(OUT / "page.bboxes.json").write_text(json.dumps(annotations, indent=2))

print(f"{len(annotations)} blocks: {sum(1 for a in annotations if a['text'])} with text GT")
for a in annotations:
    b = a["bbox"]
    print(f"  {a['block_type']:<10} bbox=({b['x']:>4},{b['y']:>4},{b['width']:>4}x{b['height']:>4})")
