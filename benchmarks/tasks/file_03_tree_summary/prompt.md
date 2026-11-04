Write `solution.py` with a function `summarize_tree(root: str) -> list[dict]`.

It walks the directory `root` recursively (every subdirectory, including hidden ones) and
summarises the regular files by extension. The sample directory `site/` is in the working
directory.

Return one dict per extension, with exactly these keys:

- `"ext"`: the extension in lower case including the dot (`"report.PDF"` gives `".pdf"`).
  Only the last suffix counts (`"pack.tar.gz"` gives `".gz"`). A file with no extension,
  including a dot-file such as `.gitignore`, uses the label `"(none)"`.
- `"count"`: how many files have that extension (an `int`).
- `"bytes"`: the total size in bytes of those files (an `int`).

Sort the list by `bytes` descending; when two extensions have the same total, by `ext`
ascending (plain string order). Directories are not counted. An empty directory gives `[]`.
If `root` does not exist, raise `FileNotFoundError`.
