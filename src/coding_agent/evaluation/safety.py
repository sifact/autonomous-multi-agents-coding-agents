"""Run the safety cases against a sandbox and report how many were contained."""
import shutil
from dataclasses import dataclass

from coding_agent.evaluation.safety_cases import (
    CANARY_TOKEN,
    SAFETY_CASES,
    WORKSPACE_TOKEN,
    HostContext,
    SafetyCase,
    list_agent_containers,
)
from coding_agent.sandbox import Sandbox, make_workspace, write_files


@dataclass(frozen=True)
class CaseResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class SafetyReport:
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def run_case(sandbox: Sandbox, case: SafetyCase) -> CaseResult:
    """Run one case in a fresh workspace; a case passes only if every check holds."""
    workspace, canary_dir = make_workspace(), make_workspace()  # canary_dir is not mounted
    try:
        canary = canary_dir / "canary.txt"
        canary.write_text("alive")
        ctx = HostContext(
            workspace, canary, shutil.disk_usage(workspace).free, list_agent_containers(),
        )
        code = case.code.replace(CANARY_TOKEN, str(canary))
        code = code.replace(WORKSPACE_TOKEN, str(workspace.resolve()))
        write_files(workspace, {"main.py": code})
        result = sandbox.run(workspace, ["python", "main.py"], case.limits)
        if not case.expect(result):
            return CaseResult(case.name, False, f"expect failed: {result}")
        if case.post_check and not case.post_check(ctx):
            return CaseResult(case.name, False, "host post-check failed")
        return CaseResult(case.name, True)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.rmtree(canary_dir, ignore_errors=True)


def run_safety_suite(sandbox: Sandbox) -> SafetyReport:
    return SafetyReport([run_case(sandbox, c) for c in SAFETY_CASES])
