Write `solution.py` with a function `find_outliers(path: str) -> dict[str, list[float]]`.

`path` is a CSV file with the header `sensor,value`. The sample file `readings.csv` is in the
working directory. Detect outliers separately for each sensor with the IQR rule:

1. Group rows by `sensor` (exact text). Values that are empty or cannot be parsed as a
   finite number (for example `err`, `nan`, `inf`) are ignored.
2. A sensor with fewer than 4 usable values is skipped entirely.
3. Quartiles use linear interpolation between order statistics (the same as NumPy's
   default). With the sensor's values sorted ascending as `v[0..n-1]`, the quantile for
   fraction `p` is: `pos = (n - 1) * p`, `lo = floor(pos)`,
   `q = v[lo] + (pos - lo) * (v[lo + 1] - v[lo])` (when `pos` is an integer, `q = v[lo]`).
   `Q1` is `p = 0.25`, `Q3` is `p = 0.75`, and `IQR = Q3 - Q1`.
4. A value is an outlier when it is **strictly** below `Q1 - 1.5 * IQR` or **strictly**
   above `Q3 + 1.5 * IQR`. Values exactly on a bound are not outliers.
5. Return `{sensor: [outlier values as floats]}` containing only sensors that have at least
   one outlier. Outlier values are listed in the order they appear in the file (a repeated
   value is listed each time). Sensors appear in order of their first row in the file.
- Do not round anything. A file with no outliers gives `{}`.
- Read the file from the `path` argument, not from a hard-coded name.
