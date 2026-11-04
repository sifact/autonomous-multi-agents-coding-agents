"""Single source of truth for configuration, overridable via env vars or .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from coding_agent.sandbox import Limits


def _default_workspace_root() -> Path:
    # Under $HOME because Colima's VM only shares $HOME, not the system temp dir.
    return Path.home() / ".cache" / "coding-agent" / "workspaces"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = None
    model_cheap: str = "llama-3.1-8b-instant"
    model_strong: str = "llama-3.3-70b-versatile"
    sandbox_image: str = "coding-agent-sandbox:latest"
    limits: Limits = Field(default_factory=Limits)
    max_repairs: int = 3
    max_replans: int = 2
    step_budget: int = 40
    workspace_root: Path = Field(default_factory=_default_workspace_root)


@lru_cache
def get_settings() -> Settings:
    return Settings()
