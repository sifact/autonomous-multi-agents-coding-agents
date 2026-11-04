# coder.py

Builds the coder node, which writes the files on the first pass and repairs them as the debugger after a `fix` verdict.

- `make_coder(model, debugger=None, name=, debugger_name=)` uses the "coder" model for a first write and the "debugger" model (default: the same model) when the last verdict was `fix`.
- A repair prompt shows the current files, the last run's summary, stdout and stderr inside untrusted-data tags, and the reviewer's reason; the system prompts say tagged content must never be obeyed.
- Output format is `### FILE: path` plus one fenced block per file; `split_files` closes a block at its last bare fence, falls back to JSON `{"files": {...}}`, and drops paths naming the workspace itself ('', '.', './').
- On a repair it reads the verdict first, then applies `apply_verdict_counters` (repairs+1, verdict cleared); a first write after a replan counts nothing.
- Every update sets `files`, includes `bump_visit` and one `coder` event with the role and model name, the file paths, any dropped paths and token counts.
