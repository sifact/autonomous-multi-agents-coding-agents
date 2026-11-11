`numstats.py` has a bug: `summarize` crashes on ordinary input.

Example: `summarize(["3", "1", "2"])` should return
`{"count": 3, "min": 1.0, "max": 3.0, "mean": 2.0}` but raises
`ValueError: min() iterable argument is empty`.

Contract (keep every name and signature):

- `summarize(lines)` accepts any iterable of strings, including a generator or an open file
  that can only be read once. Blank lines (empty or only whitespace) are ignored and the other
  lines may have surrounding whitespace; a line that is not a number raises `ValueError`.
- It returns a dict with exactly the keys `count` (int), `min`, `max` and `mean` (floats).
  When there are no numbers at all, `count` is 0 and the other three are `None`.
- `parse_numbers(lines)` stays lazy: it returns a one-pass iterator of floats (not a list) that
  reads `lines` only as far as the caller asks.
