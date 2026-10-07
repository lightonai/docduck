"""JSON serializer: returns a dict with all structured info per block."""

from ._base import register_serializer


@register_serializer("json")
def to_json(annotations, chrome_state=None) -> dict:
    """Return a structured dict: chrome + list of block records.

    Each block record: {block_type, text, data, bbox}. `data` holds any
    block-specific structured fields (table rows, list items, …).
    """
    return {
        "chrome": dict(chrome_state or {}),
        "blocks": [
            {
                "block_type": ann.get("block_type", ""),
                "text": ann.get("text", ""),
                "data": ann.get("data") or {},
                "bbox": ann.get("bbox", {}),
            }
            for ann in annotations
        ],
    }
