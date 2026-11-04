"""Shared formatting of state into prompt text, plus the event record every node emits."""
from __future__ import annotations

import html
import re
from typing import Any

from coding_agent.agents.prompts import MAX_EXEC_PROMPT_CHARS, MAX_FILES_PROMPT_CHARS
from coding_agent.graph import Step
from coding_agent.llm import Usage
from coding_agent.sandbox import ExecResult, truncate


def format_plan(steps: list[Step]) -> str:
    return "\n".join(f"{s.id}. {s.description} (done when: {s.acceptance})" for s in steps) or "(none)"


def format_list(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "(none)"


# The tags that fence untrusted data in prompts. Any occurrence of them inside
# the data itself is defanged so program output cannot close a block early or
# open a fake one.
UNTRUSTED_TAGS = ("program_stdout", "program_stderr", "file")
_OUR_TAG = re.compile(r"<(/?)\s*(" + "|".join(UNTRUSTED_TAGS) + r")\b", re.IGNORECASE)
_BACKTICKS = re.compile(r"`+")


def neutralise(text: str) -> str:
    """Replace ``<``/``</`` of our own tag names with ``&lt;`` (other markup untouched)."""
    return _OUR_TAG.sub(lambda m: f"&lt;{m.group(1)}{m.group(2)}", text)


def tagged(tag: str, content: str, **attrs: str) -> str:
    """Wrap untrusted ``content`` in ``<tag ...>...</tag>`` after defanging it."""
    attr = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in attrs.items())
    return f"<{tag}{attr}>\n{neutralise(content)}\n</{tag}>"


def _fence_for(content: str) -> str:
    """A fence longer than any backtick run in ``content`` (min 3), so it cannot close early."""
    longest = max((len(m.group(0)) for m in _BACKTICKS.finditer(content)), default=0)
    return "`" * max(3, longest + 1)


def format_files(files: dict[str, str], max_chars: int = MAX_FILES_PROMPT_CHARS) -> str:
    """All files, each in a ``<file path=...>`` tag holding a fenced block.

    The size budget is split per file before tagging, so truncation can never
    cut away a closing tag.
    """
    if not files:
        return "(no files)"
    per_file = max(1, max_chars // len(files))
    blocks = []
    for path, content in files.items():
        body = truncate(content, per_file)
        fence = _fence_for(body)
        blocks.append(tagged("file", f"{fence}\n{body}\n{fence}", path=path))
    return "\n\n".join(blocks)


def exec_summary(r: ExecResult | None) -> str:
    """One line a model (or a person) can read: exit code plus abnormal-end flags."""
    if r is None:
        return "not run"
    parts = [f"exit code {r.exit_code}", f"{r.duration_s:.1f}s"]
    if r.timed_out:
        parts.append("timed out (killed at the time limit)")
    if r.oom_killed:
        parts.append("killed: out of memory")
    if r.disk_exceeded:
        parts.append("killed: disk limit exceeded")
    return ", ".join(parts)


def exec_streams(r: ExecResult | None) -> tuple[str, str]:
    """stdout/stderr trimmed for a prompt and wrapped in untrusted-data tags."""
    out = truncate(r.stdout, MAX_EXEC_PROMPT_CHARS) if r else ""
    err = truncate(r.stderr, MAX_EXEC_PROMPT_CHARS) if r else ""
    return (
        tagged("program_stdout", out or ("(not run)" if r is None else "(empty)")),
        tagged("program_stderr", err or ("(not run)" if r is None else "(empty)")),
    )


def event(node: str, usage: Usage | None = None, **extra: Any) -> dict[str, Any]:
    """The durable per-node record appended to ``events``.

    Token counts ride on events so the finalize step can total a run's usage
    without a shared tracker (a tracker reused across runs would over-count).
    """
    ev: dict[str, Any] = {"node": node}
    if usage is not None:
        ev["tokens_in"], ev["tokens_out"] = usage.tokens_in, usage.tokens_out
    ev.update(extra)
    return ev
