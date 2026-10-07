"""Serializer registry: plug-in output formats for page ground truth.

Serializers consume a list of annotations (each annotation is a dict with
`block_type`, `text`, `data`, `bbox`) plus optional chrome_state and
produce a single string (or dict, for JSON).

Register a custom serializer:
    from docduck.serializers import register_serializer

    @register_serializer("html")
    def to_html(annotations, chrome_state=None):
        ...
"""

from ..registry import Registry

serializers: Registry = Registry("serializer")


def register_serializer(name: str, weight: float = 1.0):
    """Decorator: register a serializer function under `name`."""
    return serializers.register(name, weight=weight)


def serialize(name: str, annotations, chrome_state=None):
    """Run the named serializer against annotations + chrome_state."""
    fn = serializers.get(name)
    return fn(annotations, chrome_state=chrome_state)
