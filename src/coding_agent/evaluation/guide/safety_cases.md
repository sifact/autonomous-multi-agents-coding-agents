# safety_cases.py

The adversarial programs the sandbox must contain, and how each is judged.

- `SafetyCase` pairs program code with `expect(ExecResult)` and small `Limits` (5s, 64 MB) so the suite is fast.
- `fork_bomb` must hit the pids limit (prints LIMITED, not UNBOUNDED); `memory_hog` must be stopped by the memory limit (never prints ALLOCATED); `infinite_loop` must time out.
- `delete_outside_workspace` tries to remove `/usr` and a host canary, then prints whether the sentinel survived; a positive control checks `/usr`, `/etc` and `/` are read-only while `/tmp` and the workspace stay writable.
- `network_call` needs a blocked connect and only `lo` in `/sys/class/net`; `disk_fill` writes 8 MB files so only the disk watcher stops it; `read_host_path` probes the real host workspace and canary paths.
- Host-only checks live in `post_check(HostContext)`: no new `coding-agent-*` containers, canary intact, final workspace size near disk_mb and a loose 200 MB free-disk backstop.
