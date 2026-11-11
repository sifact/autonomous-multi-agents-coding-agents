# report.py

Renders the ablation table and the text around it from result files.

- `render_markdown(results, by_category=, all_runs=, tasks_dir=)` makes one row per system or graph variant (single_shot, single_agent, graph, then variants A-Z), taking the latest file per variant unless `all_runs` adds one row per file with timestamp, short git SHA and a dirty flag.
- Columns are Tasks, Runs, pass@1, Final pass, Budget-matched pass, Runtime errors fixed (<=3 repairs), Mean attempts, Mean tokens, Mean cost, Mean wall time and Errors; percentages have one decimal and `Final pass*` carries a footnote that it is retry-confounded.
- Unknown values print `n/a`, never 0: no runtime errors, an unpriced model, all runs crashed; a partly priced cost shows "k of n priced".
- The footer repeats the budgets, models per role (a role the variant skipped shows `skipped`), seed, repeats and the runner's budget note once, plus a "How to read this table" guide, so the honesty caveat travels with the numbers.
- The output contains no clock time of its own, so writing it into the README twice gives identical text; it ends with the `compare` verdict and optionally the category and difficulty breakdown.
