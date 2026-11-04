# docker_sandbox.py

Runs a command in a locked-down, throwaway Docker container and returns an `ExecResult`.

- Builds a `docker run` with non-root user, `--cap-drop ALL`, `no-new-privileges`, read-only root fs and a `/tmp` tmpfs.
- Applies memory, cpu, pids limits and `--network none` unless `Limits.network` is set.
- Bind-mounts the workspace at `/workspace` (cwd) with `HOME=/tmp` and `MPLCONFIGDIR=/tmp/mpl`.
- Enforces `disk_mb` with `--ulimit fsize`, a polling watcher that kills the container, and a post-run size check.
- Uses a unique container name and always `docker kill`/`rm`s it, so timeouts and errors leave no orphans.
