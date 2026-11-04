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
from coding_agent.agents.prompts import (
    COMMAND_MEANING_MAIN,
    COMMAND_MEANING_NONE,
    COMMAND_MEANING_SYNTAX,
    COMMAND_MEANING_TESTS,
    DEFAULT_ENTRYPOINT,
    MAX_EXEC_OUTPUT_CHARS,
)
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


def describe_command(command: list[str] | None) -> str:
    """Plain statement of what ``command`` proves, for the reviewer."""
    if not command:
        return COMMAND_MEANING_NONE
    if command[:3] == PYTEST_COMMAND[:3]:
        return COMMAND_MEANING_TESTS
    if command[:3] == ["python", "-m", "py_compile"]:
        return COMMAND_MEANING_SYNTAX
    return COMMAND_MEANING_MAIN


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


def execute_files(
    files: dict[str, str], sandbox: Sandbox, settings: Settings,
    fixtures: dict[str, str] | None = None,
) -> tuple[list[str] | None, ExecResult]:
    """Run ``files`` in a fresh workspace; return ``(command, capped result)``.

    The one execution core shared by the graph's executor node and the
    single-agent baseline, so both run code identically. Model-caused failures
    (no files, bad paths) come back as a failed result; Docker errors propagate.
    """
    if not files:
        return None, _failure("The coder produced no files (no ### FILE: blocks were found).")
    command = choose_command(files)
    if command is None:
        return None, _failure("No Python files to run: expected main.py, tests or modules.")
    workspace = make_workspace(settings.workspace_root)
    try:
        try:
            write_files(workspace, files)
            # Fixtures last (as in the grader) so agent files cannot replace the data.
            write_files(workspace, fixtures or {})
        except (PathEscapeError, OSError) as exc:
            # Model-chosen paths ('' or '.', a file and a dir with one name,
            # escapes) are the model's bug: report it, never crash the run.
            return None, _failure(
                f"Could not write the files ({type(exc).__name__}: {exc}). Use distinct "
                "relative file paths inside the project."
            )
        # Docker/infrastructure errors from here on propagate: they are not
        # something the coder can fix.
        return command, _capped(sandbox.run(workspace, command, settings.limits))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def make_executor(sandbox: Sandbox, settings: Settings) -> Callable[[AgentState], dict[str, Any]]:
    """Build the executor node. It runs code only; it never touches counters."""

    def executor(state: AgentState) -> dict[str, Any]:
        files = dict(state["files"])
        flags = policy_flags(files)
        command, result = execute_files(files, sandbox, settings, state["fixtures"])
        version = {
            "version": len(state["code_versions"]) + 1,
            "files": files,
            "command": command,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "oom_killed": result.oom_killed,
            "disk_exceeded": result.disk_exceeded,
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
