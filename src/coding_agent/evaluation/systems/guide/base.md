# base.py

The contract between an eval system and the benchmark runner.

- `SystemOutput` carries files, attempts, usage, cost, wall time, an optional error and the file sets the runner grades (`first_files`, `budget_files`; `None` means same as `files`).
- `attempts` is the number of code generations (1 + repairs); `had_runtime_error` is any execution that exited non-zero or timed out, and a "no files" / "nothing to run" format failure counts as one.
- `fixed` means a runtime error happened and the run ended at exit 0 within `max_repairs` (3) repairs; `first_try_pass` is the system's own first-execution verdict (`None` if it never executes).
- `budget_files` are the files of generation `max_repairs + 1` (or the last one if fewer), so systems with different retry rules are graded at the same budget.
- `attach_partial` stores tokens, cost and wall time already spent on a raised exception so the runner's crash record is not zeroed; `settings_dict` records the run-shaping settings (never the API key).
