"""Scripted model for tests: deterministic, offline, records what it was asked."""
from coding_agent.llm.base import LLMResponse, Usage

_CHARS_PER_TOKEN = 4


class ScriptExhaustedError(RuntimeError):
    """The test asked the fake for more replies than were scripted."""


def estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


class FakeLLM:
    def __init__(self, script: list[str]) -> None:
        self._script = list(script)
        self._n = len(script)
        self.calls: list[tuple[str, str]] = []

    def invoke(self, system: str, user: str) -> LLMResponse:
        self.calls.append((system, user))
        if not self._script:
            raise ScriptExhaustedError(
                f"FakeLLM exhausted: only {self._n} scripted replies, call #{len(self.calls)}"
            )
        text = self._script.pop(0)
        usage = Usage(estimate_tokens(system) + estimate_tokens(user), estimate_tokens(text))
        return LLMResponse(text, usage)
