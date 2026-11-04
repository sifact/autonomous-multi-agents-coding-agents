# safety_cases.py

The adversarial programs the sandbox must contain, and how each is judged.

- `SafetyCase` pairs program code with `expect(ExecResult)` and small `Limits` (5s, 64 MB) so the suite is fast.
- `fork_bomb`, `infinite_loop` and `memory_hog` check process, time and memory containment.
- `delete_outside_workspace` tries to remove `/usr` and a host canary, then prints whether the `/usr/bin/env` sentinel survived.
- `network_call`, `disk_fill` and `read_host_path` check no network, a bounded disk and no `/Users` mount.
- Host-only checks live in `post_check(HostContext)`: no new `coding-agent-*` containers, canary intact, free-disk drop under 200 MB.
