"""LangChain-config metadata that the Langfuse callback handler turns into trace attributes."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

TRACE_NAME_PREFIX = "coding-agent"


def trace_metadata(
    run_id: str, system: str, task_id: str | None = None, *, tags: Iterable[str] | None = None
) -> dict[str, Any]:
    """Session, trace name and tags for one run.

    ``run_id`` becomes the Langfuse session (for eval: the result file id, so all
    task runs of one benchmark group together). Tags are de-duplicated in order.
    """
    wanted = [system, *([task_id] if task_id else []), *(tags or [])]
    return {
        "langfuse_session_id": run_id,
        "langfuse_trace_name": f"{TRACE_NAME_PREFIX}/{system}",
        "langfuse_tags": list(dict.fromkeys(wanted)),
    }
