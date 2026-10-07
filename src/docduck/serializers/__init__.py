"""Page-level serializers: plain, markdown, json, plus registry for custom."""

from ._base import register_serializer, serialize, serializers

# isort: split
# Importing each submodule triggers self-registration.
from . import json_fmt, markdown, plain  # noqa: F401

__all__ = ["register_serializer", "serialize", "serializers"]
