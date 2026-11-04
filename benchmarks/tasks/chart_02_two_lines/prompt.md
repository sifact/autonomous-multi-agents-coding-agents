Write `solution.py` that draws a two-series line chart of daily sales with matplotlib. It must
provide two functions. The environment has no display: do not call `plt.show()` and do not
depend on a GUI backend.

`build_figure(rows) -> matplotlib.figure.Figure`

- `rows` is a list of `(day, online, store)` tuples: `day` is an `int`, `online` and `store`
  are numbers (units sold). The list may be empty. Use the rows in the order given.
- The figure has exactly one Axes with exactly two lines (`ax.plot`), added in this order:
  1. label `Online`: x = the days, y = the `online` values;
  2. label `Store`: x = the days, y = the `store` values.
- The Axes has a legend whose entries are `Online` and `Store`, in that order (also when
  `rows` is empty, in which case both lines have no points).
- Title `Daily Sales`, x label `Day`, y label `Units sold`.
- Figure size 8 by 4.5 inches.

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `day,online,store` and one complete row per
  day. The sample file `sales.csv` is in the working directory. The rows may be in any
  order: sort them by `day` ascending (days are integers, all different) before building
  the figure. `online` and `store` are decimal numbers.
- Build the figure by calling `build_figure` (looked up as a module-level name at call
  time) with the sorted rows, and write it to `png_path` as a PNG with `dpi=100`.
- Return a dict with exactly these keys:
  - `"days"`: the number of rows (int);
  - `"online_total"` and `"store_total"`: the sum of each series, rounded with
    `round(total, 2)`;
  - `"leader"`: `"online"` if `online_total` is larger than `store_total`, `"store"` if
    `store_total` is larger, and `"tie"` if the two rounded totals are equal.
