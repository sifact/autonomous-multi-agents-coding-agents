"""Shared helpers for graph tests: per-role scripted router and a canned sandbox."""
import json

from coding_agent.llm import FakeLLM, ModelRouter, UsageTracker

ROLES = ("planner", "architect", "coder", "debugger", "reviewer")


def scripted_router(settings, tracker=None, **scripts):
    """Router whose factory hands each role its own FakeLLM (model name = fake-<role>)."""
    llms = {role: FakeLLM(scripts.get(role, [])) for role in ROLES}
    router = ModelRouter(
        settings, tracker or UsageTracker(),
        factory=lambda name: llms[name.removeprefix("fake-")],
        overrides={role: f"fake-{role}" for role in ROLES},
    )
    return router, llms


def plan(tag: str = "a") -> str:
    return json.dumps({
        "steps": [{"id": 1, "description": f"plan {tag}", "acceptance": "prints ok"}],
        "criteria": ["prints ok"],
    })


def layout() -> str:
    return '{"files": [{"path": "main.py", "purpose": "entry point"}]}'


def code(body: str) -> str:
    return f"### FILE: main.py\n```python\n{body}\n```\n"


def verdict(action: str, reason: str = "") -> str:
    return json.dumps({"action": action, "reason": reason or f"{action} it"})


class CannedSandbox:
    """Returns the same result for every run (no Docker)."""

    def __init__(self, result):
        self.result, self.runs = result, 0

    def run(self, workspace, command, limits=None):
        self.runs += 1
        return self.result
