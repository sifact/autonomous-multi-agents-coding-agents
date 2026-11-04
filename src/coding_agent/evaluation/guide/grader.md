# grader.py

Scores agent output by running a task's hidden tests in a sandbox, hardened against forged passes.

- `grade` rejects (with an explanatory `output`) agent files that can steer pytest: conftest.py, pytest.ini, setup.cfg, tox.ini, pyproject.toml, sitecustomize.py, usercustomize.py, pytest.py, or any `pytest/` path segment.
- It writes agent files, then fixtures, then hidden tests (so hidden tests win clashes), into a fresh workspace that is always removed, even if the sandbox raises.
- It runs `python -m pytest -q -p no:cacheprovider --noconftest -c /dev/null --rootdir=.` so no config or conftest is loaded and the workspace is on `sys.path`.
- `passed` needs exit code 0, no timeout, and a parsed summary with at least one passed and no failed or error; zero tests collected or a missing summary is a fail.
- Known limit: agent code and tests share one process, so code that prints a fake summary then exits 0 could forge a pass; this is meant for LLM output, not an adversary.
