"""Role -> model routing plus token/cost accounting."""
import threading
from collections.abc import Callable, Mapping
from typing import Literal, get_args

from coding_agent.config import Settings
from coding_agent.llm.base import ChatModel, LLMResponse, Usage
from coding_agent.llm.groq_model import GroqChatModel
from coding_agent.llm.pricing import cost_usd

Role = Literal["planner", "architect", "coder", "reviewer", "debugger"]
_STRONG_ROLES: frozenset[str] = frozenset({"coder", "debugger"})


class UsageTracker:
    """Thread-safe running totals, broken down per model."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_model: dict[str, Usage] = {}

    def add(self, model: str, usage: Usage) -> None:
        with self._lock:
            old = self._by_model.get(model, Usage(0, 0))
            self._by_model[model] = Usage(
                old.tokens_in + usage.tokens_in, old.tokens_out + usage.tokens_out
            )

    @property
    def by_model(self) -> dict[str, Usage]:
        with self._lock:
            return dict(self._by_model)

    @property
    def total_tokens(self) -> int:
        return sum(u.total for u in self.by_model.values())

    @property
    def total_cost(self) -> float:
        """Sum of known costs; models with unknown prices count as 0 (see cost_known)."""
        return sum(c for m, u in self.by_model.items() if (c := cost_usd(m, u)) is not None)

    @property
    def cost_known(self) -> bool:
        return all(cost_usd(m, u) is not None for m, u in self.by_model.items())


class _TrackedModel:
    def __init__(self, name: str, inner: ChatModel, tracker: UsageTracker) -> None:
        self._name, self._inner, self._tracker = name, inner, tracker

    def invoke(self, system: str, user: str) -> LLMResponse:
        resp = self._inner.invoke(system, user)
        self._tracker.add(self._name, resp.usage)
        return resp


class ModelRouter:
    def __init__(
        self,
        settings: Settings,
        tracker: UsageTracker | None = None,
        factory: Callable[[str], ChatModel] | None = None,
        *,
        all_strong: bool = False,
        overrides: Mapping[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._tracker = tracker
        self._all_strong = all_strong
        self._overrides = dict(overrides or {})
        self._factory = factory or (
            lambda model: GroqChatModel(model, settings.groq_api_key)
        )

    def model_name(self, role: Role) -> str:
        if role not in get_args(Role):
            raise ValueError(f"unknown role {role!r}; expected one of {get_args(Role)}")
        if role in self._overrides:
            return self._overrides[role]
        if self._all_strong or role in _STRONG_ROLES:
            return self._settings.model_strong
        return self._settings.model_cheap

    def for_role(self, role: Role) -> ChatModel:
        name = self.model_name(role)
        model = self._factory(name)
        return _TrackedModel(name, model, self._tracker) if self._tracker else model
