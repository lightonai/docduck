"""Dedupe a docduck batch by near-duplicate ground-truth text.

Markov chains loop. At 1M-page scale this shows up as pages whose body text
is substantially a permutation of another page's. This script computes
character-shingle MinHash signatures, groups candidates via LSH bands, then
verifies with exact Jaccard on the shingle sets and writes a filtered
metadata.json (+ optionally copies the surviving pages to a new directory).

Usage:
    docduck-dedupe path/to/batch/metadata.json -o filtered/
    docduck-dedupe metadata.json --threshold 0.8 --shingle 5 --perms 128
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from collections import defaultdict
from pathlib import Path

_MERSENNE_PRIME = (1 << 61) - 1
_MAX_HASH = (1 << 32) - 1


def _shingles(text: str, k: int) -> set[int]:
    """Character k-shingles hashed to 32-bit ints."""
    text = " ".join(text.split())  # collapse whitespace so layout doesn't leak
    if len(text) < k:
        return {int.from_bytes(hashlib.blake2b(text.encode(), digest_size=4).digest(), "little")}
    out = set()
    for i in range(len(text) - k + 1):
        h = hashlib.blake2b(text[i : i + k].encode(), digest_size=4).digest()
        out.add(int.from_bytes(h, "little"))
    return out


def _permutations(n_perms: int, seed: int = 1):
    """Deterministic (a, b) pairs for universal hashing h_i(x) = (a*x + b) mod p."""
    import random

    rng = random.Random(seed)
    return [
        (rng.randint(1, _MERSENNE_PRIME - 1), rng.randint(0, _MERSENNE_PRIME - 1))
        for _ in range(n_perms)
    ]


def _minhash(shingle_hashes: set[int], perms) -> list[int]:
    if not shingle_hashes:
        return [_MAX_HASH] * len(perms)
    sig = []
    for a, b in perms:
        m = _MAX_HASH
        for x in shingle_hashes:
            v = ((a * x + b) % _MERSENNE_PRIME) & _MAX_HASH
            if v < m:
                m = v
        sig.append(m)
    return sig


def _band_keys(sig: list[int], bands: int, rows: int) -> list[bytes]:
    """Split the signature into bands: identical band tuples go to one LSH bucket."""
    out = []
    for i in range(bands):
        chunk = sig[i * rows : (i + 1) * rows]
        out.append(struct.pack(f"{rows}I", *chunk))
    return out


def _exact_jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def dedupe(
    metadata_path: Path,
    threshold: float = 0.85,
    shingle: int = 5,
    perms: int = 128,
    bands: int = 32,
    output_dir: Path | None = None,
    copy_pages: bool = False,
) -> dict:
    """Filter a metadata.json to its near-duplicate-free subset.

    Returns a summary dict. If `output_dir` is set, writes
    ``output_dir/metadata.json`` with surviving pages and (if copy_pages) the
    matching PNG + .md files. Otherwise writes
    ``<batch>/metadata.dedup.json`` alongside the input.
    """
    metadata_path = Path(metadata_path)
    batch_dir = metadata_path.parent
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    pages = meta.get("pages", [])
    if perms % bands:
        raise ValueError(f"perms ({perms}) must be divisible by bands ({bands})")
    rows = perms // bands

    # 1. Shingle + MinHash each page
    perm_table = _permutations(perms)
    signatures: list[list[int]] = []
    shingle_sets: list[set[int]] = []
    for i, p in enumerate(pages):
        gt = (batch_dir / p["ground_truth_file"]).read_text(encoding="utf-8")
        s = _shingles(gt, shingle)
        shingle_sets.append(s)
        signatures.append(_minhash(s, perm_table))
        if (i + 1) % 1000 == 0:
            print(f"  hashed {i + 1}/{len(pages)}")

    # 2. LSH: group pages that share at least one band tuple
    buckets: dict[bytes, list[int]] = defaultdict(list)
    for idx, sig in enumerate(signatures):
        for key in _band_keys(sig, bands, rows):
            buckets[key].append(idx)

    # 3. Verify candidate pairs with exact Jaccard, cluster survivors
    alive = [True] * len(pages)
    dup_pairs = 0
    seen_pair: set[tuple[int, int]] = set()
    for indices in buckets.values():
        if len(indices) < 2:
            continue
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                a, b = indices[i], indices[j]
                if a > b:
                    a, b = b, a
                if (a, b) in seen_pair:
                    continue
                seen_pair.add((a, b))
                if not alive[a] or not alive[b]:
                    continue
                if _exact_jaccard(shingle_sets[a], shingle_sets[b]) >= threshold:
                    alive[b] = False  # keep the first one encountered
                    dup_pairs += 1

    survivors = [p for p, keep in zip(pages, alive) if keep]

    out_dir = output_dir if output_dir is not None else batch_dir
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_meta_path = out_dir / ("metadata.json" if output_dir else "metadata.dedup.json")
    out_meta = {**meta, "pages": survivors, "total_pages": len(survivors)}
    out_meta["dedup"] = {
        "original_pages": len(pages),
        "dropped": len(pages) - len(survivors),
        "threshold": threshold,
        "shingle": shingle,
        "perms": perms,
        "bands": bands,
    }
    out_meta_path.write_text(json.dumps(out_meta, indent=2, ensure_ascii=False))

    if copy_pages and output_dir is not None:
        for p in survivors:
            for key in ("filename", "ground_truth_file"):
                if key in p:
                    shutil.copy2(batch_dir / p[key], out_dir / p[key])

    return {
        "input_pages": len(pages),
        "output_pages": len(survivors),
        "dropped": len(pages) - len(survivors),
        "duplicate_pairs": dup_pairs,
        "output_metadata": str(out_meta_path),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Drop near-duplicate pages from a docduck batch via MinHash + LSH."
    )
    ap.add_argument("metadata", help="Path to metadata.json")
    ap.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output dir (writes filtered metadata.json + --copy files). "
        "If omitted, writes metadata.dedup.json next to the input.",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Jaccard threshold for duplicate (default 0.85)",
    )
    ap.add_argument("--shingle", type=int, default=5, help="Character shingle size (default 5)")
    ap.add_argument("--perms", type=int, default=128, help="Number of MinHash permutations")
    ap.add_argument(
        "--bands",
        type=int,
        default=32,
        help="LSH bands (must divide --perms). More bands = more recall + more false positives",
    )
    ap.add_argument(
        "--copy",
        action="store_true",
        help="Copy surviving PNG + .md files to --output (requires --output)",
    )
    args = ap.parse_args()

    out_dir = Path(args.output) if args.output else None
    report = dedupe(
        Path(args.metadata),
        threshold=args.threshold,
        shingle=args.shingle,
        perms=args.perms,
        bands=args.bands,
        output_dir=out_dir,
        copy_pages=args.copy,
    )
    print(
        f"Dedup: {report['input_pages']} → {report['output_pages']} pages "
        f"(dropped {report['dropped']}, {report['duplicate_pairs']} duplicate pairs)\n"
        f"Wrote {report['output_metadata']}"
    )


if __name__ == "__main__":
    main()
