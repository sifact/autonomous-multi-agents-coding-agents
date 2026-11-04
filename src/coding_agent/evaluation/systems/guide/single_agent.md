# single_agent.py

Baseline 2: one agent that generates, runs its code, and repairs with the same model.

- Sends one prompt (task, starter files, fixture previews), then runs the files through the graph's own `execute_files`, with fixtures written into the workspace.
- On a non-zero exit or timeout it feeds the truncated, untrusted-tagged stdout/stderr back to the same model and asks for a fix.
- It stops on exit 0 or after `max_repairs` repairs (default `settings.max_repairs`, 3), so it makes at most 4 generations.
- Reports attempts, `had_runtime_error`, `fixed`, the system's own `first_try_pass`, summed usage and cost from `model_name`.
- If anything raises mid-run, the tokens spent so far are attached to the exception for the runner's crash record.
