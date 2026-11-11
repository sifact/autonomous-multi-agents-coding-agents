"""Turns streamed graph updates into readable plain-text progress lines."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coding_agent.cli_support.format import tail


class StepPrinter:
    """Prints one block per finished graph node. ``echo`` is injectable for tests."""

    def __init__(
        self, echo: Callable[[str], None], *, verbose: bool = False, quiet: bool = False
    ) -> None:
        self._echo, self._verbose, self._quiet = echo, verbose, quiet

    def _say(self, text: str = "") -> None:
        if not self._quiet:
            self._echo(text)

    def handle(self, node: str, update: dict[str, Any]) -> None:
        getattr(self, f"_{node}", lambda _u: None)(update)

    def _planner(self, u: dict[str, Any]) -> None:
        self._say("== Plan ==")
        for step in u.get("plan", []):
            self._say(f"  {step.id}. {step.description}  (done when: {step.acceptance})")
        for c in u.get("criteria", []):
            self._say(f"  criterion: {c}")
        if u.get("replans"):
            self._say(f"  (replan #{u['replans']})")

    def _architect(self, u: dict[str, Any]) -> None:
        self._say("== File layout ==")
        for item in u.get("layout", []):
            self._say(f"  {item}")

    def _coder(self, u: dict[str, Any]) -> None:
        ev = u["events"][-1]
        label = "repair" if ev.get("role") == "debugger" else "first draft"
        self._say(f"== Code ({label}, model {ev.get('model', '?')}) ==")
        names = ", ".join(sorted(u["files"]))
        self._say(f"  files: {names}" if names else "  (no files produced)")
        if self._verbose:
            for path, content in sorted(u["files"].items()):
                self._say(f"--- {path} ---\n{content}")
        if u.get("repairs"):
            self._say(f"  repairs so far: {u['repairs']}")

    def _executor(self, u: dict[str, Any]) -> None:
        v = u["code_versions"][-1]
        r = u["last_exec"]
        self._say(f"== Run (version {v['version']}) ==")
        self._say(f"  command: {' '.join(v['command'])}")
        self._say(f"  exit code {r.exit_code} in {r.duration_s:.1f}s ({v['summary']})")
        for label, text in (("stdout", r.stdout), ("stderr", r.stderr)):
            if text.strip():
                self._say(f"  {label} tail:")
                self._say("    " + tail(text).replace("\n", "\n    "))
        for f in v["flags"]:
            self._say(f"  scan flag: {f['rule']} at {f['path']}:{f['line']}")

    def _reviewer(self, u: dict[str, Any]) -> None:
        v = u["verdict"]
        self._say(f"== Review: {v.action} ==")
        self._say(f"  {v.reason}")
