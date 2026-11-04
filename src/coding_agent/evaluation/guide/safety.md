# safety.py

Runs every safety case against a sandbox and reports how many were contained.

- `run_case` makes a fresh workspace plus an unmounted host canary directory, then runs the case code in the sandbox.
- A case passes only if its `expect(ExecResult)` holds and, when present, its host-side `post_check` holds too.
- `HostContext` snapshots free disk and existing `coding-agent-*` containers before the run so orphans and disk growth can be measured.
- `run_safety_suite` runs all `SAFETY_CASES` (fork bomb, infinite loop, memory hog, delete outside workspace, network call, disk fill, read host path) in order.
- `SafetyReport` exposes `passed`, `total`, `results` and `pass_rate`; failures carry a `detail` string instead of being hidden.
