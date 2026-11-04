"""Check that a benchmark task is well formed and actually discriminates.

A task is only a fair test if its reference passes, doing nothing fails, and the
hidden tests are neither trivially weak nor leaked through the prompt.
"""
import ast
from pathlib import PurePosixPath

from coding_agent.evaluation.grader import grade
from coding_agent.evaluation.task import Task
from coding_agent.sandbox import Sandbox

CATEGORIES = frozenset({
    "data_script", "file_processing", "cli_app", "chart", "bug_fix", "html_fixture",
})
MIN_TEST_CASES = 3  # fewer asserts-in-one-test cases cannot catch partial solutions


def count_test_cases(source: str) -> int:
    """Count test functions, expanding literal ``parametrize`` lists into their cases."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0
    total = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("test"):
            continue
        cases = 1
        for deco in node.decorator_list:
            if (
                isinstance(deco, ast.Call)
                and isinstance(deco.func, ast.Attribute)
                and deco.func.attr == "parametrize"
                and len(deco.args) >= 2
                and isinstance(deco.args[1], ast.List | ast.Tuple)
            ):
                cases *= max(1, len(deco.args[1].elts))
        total += cases
    return total


def _leaked_names(task: Task) -> list[str]:
    """Hidden test file names (or the hidden_tests dir) mentioned in the prompt."""
    prompt = task.prompt.lower()
    found = []
    for rel in task.hidden_tests:
        name = PurePosixPath(rel).name
        if name.lower() in prompt:
            found.append(name)
    if "hidden_tests" in prompt or "hidden test" in prompt:
        found.append("hidden tests")
    return sorted(set(found))


def validate_task(task: Task, sandbox: Sandbox) -> list[str]:
    """Return a list of problems with the task (empty list means valid)."""
    problems: list[str] = []
    if not task.prompt.strip():
        problems.append("prompt.md is empty")
    if task.category not in CATEGORIES:
        problems.append(f"unknown category {task.category!r}")
    leaked = _leaked_names(task)
    if leaked:
        problems.append(f"prompt mentions hidden tests: {', '.join(leaked)}")
    cases = sum(count_test_cases(src) for src in task.hidden_tests.values())
    if cases < MIN_TEST_CASES:
        problems.append(f"hidden tests have {cases} case(s); need at least {MIN_TEST_CASES}")
    if not task.reference:
        problems.append("reference is empty")
    else:
        ref = grade(task, task.reference, sandbox)
        if not ref.passed:
            problems.append(f"reference fails hidden tests:\n{ref.output}")
    if grade(task, {}, sandbox).passed:
        problems.append("empty file set passes hidden tests")
    if task.starter and grade(task, task.starter, sandbox).passed:
        problems.append("starter files already pass hidden tests")
    return problems


def validate_all(tasks: list[Task], sandbox: Sandbox) -> dict[str, list[str]]:
    """Validate every task; duplicate ids are reported on the repeated task."""
    report: dict[str, list[str]] = {}
    seen: set[str] = set()
    for task in tasks:
        problems = validate_task(task, sandbox)
        if task.id in seen:
            problems.append(f"duplicate task id {task.id!r}")
        seen.add(task.id)
        report.setdefault(task.id, []).extend(problems)
    return report
