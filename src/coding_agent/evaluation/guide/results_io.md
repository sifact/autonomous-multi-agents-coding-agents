# results_io.py

Loads benchmark result JSON files into typed `ResultFile` objects for the report.

- `load_results(dir_or_paths, on_warning=)` reads every `*.json` in a directory or the listed files and returns the usable ones.
- Valid JSON that is not result-shaped (no `system` and `records`) is ignored silently; invalid JSON, empty records, a bad timestamp or malformed records are skipped with a clear warning naming the file.
- Metrics are recomputed from the records with `aggregate`, so the table always agrees with the records and the stored `metrics` block is not trusted.
- `variant` defaults to `full` for older files; `variant_label` turns it into `graph`, `graph (no planner)`, `graph (no architect)` or `graph (all strong)`.
- `select_latest` keeps the newest file per (system, variant) and returns them in the fixed report order.
