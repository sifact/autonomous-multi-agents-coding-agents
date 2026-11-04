Write `solution.py` with a function `monthly_revenue(path: str) -> dict[str, float]`.

`path` is a CSV file with the header `date,product,quantity,unit_price`. The sample file
`sales.csv` is in the working directory. `date` is `YYYY-MM-DD`, `quantity` is an integer
and `unit_price` is a decimal number.

Return the total revenue per calendar month:

- The key is the month as `"YYYY-MM"`; the value is the sum of `quantity * unit_price` for
  all rows of that month.
- Round each month's total once, after summing, with Python's `round(total, 2)`.
- Skip any row where `quantity` or `unit_price` is empty. A month that has no usable rows
  does not appear in the result.
- The dict keys must be in ascending month order.
- A file with only the header row gives `{}`.
- Read the file from the `path` argument, not from a hard-coded name.
