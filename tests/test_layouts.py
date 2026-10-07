"""Tests for layout strategy registry and dispatch."""

from docduck import layouts
from docduck.layouts import MultiColumnLayout, SidebarLayout, SingleColumnLayout


class TestLayoutRegistry:
    def test_builtins_registered(self):
        names = set(layouts.layouts.as_dict().keys())
        assert {"single_column", "multi_column"}.issubset(names)

    def test_for_page_single(self):
        strategy = layouts.for_page(1)
        assert isinstance(strategy, SingleColumnLayout)

    def test_for_page_multi(self):
        strategy = layouts.for_page(3)
        assert isinstance(strategy, MultiColumnLayout)
        assert strategy.n_columns == 3

    def test_for_page_sidebar(self):
        strategy = layouts.for_page(1, layout_name="sidebar")
        assert isinstance(strategy, SidebarLayout)

    def test_sidebar_layout_name_beats_columns(self):
        # layout_name=sidebar should win over n_columns>1
        strategy = layouts.for_page(3, layout_name="sidebar")
        assert isinstance(strategy, SidebarLayout)

    def test_custom_layout_registers(self):
        from docduck.layouts import LayoutStrategy, register_layout

        @register_layout("_test_custom")
        class _Custom(LayoutStrategy):
            def render(self, *a, **kw):
                return []

        try:
            assert "_test_custom" in layouts.layouts.as_dict()
        finally:
            layouts.layouts.unregister("_test_custom")
