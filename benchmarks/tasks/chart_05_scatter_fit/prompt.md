Write `solution.py` that draws a scatter plot with a least-squares fit line using matplotlib.
It must provide two functions. The environment has no display: do not call `plt.show()` and
do not depend on a GUI backend.

`build_figure(rows) -> matplotlib.figure.Figure`

- `rows` is a list of `(x, y)` number pairs (hours studied, exam score). The ordinary
  least-squares line `y = slope * x + intercept` is fitted through all points
  (`slope = Sxy / Sxx`, with `Sxx = sum((x - mean_x)**2)` and
  `Sxy = sum((x - mean_x) * (y - mean_y))`). If there are fewer than 2 points, or all `x`
  are equal, raise `ValueError`.
- The figure is 7 by 5 inches with exactly one Axes. That Axes holds:
  1. exactly one scatter collection (`ax.scatter`), label `Data`, whose offsets are the
     points in the order of `rows` (do not sort them);
  2. exactly one line (`ax.plot`), label `Fit`, that goes from `min(x)` to `max(x)`:
     its x data is `[min_x, max_x]` and its y data is the fitted `y` at these two `x`.
- A legend with the entries `Data` and `Fit`, in that order.
- Title `Study Hours vs Exam Score`, x label `Hours studied`, y label `Exam score`.

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `hours,score`. The sample file `study.csv`
  is in the working directory. Rows where either cell is empty are skipped; the other rows
  are decimal numbers. Keep the rows in file order.
- Build the figure by calling `build_figure` (looked up as a module-level name at call
  time) with the rows, and write it to `png_path` as a PNG with `dpi=100`. The errors of
  `build_figure` propagate and no PNG has to be written then.
- Return a dict with exactly these keys:
  - `"n"`: the number of points used (int);
  - `"slope"` and `"intercept"` of the fitted line, each rounded with `round(value, 3)`;
  - `"r_squared"`: the coefficient of determination `1 - SSres / SStot` rounded with
    `round(value, 3)`, where `SSres = sum((y - fitted)**2)` and `SStot = sum((y - mean_y)**2)`;
    when all `y` are equal (`SStot == 0`) it is `1.0`.
