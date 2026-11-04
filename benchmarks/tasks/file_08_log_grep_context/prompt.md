Write `solution.py` with a function
`grep_context(path: str, pattern: str, before: int = 0, after: int = 0) -> list[str]`.

It behaves like `grep -n -B<before> -A<after>` on a UTF-8 text file. The sample log `app.log` is
in the working directory.

- The file is split into lines at `\n`; a final `\n` at the end of the file does not create an
  extra empty line. Line numbers start at 1. Lines do not include the `\n`.
- A line is a *match* if `re.search(pattern, line)` finds something (regular expression,
  case-sensitive, applied to the line without its `\n`).
- Output: one string per displayed line, in file order, each line displayed once.
  A match is shown as `"<number>:<text>"`; a context line (not itself a match) as
  `"<number>-<text>"`. For every match, also display the `before` lines above it and the `after`
  lines below it (clipped at the start and end of the file). A line that is a match is always
  shown with `:`, even when it lies in another match's context window.
- Overlapping or directly touching windows merge into one block. Where two displayed blocks
  are separated by at least one hidden line, put a separator element `"--"` between them
  (never at the start or the end of the result).
- No matches (or an empty file) gives `[]`.
- A negative `before` or `after` raises `ValueError`.
