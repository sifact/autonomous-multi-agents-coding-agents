# validate.py

Checks that a benchmark task is fair and discriminating before it is used to score systems.

- `validate_task` grades the reference (must pass), an empty file set and the starter files (must fail); a task with no reference is invalid.
- It requires a non-empty prompt, a known category, and a difficulty in easy/medium/hard (missing is an error only with `require_difficulty=True`, used for `benchmarks/tasks`).
- The leak check flags hidden test file names, hidden test function names and the phrase "hidden tests" appearing in the prompt.
- `count_test_cases` parses with `ast`, counts only collectible tests (module `test_*` functions, `test_*` methods of `Test*` classes) that contain an assert or `pytest.raises/approx/warns`, and expands literal `parametrize` lists; at least 3 are required.
- `validate_all` runs every task and flags duplicate ids, returning a dict of task id to problem list (empty list means valid).
