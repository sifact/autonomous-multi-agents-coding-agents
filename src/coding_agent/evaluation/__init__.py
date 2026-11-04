"""Evaluation: sandbox safety suite (Task 4 adds task-level evaluation)."""
from coding_agent.evaluation.safety import CaseResult, SafetyReport, run_case, run_safety_suite
from coding_agent.evaluation.safety_cases import SAFETY_CASES, HostContext, SafetyCase

__all__ = [
    "SAFETY_CASES",
    "CaseResult",
    "HostContext",
    "SafetyCase",
    "SafetyReport",
    "run_case",
    "run_safety_suite",
]
