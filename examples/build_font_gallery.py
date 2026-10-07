#!/usr/bin/env python3
"""Build a side-by-side gallery showing the same page content rendered with
different fonts. Useful after running `docduck-fonts` to see which downloaded
families work best for your batches.

All Latin pages share a seed so text content stays identical: only the font
changes. Non-Latin pages use a per-script seed so content fits the script.

Output:
- `examples/out/font_gallery/page_NNNN.png`           one PNG per font
- `examples/out/font_gallery/metadata.json`           per-page metadata
- `examples/out/font_gallery/gallery.html`            self-contained HTML grid
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from docduck.composer import compose_page
from docduck.fonts import FontPalette, get_system_fonts
from docduck.page_config import PageConfig

OUT = Path(__file__).parent / "out" / "font_gallery"
OUT.mkdir(parents=True, exist_ok=True)


# Font palettes to render. Latin serifs dominate since that's the most common
# comparison; a couple of non-Latin entries confirm script-aware rendering.
GALLERY: list[dict] = [
    # Latin serif
    {"lang": "en", "seed": 7, "serif": "Merriweather",     "sans": "Inter",        "mono": "IBM Plex Mono"},
    {"lang": "en", "seed": 7, "serif": "Playfair Display", "sans": "Inter",        "mono": "IBM Plex Mono"},
    {"lang": "en", "seed": 7, "serif": "Crimson Pro",      "sans": "Inter",        "mono": "IBM Plex Mono"},
    {"lang": "en", "seed": 7, "serif": "EB Garamond",      "sans": "Inter",        "mono": "IBM Plex Mono"},
    {"lang": "en", "seed": 7, "serif": "IBM Plex Serif",   "sans": "IBM Plex Sans","mono": "IBM Plex Mono"},
    # Latin sans
    {"lang": "en", "seed": 7, "serif": "IBM Plex Serif",   "sans": "Lato",         "mono": "IBM Plex Mono"},
    {"lang": "en", "seed": 7, "serif": "IBM Plex Serif",   "sans": "Inter",        "mono": "IBM Plex Mono"},
    # Non-Latin
    {"lang": "ar", "seed": 11, "serif": "Amiri",           "sans": "Cairo",        "mono": "IBM Plex Mono"},
    {"lang": "zh", "seed": 13, "serif": "Noto Serif SC",   "sans": "Noto Sans SC", "mono": "IBM Plex Mono"},
]


def render_one(entry: dict, idx: int) -> dict:
    pal = FontPalette(serif=entry["serif"], sans=entry["sans"], mono=entry["mono"])
    cfg = PageConfig(
        lang=entry["lang"],
        seed=entry["seed"],
        fonts=pal,
        page_w=700,
        page_h=900,
        output_dpi=150,
        # Fixed block sequence so page layout is identical across fonts;
        # only the type-system changes. Swap/remove blocks to taste.
        blocks=["heading", "prose", "prose", "subheading", "prose", "table"],
    )
    surface, annotations, block_seq, _ = compose_page(page_config=cfg)
    filename = f"page_{idx:04d}.png"
    surface.write_to_png(str(OUT / filename))
    # Coverage = fraction of page area used by content: same formula the
    # regular `docduck` generator uses so the gallery cards show useful %.
    content_area = sum(a["bbox"]["width"] * a["bbox"]["height"] for a in annotations)
    page_area = cfg.page_w * cfg.page_h
    coverage = round(content_area / page_area, 3) if page_area > 0 else 0.0
    # Mirror the metadata.json shape that docduck-visualize expects.
    return {
        "filename": filename,
        "lang": entry["lang"],
        "seed": entry["seed"],
        "complexity": "medium",
        "width": cfg.page_w,
        "height": cfg.page_h,
        "style": {
            "paper": cfg.style.paper_name,
            "text_color": cfg.style.text_name,
            "accent": cfg.style.accent_name,
            "margins": cfg.style.margin_name,
            "body_size": round(cfg.style.body_size, 1),
        },
        "fonts": {"serif": pal.serif, "sans": pal.sans, "mono": pal.mono},
        "blocks": block_seq,
        "annotations": annotations,
        "coverage": coverage,
    }


def main():
    available = get_system_fonts("en")
    have = set(available["serif"]) | set(available["sans"]) | set(available["mono"])
    plan = []
    for entry in GALLERY:
        missing = [f for f in (entry["serif"], entry["sans"], entry["mono"]) if f not in have]
        if missing:
            print(f"skip  {entry['serif']!r}/{entry['sans']!r}: missing {missing}", file=sys.stderr)
            continue
        plan.append(entry)

    if not plan:
        print(
            "error: no planned font palettes are installed. Run "
            "`python -m docduck.cli.download_fonts` first, or edit GALLERY in this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Rendering {len(plan)} pages → {OUT}")
    metadata = []
    for i, entry in enumerate(plan):
        print(f"  [{i}] {entry['lang']}  {entry['serif']:22s} / {entry['sans']:14s}")
        metadata.append(render_one(entry, i))

    meta_path = OUT / "metadata.json"
    meta_path.write_text(json.dumps({"pages": metadata}, ensure_ascii=False, indent=2))

    gallery_path = OUT / "gallery.html"
    subprocess.run(
        [sys.executable, "-m", "docduck.cli.visualize", str(meta_path), "-o", str(gallery_path)],
        check=True,
    )
    print(f"\nOpen: {gallery_path}")


if __name__ == "__main__":
    main()
