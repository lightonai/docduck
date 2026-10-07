"""Generic named registry for weighted-choice dispatch.

Used throughout the codebase to replace hand-rolled dict+weights patterns.
Blocks, form fields, page chrome, text/math/table generators all register
into their own Registry instance.

Usage:
    blocks = Registry("block")

    @blocks.register("heading", weight=6)
    def draw_heading(ctx, ...): ...

    # Look up by name
    fn = blocks.get("heading")

    # Sample one weighted-randomly
    name = blocks.sample()
    fn = blocks.get(name)

    # Or in one step
    name, fn = blocks.pick()
"""

import random
from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A named, weighted registry of items (functions, classes, anything).

    Items are stored in insertion order. Each item has an optional `weight`
    used by `sample()`. `register()` can be used as a decorator.
    """

    def __init__(self, kind: str = "item"):
        """Create a registry. `kind` appears in error messages."""
        self.kind = kind
        self._items: dict[str, T] = {}
        self._weights: dict[str, float] = {}

    # -- mutation ------------------------------------------------------------

    def register(self, name: str, weight: float = 1.0):
        """Decorator / function form. Returns the registered item unchanged.

        Example:
            @blocks.register("heading", weight=6)
            def draw_heading(...): ...
        """

        def decorator(item: T) -> T:
            if name in self._items:
                raise ValueError(f"{self.kind} {name!r} already registered")
            self._items[name] = item
            self._weights[name] = float(weight)
            return item

        return decorator

    def set_weight(self, name: str, weight: float) -> None:
        if name not in self._items:
            raise KeyError(f"{self.kind} {name!r} not registered")
        self._weights[name] = float(weight)

    def unregister(self, name: str) -> None:
        self._items.pop(name, None)
        self._weights.pop(name, None)

    # -- access --------------------------------------------------------------

    def get(self, name: str) -> T:
        if name not in self._items:
            raise KeyError(f"{self.kind} {name!r} not registered")
        return self._items[name]

    def get_or_none(self, name: str) -> T | None:
        return self._items.get(name)

    def names(self) -> list[str]:
        return list(self._items.keys())

    def items(self) -> list[tuple[str, T]]:
        return list(self._items.items())

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    # -- sampling ------------------------------------------------------------

    def sample(self, exclude: set[str] | None = None, rng: random.Random | None = None) -> str:
        """Return a name sampled by weight, optionally excluding some."""
        if not self._items:
            raise ValueError(f"no {self.kind}s registered")
        r = rng or random
        names = [n for n in self._items if not exclude or n not in exclude]
        if not names:
            raise ValueError(f"all {self.kind}s excluded")
        weights = [self._weights[n] for n in names]
        if sum(weights) == 0:
            return r.choice(names)
        return r.choices(names, weights=weights, k=1)[0]

    def pick(
        self, exclude: set[str] | None = None, rng: random.Random | None = None
    ) -> tuple[str, T]:
        """Sample a (name, item) pair."""
        name = self.sample(exclude=exclude, rng=rng)
        return name, self._items[name]

    # -- bulk config ---------------------------------------------------------

    def set_weights(self, weights: dict[str, float]) -> None:
        """Override all weights from a dict. Unknown keys are silently ignored
        (useful for YAML config where a user may reference unregistered blocks).
        """
        for name, w in weights.items():
            if name in self._items:
                self._weights[name] = float(w)

    def as_dict(self) -> dict[str, T]:
        """Return a snapshot of the registry as a plain dict."""
        return dict(self._items)
