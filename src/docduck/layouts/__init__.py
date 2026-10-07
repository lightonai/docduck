"""Page layout strategies: single-column, multi-column, sidebar."""

from ._base import LayoutStrategy, layouts, register_layout

# isort: split
from . import multi_column, sidebar, single_column  # noqa: F401

MultiColumnLayout = multi_column.MultiColumnLayout
SidebarLayout = sidebar.SidebarLayout
SingleColumnLayout = single_column.SingleColumnLayout


def for_page(n_columns: int, layout_name: str | None = None) -> LayoutStrategy:
    """Pick a strategy. `layout_name` wins over `n_columns` when both are set."""
    if layout_name == "sidebar":
        return SidebarLayout()
    if layout_name == "multi_column" or n_columns > 1:
        return MultiColumnLayout(n_columns=max(n_columns, 2))
    return SingleColumnLayout()


__all__ = [
    "LayoutStrategy",
    "MultiColumnLayout",
    "SidebarLayout",
    "SingleColumnLayout",
    "for_page",
    "layouts",
    "register_layout",
]
