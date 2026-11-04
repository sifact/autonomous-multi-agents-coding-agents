Write `solution.py` with a function `normalize_file(path: str) -> bool`.

It cleans the text file at `path` **in place**, working on the raw bytes:

1. If the file starts with the UTF-8 byte order mark (`EF BB BF`), remove that one BOM.
   A BOM-like sequence anywhere else in the file is left alone.
2. Convert every Windows line ending (`\r\n`) to `\n`, and every remaining lone `\r` to `\n`.
3. Change nothing else: no trailing-whitespace trimming, no added or removed final newline,
   and no re-encoding (bytes outside the BOM and line endings stay exactly as they were).

Return `True` if the file's bytes changed, `False` if the file was already clean (in that case
the file is left as it is). An empty file is clean. A path that does not exist raises
`FileNotFoundError`.

The file `sample.txt` in the working directory is already clean.
