Write `solution.py` that draws a stacked bar chart of units sold per quarter and product with
matplotlib. It must provide two functions. The environment has no display: do not call
`plt.show()` and do not depend on a GUI backend.

`build_figure(rows) -> matplotlib.figure.Figure`

- `rows` is a list of `(quarter, product, units)` tuples: two `str` and a number of units
  (0 or more). The same `(quarter, product)` pair may occur several times: add the units
  together. An empty list raises `ValueError`.
- The x categories are the quarters **in order of first appearance** in `rows` (not
  sorted). The series are the products **sorted ascending** (plain string order). A product
  that has no row for a quarter has 0 units there.
- One Axes holds the stacked bars, drawn with one `ax.bar` call per product, in sorted
  product order, with `label` set to the product name. Every product has one bar per quarter,
  also where the units are 0. The first product is at the bottom: the bottom of each bar is
  the sum of the units of the products before it in the same quarter (use `bottom=`).
- A legend with the product names in sorted order. The x tick labels are the quarters in
  their order.
- Title `Units by Quarter`, x label `Quarter`, y label `Units`. Figure size 8 by 5 inches,
  exactly one Axes.

`save_chart(csv_path: str, png_path: str) -> dict`

- `csv_path` is a UTF-8 CSV file with the header `quarter,product,units` (`units` is an
  integer). The sample file `units.csv` is in the working directory. Keep the file order
  when passing the rows to `build_figure`.
- Build the figure with `build_figure` and write it to `png_path` as a PNG with `dpi=100`.
- Return a dict with exactly these keys:
  - `"quarters"`: the quarters in order of first appearance;
  - `"products"`: the products sorted ascending;
  - `"totals"`: the total units of each quarter (ints), in the order of `"quarters"`;
  - `"top_product"`: the product with the most units over all quarters; if several tie, the
    one that comes first in `"products"`.
