# breakdown.py

Optional final-pass breakdown by task category and by difficulty.

- Reads `task.toml` metadata through the existing task loader (`load_tasks`) from the benchmark task directory.
- `render_breakdown` builds two tables, one row per category or difficulty and one column per displayed system or file, each cell showing the final pass rate and the number of runs.
- Task ids missing from the task directory land in an `unknown` group, explained in a footnote when it appears; tasks with no difficulty land in `unspecified`.
- A cell with no runs prints `n/a`.
- If the task directory is missing or unreadable, it returns a one-line "Breakdown skipped" note instead of failing the report.
