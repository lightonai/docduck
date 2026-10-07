"""Export a docduck batch as an SFT training dataset in the
``lightonai/lightocr-gpt4o-crops`` on-disk format: parquet rows + sharded
WebDataset-style image tars.

Each parquet row is one page (not a crop) with:
    messages : [{"role":"user","content":"<IMG_0>"},
                {"role":"assistant","content":"<page ground truth>"}]
    images   : ["pages/page_NNNNNN.png"]
    key      : "page_NNNNNN"
    metadata : {image_height, image_width, output_dpi, lang, genre, bucket,
                complexity, seed, coverage, blocks,
                fonts{serif,sans,mono},
                style{paper,text_color,accent,margins,body_size,
                      body_size_px,heading_size_px,subheading_size_px,
                      tiny_size_px}}

The assistant content is docduck's existing page-level ground truth (matching
LightOnOCR's output format: Markdown + ``<table>`` HTML + LaTeX math spans).

Output layout (default ``--files-per-shard 1200``):
    dataset/
        data/train-00000-of-00001.parquet
        data/validation-00000-of-00001.parquet
        images/pages-00000.tar      # up to 1200 PNGs each, ~700 MB per shard
        images/pages-00001.tar
        ...

Use ``--files-per-shard 0`` for the legacy monolithic ``images/pages.tar``.

Usage:
    docduck-export-sft <output_dir>/metadata.json -o dataset/ [--val-frac 0.05]
"""

from __future__ import annotations

import argparse
import json
import random
import tarfile
from pathlib import Path

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as e:
    raise SystemExit("export_sft needs pyarrow. Install with: uv pip install 'docduck[sft]'") from e


SCHEMA = pa.schema(
    [
        pa.field(
            "messages",
            pa.list_(
                pa.struct(
                    [
                        pa.field("content", pa.string()),
                        pa.field("role", pa.string()),
                    ]
                )
            ),
        ),
        pa.field("images", pa.list_(pa.string())),
        pa.field("key", pa.string()),
        pa.field(
            "metadata",
            pa.struct(
                [
                    pa.field("image_height", pa.int64()),
                    pa.field("image_width", pa.int64()),
                    pa.field("output_dpi", pa.int64()),
                    pa.field("lang", pa.string()),
                    pa.field("genre", pa.string()),
                    pa.field("bucket", pa.string()),
                    pa.field("complexity", pa.string()),
                    pa.field("seed", pa.int64()),
                    pa.field("coverage", pa.float64()),
                    pa.field("blocks", pa.list_(pa.string())),
                    pa.field(
                        "fonts",
                        pa.struct(
                            [
                                pa.field("serif", pa.string()),
                                pa.field("sans", pa.string()),
                                pa.field("mono", pa.string()),
                            ]
                        ),
                    ),
                    pa.field(
                        "style",
                        pa.struct(
                            [
                                pa.field("paper", pa.string()),
                                pa.field("text_color", pa.string()),
                                pa.field("accent", pa.string()),
                                pa.field("margins", pa.string()),
                                pa.field("body_size", pa.float64()),
                                pa.field("body_size_px", pa.float64()),
                                pa.field("heading_size_px", pa.float64()),
                                pa.field("subheading_size_px", pa.float64()),
                                pa.field("tiny_size_px", pa.float64()),
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ]
)


def _row(page: dict, batch_dir: Path) -> dict:
    gt = (batch_dir / page["ground_truth_file"]).read_text(encoding="utf-8")
    key = Path(page["filename"]).stem
    fonts = page.get("fonts") or {}
    style = page.get("style") or {}
    return {
        "messages": [
            {"role": "user", "content": "<IMG_0>"},
            {"role": "assistant", "content": gt},
        ],
        "images": [f"pages/{page['filename']}"],
        "key": key,
        "metadata": {
            "image_height": int(page["height"]),
            "image_width": int(page["width"]),
            "output_dpi": int(page.get("output_dpi") or 0),
            "lang": page.get("lang", "") or "",
            "genre": page.get("genre", "") or "",
            "bucket": page.get("bucket", "") or "",
            "complexity": page.get("complexity", "") or "",
            "seed": int(page.get("seed") or 0),
            "coverage": float(page.get("coverage") or 0.0),
            "blocks": list(page.get("blocks") or []),
            "fonts": {
                "serif": fonts.get("serif", "") or "",
                "sans": fonts.get("sans", "") or "",
                "mono": fonts.get("mono", "") or "",
            },
            "style": {
                "paper": style.get("paper", "") or "",
                "text_color": style.get("text_color", "") or "",
                "accent": style.get("accent", "") or "",
                "margins": style.get("margins", "") or "",
                "body_size": float(style.get("body_size") or 0.0),
                "body_size_px": float(style.get("body_size_px") or 0.0),
                "heading_size_px": float(style.get("heading_size_px") or 0.0),
                "subheading_size_px": float(style.get("subheading_size_px") or 0.0),
                "tiny_size_px": float(style.get("tiny_size_px") or 0.0),
            },
        },
    }


def _write_parquet(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    pq.write_table(table, path)


def _write_tar_shards(
    pages: list[dict], batch_dir: Path, out_dir: Path, files_per_shard: int, prefix: str = "pages"
) -> int:
    """Write PNGs to one-or-more tar shards. Each shard holds up to
    ``files_per_shard`` files. WebDataset-style naming: pages-00000.tar,
    pages-00001.tar, … Returns the number of shards written.

    Use ``files_per_shard=0`` to keep the monolithic behavior (one tar).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if files_per_shard <= 0:
        with tarfile.open(out_dir / f"{prefix}.tar", "w") as tf:
            for p in pages:
                src = batch_dir / p["filename"]
                tf.add(src, arcname=f"pages/{p['filename']}")
        return 1

    shard_idx = 0
    files_in_shard = 0
    tf: tarfile.TarFile | None = None
    for p in pages:
        if files_in_shard == 0:
            if tf is not None:
                tf.close()
            tf = tarfile.open(out_dir / f"{prefix}-{shard_idx:05d}.tar", "w")
        src = batch_dir / p["filename"]
        tf.add(src, arcname=f"pages/{p['filename']}")
        files_in_shard += 1
        if files_in_shard >= files_per_shard:
            files_in_shard = 0
            shard_idx += 1
    if tf is not None and not tf.closed:
        tf.close()
    return shard_idx + (1 if files_in_shard > 0 else 0)


def export(
    metadata_path: Path,
    output_dir: Path,
    val_frac: float = 0.05,
    seed: int = 0,
    files_per_shard: int = 1200,
) -> dict:
    metadata_path = Path(metadata_path)
    output_dir = Path(output_dir)
    batch_dir = metadata_path.parent

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    pages = meta.get("pages", [])
    if not pages:
        raise SystemExit(f"No pages found in {metadata_path}")

    rng = random.Random(seed)
    shuffled = list(pages)
    rng.shuffle(shuffled)
    n_val = max(1, int(round(len(shuffled) * val_frac))) if val_frac > 0 else 0
    val_pages = shuffled[:n_val]
    train_pages = shuffled[n_val:]

    train_rows = [_row(p, batch_dir) for p in train_pages]
    val_rows = [_row(p, batch_dir) for p in val_pages]

    _write_parquet(train_rows, output_dir / "data" / "train-00000-of-00001.parquet")
    if val_rows:
        _write_parquet(val_rows, output_dir / "data" / "validation-00000-of-00001.parquet")

    n_shards = _write_tar_shards(
        pages, batch_dir, output_dir / "images", files_per_shard=files_per_shard
    )

    return {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "total_pages": len(pages),
        "n_tar_shards": n_shards,
        "output_dir": str(output_dir),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Export a docduck batch as SFT parquet + image tar, "
        "matching the lightonai/lightocr-gpt4o-crops row schema."
    )
    ap.add_argument("metadata", help="Path to metadata.json from a docduck batch")
    ap.add_argument("-o", "--output", required=True, help="Output dataset directory")
    ap.add_argument(
        "--val-frac",
        type=float,
        default=0.05,
        help="Fraction of pages to place in validation split (default: 0.05; "
        "set to 0 to emit only the train split)",
    )
    ap.add_argument("--seed", type=int, default=0, help="Shuffle seed for the split")
    ap.add_argument(
        "--files-per-shard",
        type=int,
        default=1200,
        help="Tar shard size (pages per tar). 0 → monolithic pages.tar (old behavior). "
        "Default 1200 follows WebDataset convention and keeps shards ~700MB at "
        "docduck's typical page size, resumable uploads, streamable training.",
    )
    args = ap.parse_args()

    report = export(
        Path(args.metadata),
        Path(args.output),
        args.val_frac,
        args.seed,
        files_per_shard=args.files_per_shard,
    )
    print(
        f"Wrote {report['train_rows']} train + {report['val_rows']} val rows "
        f"({report['total_pages']} pages, {report['n_tar_shards']} tar shard(s)) "
        f"to {report['output_dir']}"
    )


if __name__ == "__main__":
    main()
