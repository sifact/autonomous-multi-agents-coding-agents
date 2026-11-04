"""LLM layer: provider-neutral types, Groq client, fake, pricing, routing."""
from coding_agent.llm.base import ChatModel, LLMResponse, Usage
from coding_agent.llm.fake import FakeLLM, ScriptExhaustedError
from coding_agent.llm.groq_model import GroqChatModel, MissingApiKeyError, RateLimited
from coding_agent.llm.pricing import PRICES, Price, cost_usd
from coding_agent.llm.router import ModelRouter, Role, UsageTracker

__all__ = [
    "PRICES",
    "ChatModel",
    "FakeLLM",
    "GroqChatModel",
    "LLMResponse",
    "MissingApiKeyError",
    "ModelRouter",
    "Price",
    "RateLimited",
    "Role",
    "ScriptExhaustedError",
    "Usage",
    "UsageTracker",
    "cost_usd",
]
