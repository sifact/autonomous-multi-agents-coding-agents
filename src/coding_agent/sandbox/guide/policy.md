# policy.py

Advisory static scan that flags risky constructs in generated code.

- `scan(code)` returns `PolicyFlag(rule, line)` items sorted by line; benign code returns an empty list.
- Rules are `shell_exec` (os.system, subprocess, eval, exec), `network` (socket, urllib, requests, http imports), `destructive_fs` and `fork`.
- `destructive_fs` fires on rmtree/remove/unlink of an absolute-path literal and on `rm -rf /` text found by a line regex.
- Code is only parsed with `ast`, never executed; a syntax error skips the AST pass (no flag) while the regex pass still runs.
- It is a hint only and easy to bypass; the container limits are the real enforcement.
