`leaderboard.py` has a bug: players with the same number of points come out in the wrong
order.

Example: `rank([("bo", 10), ("al", 10), ("cy", 12)])` should return
`[("cy", 12), ("al", 10), ("bo", 10)]` but returns `[("cy", 12), ("bo", 10), ("al", 10)]`.

Contract (keep every name and signature):

- `rank(scores)` takes a list of `(name, points)` pairs and returns a new list of the same
  pairs: more points first (points may be negative), and players with equal points ordered by
  name in plain string order (code point order, so `"Zed"` comes before `"al"`). The input
  list is never modified, and identical pairs may appear more than once.
- `top_names(scores, n)` returns the names of the first `n` entries of `rank(scores)`; if there
  are fewer than `n` players, all of them; `n == 0` gives `[]`.
- `format_board(scores)` returns one line per entry of `rank(scores)` in the form
  `"<position>. <name> - <points>"`, joined with `"\n"` and no trailing newline, positions
  counting 1, 2, 3... even for tied players. No players gives `""`.
