Write `solution.py` with a function `split_csv(path: str, rows_per_chunk: int, out_dir: str) -> list[str]`.

It splits the UTF-8 CSV file `path` (first row is the header) into several smaller CSV files in
the directory `out_dir`. The sample file `orders.csv` is in the working directory.

- Each chunk file holds the header row followed by at most `rows_per_chunk` data rows, taken in
  file order; every chunk except possibly the last holds exactly `rows_per_chunk` data rows.
  A "row" is one CSV record, so a quoted field that contains a line break is still one row.
- Chunk files are named `<stem>_part<NNN>.csv` where `<stem>` is the input file's base name
  without its last extension (`my.data.csv` gives `my.data`) and `NNN` is the chunk number
  starting at 1, zero-padded to 3 digits (`orders_part001.csv`, `orders_part002.csv`, ...).
- Write the chunks with the standard `csv` module's default quoting, `\n` as the line
  terminator, and UTF-8 encoding. Fields must survive a round trip through `csv.reader`
  unchanged. Create `out_dir` (and missing parents) if it does not exist.
- Return the paths of the chunk files written, in chunk order, each as
  `os.path.join(out_dir, <file name>)`.
- A file with only a header row, or an empty file, gives `[]` and writes no chunk files.
- `rows_per_chunk < 1` raises `ValueError`. A missing `path` raises `FileNotFoundError`.
