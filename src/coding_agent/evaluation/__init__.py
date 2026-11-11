"""Evaluation: sandbox safety suite, task format, grader, metrics, eval systems."""
from coding_agent.evaluation.grader import GradeResult, grade
from coding_agent.evaluation.metrics import Metrics, RunRecord, aggregate
from coding_agent.evaluation.report import render_markdown
from coding_agent.evaluation.results_io import ResultFile, load_results
from coding_agent.evaluation.runner import run_benchmark, save_results
from coding_agent.evaluation.safety import CaseResult, SafetyReport, run_case, run_safety_suite
from coding_agent.evaluation.safety_cases import SAFETY_CASES, HostContext, SafetyCase
from coding_agent.evaluation.systems import (
    GraphSystem,
    SingleAgentLoop,
    SingleShot,
    System,
    SystemOutput,
)
from coding_agent.evaluation.task import Task, load_fast_subset, load_task, load_tasks
from coding_agent.evaluation.validate import CATEGORIES, validate_all, validate_task
from coding_agent.evaluation.verdict import compare

__all__ = [
    "CATEGORIES",
    "SAFETY_CASES",
    "CaseResult",
    "GradeResult",
    "GraphSystem",
    "HostContext",
    "Metrics",
    "ResultFile",
    "RunRecord",
    "SafetyCase",
    "SafetyReport",
    "SingleAgentLoop",
    "SingleShot",
    "System",
    "SystemOutput",
    "Task",
    "aggregate",
    "compare",
    "grade",
    "load_fast_subset",
    "load_results",
    "load_task",
    "load_tasks",
    "render_markdown",
    "run_benchmark",
    "run_case",
    "run_safety_suite",
    "save_results",
    "validate_all",
    "validate_task",
]
