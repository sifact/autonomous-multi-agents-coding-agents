Write `solution.py` with a function
`rename_files(directory: str, pattern: str, replacement: str, apply: bool = False) -> list[tuple[str, str]]`.

It plans (and optionally performs) a bulk rename of the files directly inside `directory`.
The sample directory `photos/` is in the working directory.

1. Only regular files that sit directly in `directory` are considered; subdirectories are not
   entered and are never renamed. Go through the files in plain string order of their names.
2. The new name is `re.sub(pattern, replacement, name)` (case-sensitive, all matches, so
   back-references such as `\1` work). If it equals the old name, the file is skipped and
   does not appear in the result.
3. A new name must never overwrite anything. The set of *taken* names is every file and
   subdirectory name in `directory` before the run plus the new names already assigned
   earlier in this run. If the new name is taken, try `<stem>_1<ext>`, then `<stem>_2<ext>`,
   and so on until a name is free, where `stem, ext = os.path.splitext(new_name)`
   (so a name such as `.txt` has no extension and becomes `.txt_1`).
   (A file keeps its own old name as taken, even when another file is renamed away from it.)
4. Return the list of `(old_name, new_name)` pairs, base names only, in processing order.
5. With `apply=False` (the default, a dry run) nothing on disk changes. With `apply=True`
   the renames are carried out as well; the returned list is the same either way.

If `directory` does not exist, raise `FileNotFoundError`.
