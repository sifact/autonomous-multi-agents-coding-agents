"""Executor node: runs the current files in a fresh sandbox workspace and records the result.

Command choice (from the files, not from a model): any test file
(``test_*.py`` or a ``tests/`` dir) -> ``python -m pytest -q`` (tests are the
stronger check, and a CLI ``main.py`` may need arguments); else ``main.py`` ->
``python main.py``; else ``python -m py_compile`` over every module, so a
library-only answer is at least syntax-checked. No model is called here.
"""
from __future__ import annotations

import dataclasses
import shutil
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

from coding_agent.agents.context import event, exec_summary
from coding_agent.agents.prompts import DEFAULT_ENTRYPOINT, MAX_EXEC_OUTPUT_CHARS
from coding_agent.config import Settings
from coding_agent.graph import AgentState, bump_visit
from coding_agent.sandbox import (
    ExecResult,
    PathEscapeError,
    Sandbox,
    make_workspace,
    scan,
    truncate,
    write_files,
)

PYTEST_COMMAND = ["python", "-m", "pytest", "-q"]


def _is_test_file(path: str) -> bool:
    p = PurePosixPath(path)
    return p.suffix == ".py" and (p.name.startswith("test_") or "tests" in p.parts[:-1])


def choose_command(files: dict[str, str]) -> list[str] | None:
    """The command to run for ``files``; None when there is no Python to run."""
    if any(_is_test_file(p) for p in files):
        return list(PYTEST_COMMAND)
    if DEFAULT_ENTRYPOINT in files:
        return ["python", DEFAULT_ENTRYPOINT]
    modules = sorted(p for p in files if p.endswith(".py"))
    return ["python", "-m", "py_compile", *modules] if modules else None


def policy_flags(files: dict[str, str]) -> list[dict[str, Any]]:
    """Advisory scan of every .py file, as plain dicts (safe to log and serialise)."""
    return [
        {"path": path, "rule": f.rule, "line": f.line}
        for path, code in sorted(files.items())
        if path.endswith(".py")
        for f in scan(code)
    ]


def _failure(message: str) -> ExecResult:
    """A non-crashing execution failure the reviewer can read and react to."""
    return ExecResult(1, "", message, False, False, 0.0)


def _capped(r: ExecResult) -> ExecResult:
    # A 10 MB print must never reach a model or the state history.
    return dataclasses.replace(
        r,
        stdout=truncate(r.stdout, MAX_EXEC_OUTPUT_CHARS),
        stderr=truncate(r.stderr, MAX_EXEC_OUTPUT_CHARS),
    )


def make_executor(sandbox: Sandbox, settings: Settings) -> Callable[[AgentState], dict[str, Any]]:
    """Build the executor node. It runs code only; it never touches counters."""

    def run(files: dict[str, str]) -> tuple[list[str] | None, ExecResult]:
        if not files:
            return None, _failure("The coder produced no files (no ### FILE: blocks were found).")
        command = choose_command(files)
        if command is None:
            return None, _failure("No Python files to run: expected main.py, tests or modules.")
        workspace = make_workspace(settings.workspace_root)
        try:
            write_files(workspace, files)
            return command, sandbox.run(workspace, command, settings.limits)
        except PathEscapeError as exc:
            return command, _failure(f"PathEscapeError: {exc}. Use relative paths inside the project.")
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def executor(state: AgentState) -> dict[str, Any]:
        files = dict(state["files"])
        flags = policy_flags(files)
        command, raw = run(files)
        result = _capped(raw)
        version = {
            "version": len(state["code_versions"]) + 1,
            "files": files,
            "command": command,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "oom_killed": result.oom_killed,
            "summary": exec_summary(result),
            "flags": flags,
        }
        return {
            "last_exec": result,
            "code_versions": [*state["code_versions"], version],
            **bump_visit(state),
            "events": [event(
                "executor", command=command, exit_code=result.exit_code,
                summary=version["summary"], flags=flags,
            )],
        }

    return executor
