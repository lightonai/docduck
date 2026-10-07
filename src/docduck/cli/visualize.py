"""Generate an HTML grid visualizer for rendered documents.

Reads metadata.json from a generation run and produces a self-contained HTML
file with thumbnails in a responsive grid. Each thumbnail shows filename,
language, complexity, coverage, and blocks on hover. Click to open full image.

Usage:
    python -m docduck.cli.visualize output/metadata.json
    python -m docduck.cli.visualize output/metadata.json -o gallery.html
    python -m docduck.cli.visualize output/metadata.json --filter lang=fr
    python -m docduck.cli.visualize output/metadata.json --sort coverage
"""

import argparse
import base64
import html
import json
import webbrowser
from pathlib import Path


def _filter_pages(pages, expr):
    """Apply a simple key=value filter expression."""
    if not expr:
        return pages
    key, _, value = expr.partition("=")
    key, value = key.strip(), value.strip()

    def get(page, k):
        if k in page:
            return page[k]
        if "style" in page and k in page["style"]:
            return page["style"][k]
        return None

    return [p for p in pages if str(get(p, key)) == value]


def _sort_pages(pages, key):
    if not key:
        return pages
    reverse = key.startswith("-")
    k = key.lstrip("-")

    def sort_key(p):
        if k in p:
            return p[k] or 0
        if "style" in p and k in p["style"]:
            return p["style"][k] or 0
        return 0

    return sorted(pages, key=sort_key, reverse=reverse)


def _embed_image(image_path, max_bytes, html_dir=None):
    """Return an <img src=...> tag, either data URI or file link.

    When falling back to a file link, emit the path *relative to the HTML's
    own directory* so the browser can resolve it. Using ``image_path.name``
    (just the basename) only works when HTML and images live in the same
    dir: breaks as soon as a merged metadata.json references images in
    shard subdirs (e.g. ``s0_tables/page_000000.png``).
    """
    try:
        size = image_path.stat().st_size
        if size <= max_bytes:
            b64 = base64.b64encode(image_path.read_bytes()).decode()
            return f"data:image/png;base64,{b64}"
    except OSError:
        pass
    import os

    if html_dir is not None:
        try:
            return os.path.relpath(image_path, html_dir)
        except ValueError:
            pass
    return image_path.name


_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    margin: 0;
    padding: 20px;
    background: #f5f5f7;
    color: #222;
}
h1 {
    font-size: 20px;
    margin: 0 0 8px 0;
}
.meta {
    color: #666;
    font-size: 13px;
    margin-bottom: 16px;
}
.controls {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}
.controls input, .controls select {
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 13px;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
}
.card {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: pointer;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.card img {
    width: 100%;
    display: block;
    background: white;
}
.card-body {
    padding: 10px 12px;
    font-size: 12px;
    line-height: 1.5;
}
.card-title {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
    font-family: ui-monospace, Menlo, monospace;
    color: #333;
}
.card-row {
    display: flex;
    justify-content: space-between;
    color: #666;
}
.card-row .key {
    color: #999;
}
.tag {
    display: inline-block;
    padding: 1px 6px;
    background: #eee;
    border-radius: 3px;
    font-size: 11px;
    margin: 2px 2px 0 0;
    color: #444;
    font-family: ui-monospace, Menlo, monospace;
}
.coverage-bar {
    height: 4px;
    background: #eee;
    border-radius: 2px;
    margin-top: 6px;
    overflow: hidden;
}
.coverage-fill {
    height: 100%;
    background: linear-gradient(90deg, #4a90e2, #50c878);
}
.modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    z-index: 100;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.modal.open { display: flex; }
.modal img {
    max-width: 95%;
    max-height: 95%;
    box-shadow: 0 4px 40px rgba(0,0,0,0.5);
}
.modal-close {
    position: absolute;
    top: 20px;
    right: 20px;
    color: white;
    background: none;
    border: none;
    font-size: 30px;
    cursor: pointer;
}
"""

_JS = """
function openModal(src) {
    const m = document.getElementById('modal');
    document.getElementById('modal-img').src = src;
    m.classList.add('open');
}
function closeModal() {
    document.getElementById('modal').classList.remove('open');
}
function filterCards() {
    const q = document.getElementById('filter').value.toLowerCase();
    document.querySelectorAll('.card').forEach(card => {
        const text = card.dataset.search.toLowerCase();
        card.style.display = text.includes(q) ? '' : 'none';
    });
}
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});
"""


def build_html(
    metadata_path, output_path=None, max_embed_bytes=500_000, filter_expr=None, sort_key=None
):
    """Build an HTML gallery from a generation metadata.json."""
    metadata_path = Path(metadata_path)
    with open(metadata_path) as f:
        meta = json.load(f)

    base_dir = metadata_path.parent
    pages = meta.get("pages", [])
    pages = _filter_pages(pages, filter_expr)
    pages = _sort_pages(pages, sort_key)

    # Determine where the HTML will land now so _embed_image can emit image
    # paths relative to that directory when it falls back to file links.
    if output_path is None:
        html_dir = base_dir
    else:
        html_dir = Path(output_path).resolve().parent

    title = f"docduck: {metadata_path.parent.name}"
    summary_parts = [
        f"{len(pages)} page(s)",
        f"{meta.get('total_pages', len(pages))} generated",
    ]
    if "generation_time_s" in meta:
        summary_parts.append(f"{meta['generation_time_s']:.1f}s")

    cards = []
    for p in pages:
        image_path = base_dir / p["filename"]
        img_src = _embed_image(image_path, max_embed_bytes, html_dir=html_dir)

        style = p.get("style", {})
        blocks = p.get("blocks", [])
        coverage = p.get("coverage", 0)

        block_tags = "".join(f'<span class="tag">{html.escape(b)}</span>' for b in blocks)

        fonts = p.get("fonts", {})
        search = " ".join(
            [
                p.get("filename", ""),
                p.get("lang", ""),
                p.get("genre") or "",
                p.get("complexity", ""),
                style.get("paper", ""),
                style.get("accent", ""),
                fonts.get("serif", ""),
                fonts.get("sans", ""),
                fonts.get("mono", ""),
                " ".join(blocks),
            ]
        )

        cards.append(f"""
<div class="card" data-search="{html.escape(search)}"
     onclick="openModal('{img_src}')">
    <img src="{img_src}" loading="lazy" alt="{html.escape(p["filename"])}">
    <div class="card-body">
        <div class="card-title">{html.escape(p["filename"])}</div>
        <div class="card-row"><span class="key">lang / genre</span>
            <span>{html.escape(p.get("lang", "?"))} / {html.escape(p.get("genre") or "—")}</span></div>
        <div class="card-row"><span class="key">complexity</span>
            <span>{html.escape(p.get("complexity", "?"))}</span></div>
        <div class="card-row"><span class="key">paper / accent</span>
            <span>{html.escape(style.get("paper", "?"))} / {html.escape(style.get("accent", "?"))}</span></div>
        <div class="card-row"><span class="key">serif / sans / mono</span>
            <span style="font-size:11px">{html.escape(p.get("fonts", {}).get("serif", "?"))} / {html.escape(p.get("fonts", {}).get("sans", "?"))} / {html.escape(p.get("fonts", {}).get("mono", "?"))}</span></div>
        <div class="card-row"><span class="key">seed</span>
            <span>{p.get("seed", "?")}</span></div>
        <div class="card-row"><span class="key">coverage</span>
            <span>{coverage * 100:.0f}%</span></div>
        <div class="coverage-bar"><div class="coverage-fill"
             style="width: {min(100, coverage * 100):.0f}%"></div></div>
        <div style="margin-top: 6px">{block_tags}</div>
    </div>
</div>
""")

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<div class="meta">{" · ".join(summary_parts)}</div>
<div class="controls">
    <input id="filter" type="text" placeholder="Filter by lang, block, paper…"
           oninput="filterCards()" style="flex: 1; min-width: 200px;">
</div>
<div class="grid">{"".join(cards)}</div>
<div id="modal" class="modal" onclick="closeModal()">
    <button class="modal-close" onclick="closeModal()">&times;</button>
    <img id="modal-img" src="" alt="">
</div>
<script>{_JS}</script>
</body>
</html>
"""

    if output_path is None:
        output_path = base_dir / "gallery.html"
    else:
        output_path = Path(output_path)

    output_path.write_text(html_out, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Visualize rendered documents in an HTML grid")
    parser.add_argument("metadata", help="Path to metadata.json from a generation run")
    parser.add_argument(
        "-o", "--output", default=None, help="Output HTML file (default: <dir>/gallery.html)"
    )
    parser.add_argument("--filter", default=None, help="Filter pages by key=value (e.g. lang=fr)")
    parser.add_argument(
        "--sort", default=None, help="Sort pages by key (prefix - for descending, e.g. -coverage)"
    )
    parser.add_argument(
        "--max-embed-kb",
        type=int,
        default=500,
        help="Max image size to embed as base64 (default: 500 KB). "
        "Larger images are referenced by path.",
    )
    parser.add_argument("--open", action="store_true", help="Open the output file in a browser")
    args = parser.parse_args()

    path = build_html(
        args.metadata,
        args.output,
        max_embed_bytes=args.max_embed_kb * 1024,
        filter_expr=args.filter,
        sort_key=args.sort,
    )
    print(f"Wrote gallery to {path}")

    if args.open:
        webbrowser.open(f"file://{path.resolve()}")


if __name__ == "__main__":
    main()
