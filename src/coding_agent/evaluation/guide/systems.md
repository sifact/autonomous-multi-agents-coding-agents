# systems

The three systems under test (single-shot, single-agent loop, multi-agent graph) behind one `solve(task) -> SystemOutput` contract.

- `SingleShot` makes exactly one model call with the coder prompt and never executes anything, so `first_try_pass` is `None` and the runner grades its single output.
- `SingleAgentLoop` generates, runs the files through the graph's own `execute_files`, and on a non-zero exit feeds truncated stderr back to the same model, stopping on success or after 3 repairs.
- `GraphSystem` builds a fresh `ModelRouter` and `UsageTracker` per task, so tokens and cost are per-run, and reads attempts and runtime errors from the graph's code versions.
- All three get the same task text (`task_prompt`: prompt, starter files, fixture listing) and the same `### FILE:` output format rules, so format failures are not unfairly counted against one system.
- `SystemOutput` fixes the shared meanings: `attempts` = generations, `had_runtime_error` = any non-zero or timed-out run, `fixed` = errored then ended at exit 0 within 3 repairs, `first_files` = the attempt-1 files, `cost_usd` = `None` if unpriced.
