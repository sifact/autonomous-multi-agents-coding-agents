"""Helpers for splitting a list of items into pages for display."""
import math


def _check_per_page(per_page: int) -> None:
    if per_page < 1:
        raise ValueError("per_page must be at least 1")


def page_count(total_items: int, per_page: int) -> int:
    """Number of pages needed to show total_items (no items need no pages)."""
    _check_per_page(per_page)
    return math.ceil(total_items / per_page)


def get_page(items: list, page: int, per_page: int = 10) -> list:
    """Return the items shown on the given page."""
    _check_per_page(per_page)
    if page < 1:
        raise ValueError("page numbers start at 1")
    start = page * per_page
    return items[start:start + per_page]
