Write `main.py`, a log level filter, run as `python main.py [--min-level LEVEL] [--summary]
[FILE]`. A sample log `app.log` is in the working directory.

Input is UTF-8 text from `FILE`, or from standard input when `FILE` is omitted or is `-`.
Lines end at `\n` only (a final `\n` does not start another line).

- The levels, lowest to highest, are `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`.
- An *entry line* starts with a timestamp of the form `dddd-dd-dd dd:dd:dd` (ASCII digits
  only; the values are not checked, so `2024-13-45 99:99:99` is fine), then one space, then
  a level name written exactly in upper case, which is followed by a single space or by the
  end of the line. Everything after that is the free-text message and may be empty.
- Every other line (a stack trace, a blank line, a line whose level is lower case or longer
  such as `ERRORS`, a line with two spaces before the level, ...) is a *continuation line*
  of the closest entry line above it. Continuation lines before the first entry line belong
  to no entry: they are never printed and never counted.
- `--min-level LEVEL` (default `DEBUG`) selects the entries whose level is at least LEVEL.
  LEVEL is matched case-insensitively (`warn` works). A continuation line is selected when
  its entry is selected.
- Without `--summary`: print every selected line (entry lines and their continuation lines)
  unchanged, in input order, each followed by `\n`.
- With `--summary`: print nothing else, only one line `<LEVEL>: <count>` for each level that
  has at least one selected entry, from lowest to highest level. Only entry lines are counted.
- Exit status 0 if at least one entry was selected. If no entry was selected (including
  empty input) nothing is printed and the exit status is 1. In both cases output is
  produced only as described above.
- Errors print nothing on standard output, put a message on standard error and exit with
  status 2 for an unknown level name, a missing option value, an unknown option or more than
  one `FILE`, and with status 3 for a `FILE` that cannot be read or is not valid UTF-8.
