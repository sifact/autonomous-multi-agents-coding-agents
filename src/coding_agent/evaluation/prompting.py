"""The one task text every eval system sees, so no system gets extra information."""
from coding_agent.agents.context import format_files
from coding_agent.agents.prompts import MAX_FIXTURE_PREVIEW_CHARS
from coding_agent.evaluation.task import Task
from coding_agent.sandbox import truncate


def task_prompt(task: Task) -> str:
    """Prompt text + starter files (if any) + a listing of fixture files with a short preview.

    Fixtures are only previewed because the real files are present when the hidden
    tests run; the starter is shown in full because the agent must edit it.
    """
    parts = [task.prompt.strip()]
    if task.starter:
        parts.append("Starting files (edit these):\n" + format_files(task.starter))
    if task.fixtures:
        listing = "\n".join(
            f"- {path}: {truncate(text, MAX_FIXTURE_PREVIEW_CHARS)!r}"
            for path, text in sorted(task.fixtures.items())
        )
        parts.append("Files available in the working directory (name and start):\n" + listing)
    return "\n\n".join(parts)
