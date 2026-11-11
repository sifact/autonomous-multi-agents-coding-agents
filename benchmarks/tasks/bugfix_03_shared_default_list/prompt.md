`logscan.py` has a bug: `collect_problems` remembers lines from earlier calls.

Example: `collect_problems(["ERROR disk full", "INFO started"])` returns `["ERROR disk full"]`
the first time. Calling it again with `["WARN low memory"]` should return `["WARN low memory"]`
but returns `["ERROR disk full", "WARN low memory"]`.

Contract (keep every name and signature; `found` stays an optional second argument):

- A line is a problem when its first word (after stripping surrounding whitespace) is exactly
  `WARN` or `ERROR`; `WARNING ...` and `INFO ...` lines are not. The stripped line is kept,
  in input order.
- When `found` is left out, each call starts from a brand new empty list and returns it.
- When a list is passed as `found`, the problems are appended to that list (its existing
  entries stay in place) and that same list object is returned.
- `count_by_level` already works and must keep working.
