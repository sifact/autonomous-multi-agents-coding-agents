# validate.py

Checks that a benchmark task is fair and discriminating before it is used to score systems.

- `validate_task` grades the reference files and requires them to pass the hidden tests; a task with no reference is invalid.
- It grades an empty file set (and the starter files, if any) and requires them to fail, so tests that pass on nothing are caught.
- It requires a non-empty prompt, a category from the allowed set, and no mention of hidden test file names or "hidden tests" in the prompt.
- `count_test_cases` parses the hidden tests with `ast`, expanding literal `parametrize` lists, and requires at least 3 cases so one-assert tests are rejected.
- `validate_all` runs every task and flags duplicate ids, returning a dict of task id to problem list (empty list means valid).
