# task.py

Defines the `Task` dataclass and loads task directories from disk.

- `Task` holds id, category, prompt, fixtures, hidden tests, optional starter and reference files.
- `load_task` reads `prompt.md`, `task.toml` (category), and the `fixtures/`, `hidden_tests/`, `starter/`, `reference/` trees as relative-path-to-text dicts.
- A missing `prompt.md` or missing `hidden_tests/` raises a `ValueError` naming the task.
- `starter` is `None` when the task has no `starter/` directory; fixtures and reference default to empty.
- `load_tasks(root)` loads every sub-directory of `root`, sorted by task id.
