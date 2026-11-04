"""Provider-neutral LLM types so agents never import a vendor SDK."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Usage:
    tokens_in: int
    tokens_out: int

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.tokens_in + other.tokens_in, self.tokens_out + other.tokens_out)

    @property
    def total(self) -> int:
        return self.tokens_in + self.tokens_out


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: Usage


class ChatModel(Protocol):
    def invoke(self, system: str, user: str) -> LLMResponse: ...
