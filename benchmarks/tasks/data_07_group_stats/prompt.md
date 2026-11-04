Write `solution.py` with a function `group_stats(path: str) -> dict[str, dict]`.

`path` is a CSV file with the header `team,score`. The sample file `scores.csv` is in the
working directory. `score` is a number (it may be a decimal) or empty.

Return statistics per team, as `{team: {"count": int, "missing": int, "mean": float | None}}`:

- `count`: number of rows of that team with a score.
- `missing`: number of rows of that team whose `score` is empty or only whitespace.
- `mean`: the mean of the team's scores rounded with `round(mean, 2)`, or `None` when the
  team has no scores (`count == 0`). Missing scores are not treated as zero.
- A row whose `team` is empty or only whitespace belongs to the team `"unknown"`. Team
  names are stripped of surrounding whitespace.
- Teams appear in the result in ascending plain string order of the team name (`"unknown"`
  is sorted like any other name). A team that only has missing scores is still included.
- A file with only the header row gives `{}`.
- Read the file from the `path` argument, not from a hard-coded name.
