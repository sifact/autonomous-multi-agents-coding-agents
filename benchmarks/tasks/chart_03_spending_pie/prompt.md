Write `solution.py` that draws a pie chart of spending by category with matplotlib. It must
provide two functions. The environment has no display: do not call `plt.show()` and do not
depend on a GUI backend.

`build_figure(rows) -> matplotlib.figure.Figure`

- `rows` is a list of `(category, amount)` tuples with unique `str` categories and amounts
  greater than 0. An empty list raises `ValueError`.
- Let `total` be the sum of the amounts. A category whose share `amount / total` is
  **strictly less than 0.05** is *small*; a share of exactly 0.05 is not small. All small
  categories are merged into one slice labelled `Other` whose amount is their sum (even if
  that sum is 5% or more). If there are no small categories there is no `Other` slice.
- Slice order: the remaining categories by amount descending, ties broken by category name
  ascending (plain string order); the `Other` slice, if any, always comes last.
- The figure is 8 by 6 inches with exactly one Axes holding the pie, drawn with `ax.pie`
  using the category names as `labels` and `autopct` so that every wedge has two texts: its
  label and its percentage `f"{share * 100:.1f}%"` (for example `27.5%`). The wedge angle is
  `360 * amount / total` degrees. No legend.
- Title `Spending by Category`.

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `category,amount`; `amount` is a positive
  decimal number. The sample file `spend.csv` is in the working directory. The same category
  may appear on several rows: add its amounts together before charting (a category keeps
  the position of its first appearance in the aggregated list given to `build_figure`).
- Build the figure with `build_figure` and write it to `png_path` as a PNG with `dpi=100`.
- Return a dict with exactly these keys:
  - `"total"`: the sum of all amounts, `round(total, 2)`;
  - `"slices"`: a list with one `(label, percent)` pair (a tuple or a list) per wedge, in
    wedge order, where `percent` is `round(100 * amount / total, 1)` of that wedge.
