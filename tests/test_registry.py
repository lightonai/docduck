"""Tests for the Registry utility."""

import random

import pytest

from docduck.registry import Registry


class TestRegister:
    def test_register_as_function(self):
        r = Registry("widget")
        r.register("a")(lambda: 1)
        assert "a" in r

    def test_register_as_decorator(self):
        r = Registry("widget")

        @r.register("foo", weight=3)
        def fn():
            return 42

        assert r.get("foo")() == 42

    def test_duplicate_register_raises(self):
        r = Registry("widget")
        r.register("a")(lambda: 1)
        with pytest.raises(ValueError, match="already registered"):
            r.register("a")(lambda: 2)

    def test_unregister(self):
        r = Registry("widget")
        r.register("a")(lambda: 1)
        r.unregister("a")
        assert "a" not in r

    def test_set_weight(self):
        r = Registry("widget")
        r.register("a", weight=1)(lambda: 1)
        r.set_weight("a", 5)
        assert r.sample() == "a"

    def test_set_weight_unknown_raises(self):
        r = Registry("widget")
        with pytest.raises(KeyError):
            r.set_weight("missing", 1)


class TestGet:
    def test_get_existing(self):
        r = Registry("widget")
        r.register("a")(lambda: 1)
        assert r.get("a")() == 1

    def test_get_missing_raises(self):
        r = Registry("widget")
        with pytest.raises(KeyError):
            r.get("nope")

    def test_get_or_none(self):
        r = Registry("widget")
        assert r.get_or_none("nope") is None

    def test_len_and_iter(self):
        r = Registry("widget")
        r.register("a")(1)
        r.register("b")(2)
        assert len(r) == 2
        assert list(r) == ["a", "b"]

    def test_items(self):
        r = Registry("widget")
        r.register("a")(1)
        r.register("b")(2)
        assert r.items() == [("a", 1), ("b", 2)]


class TestSample:
    def test_empty_raises(self):
        r = Registry("widget")
        with pytest.raises(ValueError):
            r.sample()

    def test_single_item(self):
        r = Registry("widget")
        r.register("only")(1)
        assert r.sample() == "only"

    def test_weighted_distribution_approximate(self):
        r = Registry("widget")
        r.register("rare", weight=1)(1)
        r.register("common", weight=99)(2)

        counts = {"rare": 0, "common": 0}
        rng = random.Random(0)
        for _ in range(1000):
            counts[r.sample(rng=rng)] += 1
        assert counts["common"] > 900

    def test_exclude(self):
        r = Registry("widget")
        r.register("a")(1)
        r.register("b")(2)
        # Exclude "a": should always return "b"
        for _ in range(20):
            assert r.sample(exclude={"a"}) == "b"

    def test_exclude_all_raises(self):
        r = Registry("widget")
        r.register("a")(1)
        with pytest.raises(ValueError):
            r.sample(exclude={"a"})

    def test_pick_returns_pair(self):
        r = Registry("widget")
        r.register("a")(42)
        name, item = r.pick()
        assert name == "a"
        assert item == 42

    def test_zero_weights_fallback_to_choice(self):
        r = Registry("widget")
        r.register("a", weight=0)(1)
        r.register("b", weight=0)(2)
        # With all zero weights, sample() falls back to choice()
        rng = random.Random(0)
        # No exception, returns one of them
        assert r.sample(rng=rng) in {"a", "b"}


class TestBulkConfig:
    def test_set_weights(self):
        r = Registry("widget")
        r.register("a", weight=1)(1)
        r.register("b", weight=1)(2)
        r.set_weights({"a": 10, "b": 1})
        rng = random.Random(0)
        counts = {"a": 0, "b": 0}
        for _ in range(500):
            counts[r.sample(rng=rng)] += 1
        assert counts["a"] > counts["b"]

    def test_set_weights_ignores_unknown(self):
        r = Registry("widget")
        r.register("a")(1)
        # Should not raise even though "missing" isn't registered
        r.set_weights({"a": 5, "missing": 99})

    def test_as_dict(self):
        r = Registry("widget")
        r.register("a")(1)
        r.register("b")(2)
        assert r.as_dict() == {"a": 1, "b": 2}
