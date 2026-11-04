"""Check that a benchmark task is well formed and actually discriminates.

A task is only a fair test if its reference passes, doing nothing fails, and the
hidden tests are neither trivially weak nor leaked through the prompt.
"""
import ast
import re
from pathlib import PurePosixPath

from coding_agent.evaluation.grader import grade
from coding_agent.evaluation.task import Task
from coding_agent.sandbox import Sandbox

CATEGORIES = frozenset({
    "data_script", "file_processing", "cli_app", "chart", "bug_fix", "html_fixture",
})
DIFFICULTIES = frozenset({"easy", "medium", "hard"})
MIN_TEST_CASES = 3  # fewer checked cases cannot catch partial solutions


_CHECK_ATTRS = frozenset({"raises", "approx", "warns"})


def _collectible_tests(source: str) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Module-level ``test*`` functions and ``test*`` methods of ``Test*`` classes."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    func_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, func_types) and node.name.startswith("test"):
            found.append(node)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            found.extend(
                m for m in node.body if isinstance(m, func_types) and m.name.startswith("test")
            )
    return found


def _has_check(func: ast.AST) -> bool:
    """True if the test body asserts something (assert, pytest.raises/approx/warns)."""
    return any(
        isinstance(n, ast.Assert) or (isinstance(n, ast.Attribute) and n.attr in _CHECK_ATTRS)
        for n in ast.walk(func)
    )


def _case_count(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """1, or the product of literal ``parametrize`` list sizes on the function."""
    cases = 1
    for deco in func.decorator_list:
        if (
            isinstance(deco, ast.Call)
            and isinstance(deco.func, ast.Attribute)
            and deco.func.attr == "parametrize"
            and len(deco.args) >= 2
            and isinstance(deco.args[1], ast.List | ast.Tuple)
        ):
            cases *= max(1, len(deco.args[1].elts))
    return cases


def count_test_cases(source: str) -> int:
    """Count collectible tests that check something, expanding literal parametrize lists."""
    return sum(_case_count(f) for f in _collectible_tests(source) if _has_check(f))


def _leaked_names(task: Task) -> list[str]:
    """Hidden test file or function names (or the phrase 'hidden tests') used in the prompt."""
    prompt = task.prompt.lower()
    found = []
    for rel, source in task.hidden_tests.items():
        name = PurePosixPath(rel).name
        if name.lower() in prompt:
            found.append(name)
        for func in _collectible_tests(source):
            if re.search(rf"\b{re.escape(func.name.lower())}\b", prompt):
                found.append(func.name)
    if "hidden_tests" in prompt or "hidden test" in prompt:
        found.append("hidden tests")
    return sorted(set(found))


def validate_task(
    task: Task, sandbox: Sandbox, require_difficulty: bool = False
) -> list[str]:
    """Return a list of problems with the task (empty list means valid).

    ``require_difficulty`` is on for the real benchmark set, where reports group by it.
    """
    problems: list[str] = []
    if task.difficulty is None:
        if require_difficulty:
            problems.append("missing difficulty in task.toml")
    elif task.difficulty not in DIFFICULTIES:
        problems.append(f"invalid difficulty {task.difficulty!r}")
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


def validate_all(
    tasks: list[Task], sandbox: Sandbox, require_difficulty: bool = False
) -> dict[str, list[str]]:
    """Validate every task; duplicate ids are reported on the repeated task."""
    report: dict[str, list[str]] = {}
    seen: set[str] = set()
    for task in tasks:
        problems = validate_task(task, sandbox, require_difficulty)
        if task.id in seen:
            problems.append(f"duplicate task id {task.id!r}")
        seen.add(task.id)
        report.setdefault(task.id, []).extend(problems)
    return report
