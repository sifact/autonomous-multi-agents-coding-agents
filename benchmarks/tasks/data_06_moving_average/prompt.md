Write `solution.py` with a function
`moving_average(path: str, window: int) -> list[dict]`.

`path` is a CSV file with the header `date,close` (one row per day, in date order). The
sample file `prices.csv` is in the working directory.

Compute a trailing simple moving average of `close`:

1. First drop every row whose `close` is empty (it is as if that day does not exist).
2. For each remaining row, if at least `window` rows (including that row) are available up
   to and including it, output one dict `{"date": <date string>, "ma": <float>}` where `ma`
   is the mean of the last `window` closes, rounded with Python's `round(value, 2)`.
   Rows with fewer than `window` rows available produce no output.
3. Output keeps file order. If the file has fewer than `window` usable rows, return `[]`.
4. If `window < 1`, raise `ValueError`.
- Read the file from the `path` argument, not from a hard-coded name.
