# architect.py

Builds the architect node, which decides which files the coder must write.

- `make_architect(model)` returns a node that asks the "architect" model for JSON `{"files": [{"path", "purpose"}]}`.
- The reply is validated with the `Layout` schema (at least one file) and stored as `layout` strings like `"main.py: reads the CSV"`.
- The prompt fixes the conventions the executor relies on: `main.py` as entry point, tests in `test_*.py`, no network, only the sandbox's libraries.
- Malformed JSON is retried once; after two failures the layout falls back to `["main.py"]` and the error is recorded in the event.
- It never touches counters; its update is `layout`, `bump_visit` and one `architect` event with token counts.
