"""One traced run: a named root observation, session and tags, plus the callbacks to pass on.

Shape of a trace: ``coding-agent/<system>`` (agent) -> LangGraph run -> one span per
node -> model generations. The root's input is the task text and its output a small
summary, not the whole state; each node's returned update is that node's output, which
is where the plan, code versions, errors and fixes become visible.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import Any

from coding_agent.config import Settings
from coding_agent.tracing import langfuse_setup
from coding_agent.tracing.masking import Scrubber
from coding_agent.tracing.metadata import trace_metadata

log = logging.getLogger(__name__)
MAX_STATUS_CHARS = 500


def summarize_report(report: Any) -> dict[str, Any]:
    """Small trace output for a FinalReport: verdict, repairs, explanation, usage, file names."""
    return {
        "success": report.success, "repairs": report.repairs, "explanation": report.explanation,
        "tokens_in": report.usage.tokens_in, "tokens_out": report.usage.tokens_out,
        "files": sorted(report.files),
    }


class TraceRun:
    """Handle for the current traced run. Every method is a safe no-op when tracing is off."""

    def __init__(
        self, *, client: Any = None, root: Any = None, callbacks: list[Any] | None = None,
        metadata: dict[str, Any] | None = None, scrub: Scrubber | None = None,
    ) -> None:
        self._scrub = scrub or (lambda text: text)
        self._client, self._root = client, root
        self.callbacks = callbacks or []
        self.metadata = metadata or {}
        self.trace_id: str | None = getattr(root, "trace_id", None)

    @property
    def config(self) -> dict[str, Any]:
        """LangChain ``config`` for ``graph.invoke/stream`` (empty when tracing is off)."""
        if not self.callbacks:
            return {}
        return {"callbacks": self.callbacks, "metadata": self.metadata}

    def set_output(self, output: Any) -> None:
        self._safely(lambda: self._root.update(output=output))

    def set_report(self, report: Any) -> None:
        """Make the final report summary the trace output."""
        self._safely(lambda: self._root.update(output=summarize_report(report)))

    def score(self, name: str, value: bool | float, comment: str | None = None) -> None:
        """Attach a Langfuse score to this trace (e.g. ``final_pass`` after grading)."""
        def send() -> None:
            kwargs: dict[str, Any] = {
                "trace_id": self.trace_id, "name": name, "value": float(value),
                "data_type": "BOOLEAN" if isinstance(value, bool) else "NUMERIC",
            }
            if comment:
                kwargs["comment"] = comment
            self._client.create_score(**kwargs)
        self._safely(send)

    def record_error(self, exc: BaseException) -> None:
        message = self._scrub(f"{type(exc).__name__}: {exc}")[:MAX_STATUS_CHARS]
        self._safely(lambda: self._root.update(level="ERROR", status_message=message))

    def _safely(self, fn: Any) -> None:
        if self._root is None:
            return
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - tracing must never break a run
            log.warning("Langfuse update failed: %s: %s", type(exc).__name__, exc)


def _open(
    stack: ExitStack, settings: Settings, *, session_id: str, system: str,
    task_id: str | None, input_text: str, tags: list[str],
) -> TraceRun:
    client = langfuse_setup.get_client(settings)
    callbacks = langfuse_setup.get_callbacks(settings) if client else []
    if client is None or not callbacks:
        return TraceRun()
    from langchain_core.runnables.config import var_child_runnable_config
    from langfuse import propagate_attributes

    metadata = trace_metadata(session_id, system, task_id, tags=tags)
    name = metadata["langfuse_trace_name"]
    root = stack.enter_context(
        client.start_as_current_observation(name=name, as_type="agent", input=input_text))
    stack.enter_context(propagate_attributes(
        trace_name=name, session_id=session_id, tags=metadata["langfuse_tags"]))
    run = TraceRun(client=client, root=root, callbacks=callbacks, metadata=metadata,
                   scrub=langfuse_setup.scrubber_for(settings))
    # Ambient config (guarded by tests/tracing/test_propagation.py: ``var_child_runnable_config``
    # is a langchain_core module variable, not a documented API, hence the pinned version):
    # code that calls a model without an explicit config (the baselines'
    # ChatGroq call) still reports to this handler through LangChain's context variable.
    token = var_child_runnable_config.set(run.config)
    stack.callback(var_child_runnable_config.reset, token)
    return run


@contextmanager
def trace_run(
    settings: Settings, *, session_id: str, system: str, input_text: str,
    task_id: str | None = None, tags: list[str] | None = None,
) -> Iterator[TraceRun]:
    """Open one trace for one run; ends (and records an error) when the block exits."""
    stack = ExitStack()
    try:
        run = _open(stack, settings, session_id=session_id, system=system, task_id=task_id,
                    input_text=input_text, tags=list(tags or []))
    except Exception as exc:  # noqa: BLE001
        log.warning("Langfuse tracing disabled: %s: %s", type(exc).__name__, exc)
        _close(stack)
        run = TraceRun()
    try:
        yield run
    except BaseException as exc:
        run.record_error(exc)
        raise
    finally:
        _close(stack)


def _close(stack: ExitStack) -> None:
    try:
        stack.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("Langfuse trace close failed: %s: %s", type(exc).__name__, exc)
