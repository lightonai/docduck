"""Plain-text serializer: strips light markdown markup from each block's text."""

import re

from ._base import register_serializer

_HEADING_PREFIX_RE = re.compile(r"^#+\s+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITAL_RE = re.compile(r"\*(.+?)\*")
_CODE_FENCE_RE = re.compile(r"^```.*$", re.MULTILINE)
_LIST_BULLET_RE = re.compile(r"^(\s*)-\s+", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    text = _CODE_FENCE_RE.sub("", text)
    text = _HEADING_PREFIX_RE.sub("", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITAL_RE.sub(r"\1", text)
    text = _LIST_BULLET_RE.sub(r"\1", text)
    return text.strip()


@register_serializer("plain")
def to_plain(annotations, chrome_state=None) -> str:
    """Concatenate stripped-markdown text from all blocks + chrome."""
    parts = []
    if chrome_state and chrome_state.get("banner_title"):
        parts.append(chrome_state["banner_title"])
    if chrome_state and chrome_state.get("header_title"):
        parts.append(chrome_state["header_title"])
    for ann in annotations:
        if ann.get("block_type", "").startswith("chrome:"):
            continue
        stripped = _strip_markdown(ann.get("text", ""))
        if stripped:
            parts.append(stripped)
    if chrome_state and chrome_state.get("page_number"):
        parts.append(chrome_state["page_number"])
    return "\n\n".join(parts)
