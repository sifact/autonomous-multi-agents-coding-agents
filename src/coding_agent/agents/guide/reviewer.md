# reviewer.py

Builds the reviewer node, which judges the last real run and decides pass, fix, replan or stop.

- The prompt shows the task, criteria, files, the last run (exit code, stdout, stderr, timeout/OOM/disk flags), policy flags and the repair/replan counters.
- The reply is JSON `{"action", "reason"}` parsed into a `Verdict`; malformed output is retried once, then becomes `stop` with a clear reason.
- `enforce_pass_rule` downgrades a `pass` to `fix` whenever the last run failed, timed out or was killed, so success always rests on a real exit code 0.
- It never bumps `repairs`/`replans`: the router must read pre-bump counts, and the coder or planner applies the bump.
- Its update sets `verdict`, includes `bump_visit` and appends a `reviewer` event with the action and reason, the only durable record of each verdict.
