Write `solution.py` with a function `find_duplicates(root: str) -> list[list[str]]`.

It finds files under the directory `root` (searched recursively) that have exactly the same
content, regardless of their names. The sample directory `sample/` is in the working directory.

- Two files are duplicates when their bytes are identical. Same size or same name is not
  enough. Empty files are all duplicates of each other.
- Return one group per set of identical files, and only for sets with two or more files.
- Each file is identified by its path relative to `root`, written with `/` as the separator
  (for example `"docs/readme.txt"`). Directories are not files and never appear.
- Order: inside each group the paths are sorted (plain string order); the groups are sorted
  by their first path.
- No duplicates gives `[]`. If `root` does not exist, raise `FileNotFoundError`.
