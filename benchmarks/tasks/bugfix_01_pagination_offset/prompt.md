`pagination.py` has a bug: `get_page` returns the wrong items, as if every page were shifted
by one page.

Example: with `items = list(range(1, 26))` and 10 items per page, `get_page(items, 1, 10)` should
return `[1, 2, ..., 10]` but returns `[11, 12, ..., 20]`, and `get_page(items, 3, 10)` returns
`[]` instead of `[21, 22, 23, 24, 25]`.

Contract (keep every name and signature, including the default `per_page=10`):

- Pages are numbered from 1. Page N holds the N-th block of `per_page` items, in the original
  order. The last page may be shorter, and a page past the end is the empty list.
- `get_page` returns a new list and never modifies `items`.
- `page < 1` or `per_page < 1` raises `ValueError`.
- `page_count(total_items, per_page)` already works and must keep working (no items means
  zero pages).
