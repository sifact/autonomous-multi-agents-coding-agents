Write `solution.py` that draws a monthly revenue bar chart with matplotlib. It must provide
two functions. The environment has no display: do not call `plt.show()` and do not depend
on a GUI backend.

`build_figure(rows) -> matplotlib.figure.Figure`

- `rows` is a list of `(month, revenue)` tuples: `month` is a unique `str`, `revenue` a
  number. The list may be empty.
- The figure is 8 by 4.5 inches (`figsize=(8, 4.5)`) and has exactly one Axes.
- The Axes holds a vertical bar chart (`ax.bar`) with one bar per row, **in the order of
  `rows`** (never sorted); the bar heights are the revenues.
- The x tick labels are the month names, in the same order. There is no legend.
- Title `Monthly Revenue`, x label `Month`, y label `Revenue (USD)`. These texts are also
  set when `rows` is empty (then the Axes has no bars).

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `month,revenue`. The sample file
  `revenue.csv` is in the working directory. Rows whose `revenue` cell is empty (or only
  whitespace) are skipped;
  all other rows have a numeric revenue and a non-empty month. Keep the rows in file order.
- Build the figure by calling `build_figure` (looked up as a module-level name at call
  time) with the rows, and write the figure it returns to `png_path` as a PNG with
  `dpi=100` (so an 8 by 4.5 inch figure gives 800 by 450 pixels).
- Return a dict with exactly these keys:
  - `"months"`: the number of bars (int);
  - `"total"`: the sum of all revenues, rounded with `round(total, 2)`;
  - `"best_month"`: the month with the highest revenue (the first one in file order if
    several tie), or `None` when there are no rows.
