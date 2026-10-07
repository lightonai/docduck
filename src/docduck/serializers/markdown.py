"""Markdown serializer: preserves block markup, wraps banner/header as headings."""

import re

from ._base import register_serializer

# Every image block emits the literal ``image.png``. Paradigm / LightOnOCR
# outputs a per-page-index numbering (``image_1.png``, ``image_2.png``, …),
# so we rewrite here at serialize time where the order-within-page is known.
_IMAGE_REF_RE = re.compile(r"!\[image\]\(image\.png\)")


def _number_image_refs(text: str, counter: list[int]) -> str:
    """Rewrite each ``![image](image.png)`` to ``![image](image_N.png)`` with
    N monotonically increasing per page. The list is mutated in place so the
    counter persists across annotations."""

    def repl(_m):
        counter[0] += 1
        return f"![image](image_{counter[0]}.png)"

    return _IMAGE_REF_RE.sub(repl, text)


@register_serializer("markdown")
def to_markdown(annotations, chrome_state=None) -> str:
    """Join block `text` fields (which already carry markdown markup)."""
    parts = []
    if chrome_state and chrome_state.get("banner_title"):
        parts.append(f"# {chrome_state['banner_title']}")
    if chrome_state and chrome_state.get("header_title"):
        # Running-header chrome is a faded decorative title at the top of the
        # page: not a quotation. Emit plain text so the GT matches what
        # Paradigm / LightOnOCR outputs for the same page. Using Markdown
        # blockquote syntax (`> …`) would teach downstream models to prefix
        # top-of-page titles with `>`.
        parts.append(chrome_state["header_title"])
    img_counter = [0]
    for ann in annotations:
        # Chrome text (banner/header/page-number) is emitted explicitly via
        # chrome_state above, so skip the duplicate copy that flows in through
        # the chrome_annotations prepended to `annotations`.
        if ann.get("block_type", "").startswith("chrome:"):
            continue
        txt = ann.get("text", "")
        if txt:
            parts.append(_number_image_refs(txt, img_counter))
    if chrome_state and chrome_state.get("page_number"):
        # Page-number chrome renders only the digits (e.g. "273"), faded, in
        # the footer. Emit the same: the old "_page 273_" form added an
        # italic wrapper and a "page " prefix that don't exist in pixels.
        parts.append(chrome_state["page_number"])
    return "\n\n".join(parts)
