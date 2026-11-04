# workspace.py

Helpers for the host-side workspace the sandbox mounts.

- `make_workspace` creates a unique directory under the configured workspace root (inside `$HOME` for Colima).
- The directory is made world-writable so the container's uid 1000 can write to it.
- `write_files` writes a dict of relative paths to files, creating parent directories as world-writable (0777).
- It raises `PathEscapeError` for absolute paths or `..` segments, before writing anything.
- `truncate` keeps the head and tail of long output and inserts a marker saying how many characters were cut.
