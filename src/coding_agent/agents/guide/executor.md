# executor.py

Builds the executor node, which runs the current files in a fresh sandbox workspace and records the result.

- `choose_command` runs `python -m pytest -q` when any test file exists, else `python main.py`, else `python -m py_compile` over every module.
- Each run gets a new workspace (`make_workspace`) written with `write_files` and always removed in a `finally`.
- A path that escapes the workspace, no files, or no Python files become a failed `ExecResult` (exit code 1, readable stderr) for the reviewer instead of a crash.
- `policy_flags` scans every `.py` file with the advisory `scan`; flags go into the code version and the event, and the reviewer sees them.
- stdout and stderr are truncated to 20,000 characters each before storing `last_exec` and appending a `code_versions` entry; no counters are changed.
