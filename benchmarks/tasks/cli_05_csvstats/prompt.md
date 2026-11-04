Write `main.py`, a CSV column statistics tool, run as `python main.py FILE --column NAME`.
A sample file `orders.csv` is in the working directory.

- `FILE` is a UTF-8 CSV file (standard `csv` module rules: quoted fields may contain commas).
  It may start with a UTF-8 byte order mark, which must be ignored (use `utf-8-sig`). The
  first record is the header. `NAME` is matched exactly against the header names
  (case-sensitive); if a name occurs twice, the first such column is used.
- Data records are numbered from 1 after the header. Completely blank lines (zero
  characters) are skipped and are not counted; a line with only spaces is a normal record.
  Records whose cell in the column is empty still count for the numbering. A record shorter
  than the header counts as an empty cell for the missing
  columns.
- A cell is stripped of leading and trailing whitespace; an empty cell is skipped. Any other
  cell must parse with `float()` and be finite (`nan` and `inf` are not numbers).
- On success print these lines to standard output, each ending with `\n`, and exit 0:

      count: <n>
      min: <min>
      max: <max>
      mean: <mean>
      median: <median>

  `n` is the number of numeric cells as an integer; the other four values use
  `f"{value:.2f}"`. The median of an even number of values is the mean of the two middle
  values. If there are no numeric cells print only `count: 0`.
- Errors print nothing on standard output, put a message on standard error, and exit with a
  status code:
  - 2: `--column` is missing or has no value, the wrong number of positional arguments, or
    `FILE` cannot be read;
  - 3: a non-empty cell is not a number; the message is exactly
    `error: row <r>: not a number: <cell>` where `<r>` is the record number of the first
    bad cell and `<cell>` is the stripped cell text;
  - 4: the column does not exist, including a file with no header at all; the message is
    `error: no such column: <NAME>`.
