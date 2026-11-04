"""The one task text every eval system sees, so no system gets extra information."""
from coding_agent.agents.context import format_files, format_fixtures
from coding_agent.evaluation.task import Task


def task_prompt(task: Task, with_fixtures: bool = True) -> str:
    """Prompt text + starter files (if any) + a preview of each fixture file.

    The starter is shown in full because the agent must edit it. Fixtures are
    previewed (same helper the graph agents use) and are also written into the
    workspace where the agent's code runs. The graph passes ``with_fixtures=False``
    because its nodes add the fixtures section themselves from the state.
    """
    parts = [task.prompt.strip()]
    if task.starter:
        parts.append("Starting files (edit these):\n" + format_files(task.starter))
    if with_fixtures and task.fixtures:
        parts.append(format_fixtures(task.fixtures))
    return "\n\n".join(parts)
