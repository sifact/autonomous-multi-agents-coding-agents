# grader.py

Scores agent output by running a task's hidden tests in a sandbox.

- `grade(task, files, sandbox)` makes a fresh workspace per call and removes it afterwards.
- It writes agent files first, then fixtures, then hidden tests, so hidden tests always win on path clashes.
- It runs `pytest -q` through the given `Sandbox`, so any backend (Docker or a fake) works.
- `passed` is true only when the exit code is 0 and the run did not time out.
- `GradeResult.output` is stdout plus stderr, truncated so huge logs cannot flood the caller.
