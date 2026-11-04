Write `solution.py` that draws a histogram of exam scores with matplotlib. It must provide
two functions. The environment has no display: do not call `plt.show()` and do not depend
on a GUI backend.

`build_figure(rows, edges=None) -> matplotlib.figure.Figure`

- `rows` is a list of numbers (scores); it may be empty. `edges` is the list of bin edges;
  `None` means `[0, 20, 40, 60, 80, 100]`. It needs at least two values and must be strictly
  increasing, otherwise raise `ValueError`.
- Bins are half-open `[edges[i], edges[i+1])`, except the last bin which also includes its
  upper edge (the same rule as `numpy.histogram`). A score outside `[edges[0], edges[-1]]`
  is not counted in any bin.
- The figure is 8 by 4.5 inches with exactly one Axes holding one bar per bin (also bins with
  a count of 0), in bin order. The bar of bin `i` has height equal to its count, its left
  side is at `edges[i]` and its width is `edges[i+1] - edges[i]` (use `ax.hist` with the
  edges as `bins`, or `ax.bar` with `align="edge"`). The Axes holds no other bars or
  rectangles.
- Title `Exam Scores`, x label `Score`, y label `Students`.

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `student,score`. The sample file
  `scores.csv` is in the working directory. Rows with an empty `score` are skipped; all
  other scores are decimal numbers.
- Build the figure with the default edges and write it to `png_path` as a PNG with
  `dpi=100`.
- Return a dict with exactly these keys:
  - `"counts"`: the list of the bin counts as ints, in bin order;
  - `"edges"`: the list `[0, 20, 40, 60, 80, 100]`;
  - `"outside"`: how many scores fall outside the edges (int);
  - `"mean"`: the mean of all scores, outside ones included, rounded with `round(mean, 2)`,
    or `None` when there are no scores.
