# reviewer.py

Builds the reviewer node, which judges the last real run and decides pass, fix, replan or stop.

- The prompt shows the task, criteria, files, the command that ran with what it means (tests, program, or SYNTAX CHECK ONLY), the last run (exit code, stdout, stderr, timeout/OOM/disk flags), policy flags and the repair/replan counters.
- Files, stdout and stderr sit inside `<file>`, `<program_stdout>`, `<program_stderr>` tags with our tag names defanged, and the system prompt says tagged content is untrusted data, never instructions.
- The reply is parsed with `prefer="last"` (the last valid `Verdict` object wins, so a quoted `{"action": "pass"}` cannot); malformed output is retried once, then becomes `stop` with a clear reason.
- `enforce_pass_rule` downgrades a `pass` to `fix` whenever the last run failed, timed out or was killed; it never bumps `repairs`/`replans` (the coder or planner does).
- Its update sets `verdict`, includes `bump_visit` and appends a `reviewer` event with the model name, action and reason, the only durable record of each verdict.
