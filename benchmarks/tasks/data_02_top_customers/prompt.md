Write `solution.py` with a function `top_customers(path: str, n: int) -> list[tuple[str, float]]`.

`path` is a CSV file with the header `order_id,customer,amount`. The sample file `orders.csv`
is in the working directory.

Return the `n` customers with the highest total spend:

- Sum `amount` per customer (names are compared exactly after stripping surrounding spaces).
- Round each customer's total with Python's `round(total, 2)`.
- Rows whose `amount` is empty are skipped.
- Sort by the rounded total, highest first. Customers with equal rounded totals are ordered
  by name in ascending plain string order (so `"Zed"` comes before `"alice"`).
- Return a list of `(customer, total)` tuples, at most `n` long. If there are fewer than
  `n` customers return all of them. If `n <= 0` or there are no rows, return `[]`.
- Read the file from the `path` argument, not from a hard-coded name.
