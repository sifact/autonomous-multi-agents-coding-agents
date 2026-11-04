# report.py

Turns the final graph state into the FinalReport returned to callers.

- `build_report` marks success only when the final verdict is `pass`, which the reviewer allows only after a run with exit code 0.
- A failed run's explanation starts with `stop_reason` (repair limit, replan limit, step budget or reviewer stop) and the last run's summary.
- `last_error_line` quotes the last non-blank error line (the exception line of a traceback), read from stderr or, for pytest, from stdout.
- The error tail is capped at 500 characters, so a huge traceback never bloats the report.
- `run_usage` sums the token counts recorded on node events, so usage is per run even when one tracker is shared across many runs.
