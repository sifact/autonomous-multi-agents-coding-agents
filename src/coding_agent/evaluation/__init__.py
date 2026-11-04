"""Evaluation: sandbox safety suite, task format, grader, metrics."""
from coding_agent.evaluation.grader import GradeResult, grade
from coding_agent.evaluation.metrics import Metrics, RunRecord, aggregate
from coding_agent.evaluation.safety import CaseResult, SafetyReport, run_case, run_safety_suite
from coding_agent.evaluation.safety_cases import SAFETY_CASES, HostContext, SafetyCase
from coding_agent.evaluation.task import Task, load_task, load_tasks

__all__ = [
    "SAFETY_CASES",
    "CaseResult",
    "GradeResult",
    "HostContext",
    "Metrics",
    "RunRecord",
    "SafetyCase",
    "SafetyReport",
    "Task",
    "aggregate",
    "grade",
    "load_task",
    "load_tasks",
    "run_case",
    "run_safety_suite",
]
