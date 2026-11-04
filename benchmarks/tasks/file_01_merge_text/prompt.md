Write `solution.py` with a function `merge_files(paths: list[str], out_path: str) -> int`.

It merges the UTF-8 text files in `paths` into one file, `out_path` (UTF-8, overwritten if it
already exists). The sample files `notes_a.txt` and `notes_b.txt` are in the working directory.

Output format, for the input files in the order given in `paths` (do not sort them):

1. A header line `==> <name> <==`, where `<name>` is the file's base name (no directory part).
2. The file's content, unchanged. If the content is not empty and does not end with a newline,
   add one `\n`. An empty file contributes only its header line.
3. Between two consecutive files, exactly one blank line, added after the unchanged content
   (so content that already ends in a blank line still gets the separator on top of it).
   No blank line after the last file.

Every line of the output ends with `\n`. Input files use `\n` line endings.

- Return the number of files merged. With an empty `paths`, create `out_path` as an empty
  file and return `0`.
- If any input path does not exist, raise `FileNotFoundError` and do not create or modify
  `out_path`.
