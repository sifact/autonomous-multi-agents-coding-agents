Write `solution.py` with a function `count_levels(path: str) -> dict[str, int]`.

`path` is a plain-text application log. The sample file `app.log` is in the working
directory. A log entry is a line that starts with a timestamp and a level in square brackets:

    2024-03-01 12:00:01 [INFO] request 0 handled

Precisely, an entry line starts with `YYYY-MM-DD HH:MM:SS ` followed by `[LEVEL]` where
`LEVEL` is exactly one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (upper case).

Return how many entries there are per level:

- Only the level directly after the timestamp counts. Text such as `[ERROR]` later in the
  message does not.
- Lines that are not entries (stack-trace lines, blank lines, lower-case or unknown levels)
  are ignored.
- The result always contains all five levels, with `0` for absent ones, in the order
  `DEBUG, INFO, WARNING, ERROR, CRITICAL`.
- Read the file from the `path` argument, not from a hard-coded name.
