"""Robust extraction of one JSON object from chatty model output."""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from coding_agent.agents.prompts import JSON_RETRY_REMINDER
from coding_agent.llm import ChatModel, Usage

_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n(.*?)```", re.DOTALL)
_DECODER = json.JSONDecoder()


class ParseError(ValueError):
    """Model output held no JSON object matching the expected schema."""


def _candidates(text: str) -> list[str]:
    # Fenced blocks first (the model's intended answer), then the raw text so a
    # bare object surrounded by prose is still found.
    return [m.group(1) for m in _FENCE.finditer(text)] + [text]


def _objects(text: str):
    """Yield every top-level JSON object that decodes starting at a '{'."""
    i = text.find("{")
    while i != -1:
        try:
            obj, end = _DECODER.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        if isinstance(obj, dict):
            yield obj
        i = text.find("{", end)


def parse_json[T: BaseModel](text: str, schema: type[T]) -> T:
    """Return the first JSON object in ``text`` that validates against ``schema``.

    Small models wrap JSON in fences and prose, or emit a draft object before
    the real one, so every candidate is tried rather than only the first.
    """
    last_error = "no JSON object found"
    for chunk in _candidates(text):
        for obj in _objects(chunk):
            try:
                return schema.model_validate(obj)
            except ValidationError as exc:
                last_error = f"invalid {schema.__name__}: {exc.errors()[0]['msg']}"
    raise ParseError(f"could not parse {schema.__name__}: {last_error}")


def invoke_json[T: BaseModel](
    model: ChatModel, system: str, user: str, schema: type[T]
) -> tuple[T | None, Usage, str]:
    """Ask for JSON, retrying ONCE with a reminder; never raise on bad output.

    Returns ``(obj, usage, error)``: ``obj`` is None and ``error`` explains why
    when both replies were malformed. ``usage`` sums both calls so callers can
    account for the retry.
    """
    resp = model.invoke(system, user)
    usage = resp.usage
    try:
        return parse_json(resp.text, schema), usage, ""
    except ParseError:
        pass
    retry = model.invoke(system, f"{user}\n\n{JSON_RETRY_REMINDER.format(schema=schema.__name__)}")
    usage = Usage(usage.tokens_in + retry.usage.tokens_in, usage.tokens_out + retry.usage.tokens_out)
    try:
        return parse_json(retry.text, schema), usage, ""
    except ParseError as exc:
        return None, usage, str(exc)
