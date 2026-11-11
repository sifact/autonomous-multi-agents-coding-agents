`runs.py` has bugs in its run-length helpers: the results are wrong whenever the input ends with
the longest or only block, and empty input gives a surprising answer.

Examples: `run_lengths([1, 1, 2, 2, 2])` should return `[(1, 2), (2, 3)]` but returns
`[(1, 2)]`; `longest_run([1, 2, 2, 2])` should be `3` but is `1`; `longest_run([])` should be
`0` but is `None`.

Contract (keep every name and signature):

- `run_lengths(values)` accepts any iterable and returns a list of `(value, length)` tuples, one
  for each block of consecutive equal values (compared with `==`), in order. Every block is
  reported, including the last one and blocks of the value `None`. No values gives `[]`.
- A block is a stretch of directly adjacent equal values: equal values separated by a
  different one belong to different blocks.
- `longest_run(values)` is the length of the longest block, 0 when there are no values; it
  returns an `int` and does not raise for empty input.
- `is_constant(values)` is `True` when there is at most one block (so for empty input and for
  all-equal input) and `False` otherwise.
