# executor.py

Builds the executor node, which runs the current files in a fresh sandbox workspace and records the result.

- `choose_command` runs `python -m pytest -q` when any test file exists (main.py is then not run, so CLIs needing arguments don't false-fail), else `python main.py`, else `python -m py_compile` over every module; `describe_command` states what each proves for the reviewer.
- Each run gets a new workspace (`make_workspace`) written with `write_files` and always removed in a `finally`.
- Any file-write error on model-chosen paths (`PathEscapeError` or `OSError`: '' or '.', a file and a directory with one name), no files, or no Python files become a failed `ExecResult` (exit code 1, readable stderr) for the reviewer; Docker or other infrastructure errors from `sandbox.run` propagate, since the coder cannot fix them.
- `policy_flags` scans every `.py` file with the advisory `scan`; flags go into the code version and the event, and the reviewer sees them.
- stdout and stderr are truncated to 20,000 characters each before storing `last_exec` and appending a `code_versions` entry (command, exit code, timeout/OOM/disk flags, flags); no counters are changed.
