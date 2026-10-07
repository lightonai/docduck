#!/usr/bin/env python3
"""Draw block bounding boxes over generated pages.

Reads ``metadata.json`` from a ``docduck`` run and writes a ``<page>_boxes.png``
next to each page image, outlining every block (and chrome region) with a
label. Useful for inspecting layout and ground-truth geometry.

Usage:
    python examples/render_boxes.py output/metadata.json
    python examples/render_boxes.py output/metadata.json --index 6
"""

import argparse
import json
from pathlib import Path

import cairo

BLOCK_RGBA = (0.85, 0.12, 0.10, 0.95)
CHROME_RGBA = (0.12, 0.38, 0.90, 0.95)


def overlay(png_path: Path, annotations: list, logical_w: float, logical_h: float, out_path: Path):
    surface = cairo.ImageSurface.create_from_png(str(png_path))
    ctx = cairo.Context(surface)
    sx = surface.get_width() / logical_w
    sy = surface.get_height() / logical_h
    line_w = max(2.0, 2.5 * sx)
    font_size = max(12.0, 11.0 * sx)
    pad = max(2.0, 3.0 * sx)

    for ann in annotations:
        b = ann.get("bbox")
        if not b:
            continue
        x, y = b["x"] * sx, b["y"] * sy
        w, h = b["width"] * sx, b["height"] * sy
        chrome = str(ann.get("block_type", "")).startswith("chrome:")
        color = CHROME_RGBA if chrome else BLOCK_RGBA

        ctx.set_source_rgba(*color)
        ctx.set_line_width(line_w)
        if chrome:
            ctx.set_dash([6 * sx, 4 * sx])
        else:
            ctx.set_dash([])
        ctx.rectangle(x, y, w, h)
        ctx.stroke()

        label = str(ann.get("block_type", ""))
        if label:
            ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(font_size)
            ext = ctx.text_extents(label)
            box_w = ext.width + 2 * pad
            box_h = ext.height + 2 * pad
            ly = y - box_h - 2
            if ly < 2:
                ly = y + 1
            ctx.set_dash([])
            ctx.set_source_rgba(*color)
            ctx.rectangle(x, ly, box_w, box_h)
            ctx.fill()
            ctx.set_source_rgba(1, 1, 1, 1)
            ctx.move_to(x + pad, ly + ext.height + pad)
            ctx.show_text(label)

    surface.write_to_png(str(out_path))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("metadata", help="Path to metadata.json from a docduck run")
    ap.add_argument("--index", type=int, default=None, help="Only this page index")
    args = ap.parse_args()

    meta_path = Path(args.metadata)
    meta = json.loads(meta_path.read_text())
    pages = meta.get("pages", meta if isinstance(meta, list) else [])
    out_dir = meta_path.parent

    n = 0
    for i, page in enumerate(pages):
        if args.index is not None and i != args.index:
            continue
        name = page.get("filename") or f"page_{i:06d}.png"
        png = out_dir / name
        if not png.exists():
            continue
        logical_w = page.get("width", 900)
        logical_h = page.get("height", 1200)
        out = png.with_name(f"{png.stem}_boxes.png")
        overlay(png, page.get("annotations", []), logical_w, logical_h, out)
        n += 1
        print(f"wrote {out}")

    if n == 0:
        raise SystemExit("no pages overlaid (check --index and page images)")


if __name__ == "__main__":
    main()
