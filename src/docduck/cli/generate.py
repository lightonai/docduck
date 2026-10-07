#!/usr/bin/env python3
"""Main entry point: batch generate document pages with diversity tracking."""

import argparse
import json
import os
import random
import time

from ..artifacts import apply_artifacts, apply_rotation
from ..composer import compose_page
from ..defaults import DEFAULTS
from ..diversity import BatchDiversityTracker
from ..fonts import BatchFontScheduler
from ..generators import text as text_gen
from ..page_config import PageConfig

# Zero-pad filenames wide enough to support sharded 1M-page runs without
# filename collisions when multiple workers write into the same directory
# (each worker passes a disjoint --start-index).
_FILENAME_PAD = 6


def generate_batch(
    output_dir,
    n_pages=10,
    seed=None,
    page_w=900,
    page_h=1200,
    blocks=None,
    artifacts=0.0,
    artifacts_preset="mild",
    min_coverage=0.0,
    n_columns=1,
    lang=None,
    complexity=None,
    layout=None,
    output_dpi=None,
    start_index=0,
    lock_genre=True,
    features=None,
):
    """Generate a batch of diverse document pages.

    `start_index` offsets page filenames (page_{start_index+i:06d}.png), so
    multiple parallel workers can safely write into the same output dir with
    disjoint index ranges.

    `lock_genre` (default True) picks one English-genre Markov corpus per
    page, biased toward underused genres, and keeps every block on that
    page in the same genre. Set False to restore per-call genre sampling.

    Returns list of per-page metadata dicts.
    """
    os.makedirs(output_dir, exist_ok=True)

    if seed is not None:
        random.seed(seed)

    font_scheduler = BatchFontScheduler(seed=seed)
    diversity_tracker = BatchDiversityTracker()

    metadata = []
    t0 = time.time()

    for i in range(n_pages):
        max_attempts = 10 if min_coverage > 0 else 1

        # Per-page genre lock. Chosen once per page, biased toward underused
        # genres across the batch. Applies only when rendered language is
        # English (or unspecified, which defaults to English).
        page_genre = None
        if lock_genre:
            page_genre = diversity_tracker.pick_genre(text_gen.english_genres())

        for _ in range(max_attempts):
            page_seed = random.randint(0, 2**31)

            cfg_kwargs = {
                "seed": page_seed,
                "page_w": page_w,
                "page_h": page_h,
                "blocks": blocks,
                "n_columns": n_columns,
                "lang": lang,
                "complexity": complexity,
                "layout": layout,
                "output_dpi": output_dpi,
            }
            if features is not None:
                cfg_kwargs["features"] = features
            cfg = PageConfig(**cfg_kwargs)

            if min_coverage >= 0.5:
                cfg.complexity = "high"
                from ..page_config import COMPLEXITY_PROFILES

                cfg._complexity_profile = {
                    **COMPLEXITY_PROFILES["high"],
                    "min_blocks": 10,
                    "max_blocks": 20,
                }
                margin = max(15, int(50 * (1.0 - min_coverage) / 0.15))
                cfg.style.margin_name = "dense"
                cfg.style.margins = {
                    "top": margin,
                    "bottom": margin,
                    "left": margin,
                    "right": margin,
                }
                cfg.style.body_size = max(cfg.style.body_size, 9)

            style_pools = DEFAULTS["style"]
            overrides = diversity_tracker.suggest_style_overrides()
            if "preferred_paper" in overrides and random.random() < 0.6:
                name = overrides["preferred_paper"]
                cfg.style.paper_name = name
                cfg.style.paper_color = style_pools["papers"][name]
            if "preferred_accent" in overrides and random.random() < 0.6:
                name = overrides["preferred_accent"]
                cfg.style.accent_name = name
                cfg.style.accent_color = style_pools["accents"][name]

            cfg.fonts = font_scheduler.next_palette()

            applied_genre = page_genre if (cfg.lang in (None, "en")) else None
            text_gen.set_locked_genre(applied_genre)
            try:
                surface, annotations, block_seq, full_text = compose_page(
                    page_config=cfg,
                )
            finally:
                text_gen.set_locked_genre(None)

            content_area = sum(a["bbox"]["width"] * a["bbox"]["height"] for a in annotations)
            coverage = content_area / (page_w * page_h)
            if coverage >= min_coverage:
                break

        page_index = start_index + i
        fname = f"page_{page_index:0{_FILENAME_PAD}d}.png"
        fpath = os.path.join(output_dir, fname)
        cov_str = f"  cov={coverage:.0%}" if min_coverage > 0 else ""
        print(
            f"  [{i + 1}/{n_pages}] {fname}  lang={cfg.lang}  "
            f"complexity={cfg.complexity}  "
            f"fonts={cfg.fonts.serif}/{cfg.fonts.sans}  "
            f"paper={cfg.style.paper_name}  accent={cfg.style.accent_name}{cov_str}"
        )

        if artifacts > 0:
            # Harder presets tolerate larger skew: scale rotation accordingly.
            rot_scale = {"mild": 0.8, "photocopy": 1.6, "fax": 3.0, "extreme": 5.0}.get(
                artifacts_preset, 0.8
            )
            surface = apply_rotation(surface, max_degrees=artifacts * rot_scale, seed=page_seed)
            surface = apply_artifacts(
                surface, intensity=artifacts, seed=page_seed, preset=artifacts_preset
            )

        surface.write_to_png(fpath)

        gt_fname = f"page_{page_index:0{_FILENAME_PAD}d}.md"
        gt_path = os.path.join(output_dir, gt_fname)
        with open(gt_path, "w", encoding="utf-8") as gt_f:
            gt_f.write(full_text)

        diversity_tracker.record_page(cfg.style, block_seq, genre=applied_genre)

        # Compute pixel-space font sizes for downstream filtering / analysis.
        # 1pt = output_dpi / 72 px. Store both so consumers don't need to know
        # the rendering DPI.
        from ..composer import DEFAULT_OUTPUT_DPI

        dpi = getattr(cfg, "output_dpi", None) or DEFAULT_OUTPUT_DPI
        px_scale = dpi / 72.0

        page_meta = {
            "filename": fname,
            "ground_truth_file": gt_fname,
            "seed": page_seed,
            "lang": cfg.lang,
            "genre": applied_genre,
            "complexity": cfg.complexity,
            "width": page_w,
            "height": page_h,
            "output_dpi": dpi,
            "style": {
                "paper": cfg.style.paper_name,
                "text_color": cfg.style.text_name,
                "accent": cfg.style.accent_name,
                "margins": cfg.style.margin_name,
                "body_size": round(cfg.style.body_size, 1),
                "body_size_px": round(cfg.style.body_size * px_scale, 1),
                "heading_size_px": round(cfg.style.heading_size * px_scale, 1),
                "subheading_size_px": round(cfg.style.subheading_size * px_scale, 1),
                "tiny_size_px": round(cfg.style.tiny_size * px_scale, 1),
            },
            "fonts": {
                "serif": cfg.fonts.serif,
                "sans": cfg.fonts.sans,
                "mono": cfg.fonts.mono,
            },
            "blocks": block_seq,
            "annotations": annotations,
        }

        content_area = sum(a["bbox"]["width"] * a["bbox"]["height"] for a in annotations)
        page_area = page_w * page_h
        page_meta["coverage"] = round(content_area / page_area, 3) if page_area > 0 else 0

        metadata.append(page_meta)

    elapsed = time.time() - t0

    meta_path = os.path.join(output_dir, "metadata.json")
    diversity_report = diversity_tracker.report()

    lang_dist = {}
    for m in metadata:
        lang_dist[m["lang"]] = lang_dist.get(m["lang"], 0) + 1

    with open(meta_path, "w") as f:
        json.dump(
            {
                "total_pages": n_pages,
                "generation_time_s": round(elapsed, 2),
                "diversity": diversity_report,
                "language_distribution": lang_dist,
                "pages": metadata,
            },
            f,
            indent=2,
        )

    print(f"\n{'=' * 60}")
    print(f"Generated {n_pages} pages in {elapsed:.1f}s ({elapsed / n_pages:.2f}s/page)")
    print(f"Output:   {output_dir}")
    print(f"Metadata: {meta_path}")
    print("\nDiversity report:")
    print(f"  Unique layouts:    {diversity_report['unique_layouts']}")
    print(f"  Block type counts: {diversity_report['block_type_counts']}")
    print(f"  Style combos used: {len(diversity_report['style_distribution'])}")
    print(f"  Languages:         {lang_dist}")
    coverages = [m["coverage"] for m in metadata]
    avg_cov = sum(coverages) / len(coverages) if coverages else 0
    min_cov = min(coverages) if coverages else 0
    max_cov = max(coverages) if coverages else 0
    print(f"  Page coverage:     {avg_cov:.0%} avg, {min_cov:.0%} min, {max_cov:.0%} max")
    print(f"{'=' * 60}")

    return metadata


def main():
    from ..adversarial import VALID_MODES

    parser = argparse.ArgumentParser(description="Generate synthetic document pages")
    parser.add_argument(
        "-n", "--num-pages", type=int, default=10, help="Number of pages to generate (default: 10)"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="output", help="Output directory (default: output)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--width", type=int, default=900, help="Page width in pixels (default: 900)"
    )
    parser.add_argument(
        "--height", type=int, default=1200, help="Page height in pixels (default: 1200)"
    )
    parser.add_argument(
        "--output-dpi",
        type=int,
        default=None,
        help="Render DPI. Defaults to DOCDUCK_OUTPUT_DPI or 200.",
    )
    parser.add_argument(
        "--blocks",
        type=str,
        default=None,
        help="Comma-separated block types to render (e.g. heading,multicolumn,table,code)",
    )
    parser.add_argument(
        "--artifacts",
        type=float,
        default=0.0,
        help="Scan artifact intensity 0.0-1.0 (default: 0.0)",
    )
    parser.add_argument(
        "--artifacts-preset",
        type=str,
        default="mild",
        choices=["mild", "photocopy", "fax", "extreme"],
        help="Artifact regime: 'mild' (near-invisible, default), 'photocopy', "
        "'fax', 'extreme'. Harder presets add blur + contrast saturation + "
        "dropout to produce OCR-challenging input.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.0,
        help="Minimum page coverage 0.0-1.0 (retries until met)",
    )
    parser.add_argument(
        "--columns", type=int, default=1, help="Page-level column layout: 1-4 (default: 1)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="Force a single language code for every page (e.g. 'en', 'fr', 'zh'). "
        "Default: per-page random pick weighted toward English.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="First page filename index (default: 0). Use with sharded parallel "
        "runs, for example worker 1 passes --start-index 0 and worker 2 passes "
        "--start-index 100000, so each worker writes a disjoint page_XXXXXX.png "
        "range into the shared dir.",
    )
    parser.add_argument(
        "--no-lock-genre",
        action="store_true",
        help="Disable per-page English genre lock. By default every block on one "
        "page uses the same en_* corpus (chosen least-used-first) for content "
        "coherence; this flag restores per-call genre sampling.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="YAML config file that overrides DEFAULTS and "
        "sets PageConfig fields (see config_loader.py)",
    )
    parser.add_argument(
        "--content-mode",
        choices=VALID_MODES,
        default=None,
        help="Adversarial content mode for the whole batch "
        "(overrides features.content_mode from YAML if set)",
    )
    parser.add_argument(
        "--hf-dataset",
        type=str,
        default=None,
        metavar="SPEC",
        help="Use a HuggingFace dataset as the text source instead of Markov. "
        "Format: 'dataset_id[:config[:split[:column]]]'. "
        "Example: 'acme/corpus::train:text'. "
        "Requires the 'datasets' package (install with [hf] extra).",
    )
    parser.add_argument(
        "--hf-samples",
        type=int,
        default=2000,
        help="Number of rows to sample from the HF dataset to build the sentence pool (default: 2000).",
    )
    args = parser.parse_args()

    if args.hf_dataset:
        from ..generators import text as text_gen

        parts = args.hf_dataset.split(":")
        text_gen.set_text_source(
            "hf",
            dataset=parts[0],
            config=parts[1] if len(parts) > 1 and parts[1] else None,
            split=parts[2] if len(parts) > 2 and parts[2] else "train",
            column=parts[3] if len(parts) > 3 and parts[3] else "text",
            n_samples=args.hf_samples,
            seed=args.seed,
        )

    yaml_cfg = None
    if args.config:
        from ..config_loader import apply_defaults, load_config

        yaml_cfg, merged = load_config(args.config)
        apply_defaults(merged)

    block_list = args.blocks.split(",") if args.blocks else None

    # YAML PageConfig fields are only honored when the YAML file explicitly
    # declared them (tracked on _yaml_explicit_fields). Otherwise the value
    # on yaml_cfg came from PageConfig.__post_init__'s randomized fallback,
    # and forwarding it would pin one "randomly picked" complexity / lang /
    # layout across the entire batch: which is the bug that made every
    # page complexity=low.
    explicit = getattr(yaml_cfg, "_yaml_explicit_fields", frozenset()) if yaml_cfg else frozenset()

    def _yaml_field(name):
        return getattr(yaml_cfg, name) if (yaml_cfg is not None and name in explicit) else None

    lang = args.lang or _yaml_field("lang")
    complexity = _yaml_field("complexity")
    layout = _yaml_field("layout")
    features = _yaml_field("features")
    if args.content_mode:
        from ..page_config import Features

        features = features or Features()
        features.content_mode = args.content_mode
    if yaml_cfg is not None:
        if "blocks" in explicit and not block_list:
            block_list = yaml_cfg.blocks
        if "page_w" in explicit and args.width == 900:
            args.width = yaml_cfg.page_w
        if "page_h" in explicit and args.height == 1200:
            args.height = yaml_cfg.page_h
        if "n_columns" in explicit and args.columns == 1:
            args.columns = yaml_cfg.n_columns
        if "output_dpi" in explicit and args.output_dpi is None:
            args.output_dpi = yaml_cfg.output_dpi

    generate_batch(
        output_dir=args.output,
        n_pages=args.num_pages,
        seed=args.seed,
        page_w=args.width,
        page_h=args.height,
        blocks=block_list,
        artifacts=args.artifacts,
        artifacts_preset=args.artifacts_preset,
        min_coverage=args.min_coverage,
        n_columns=args.columns,
        lang=lang,
        complexity=complexity,
        layout=layout,
        output_dpi=args.output_dpi,
        start_index=args.start_index,
        lock_genre=not args.no_lock_genre,
        features=features,
    )


if __name__ == "__main__":
    main()
