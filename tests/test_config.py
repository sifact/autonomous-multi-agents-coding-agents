from pathlib import Path

from coding_agent.config import Settings, get_settings
from coding_agent.sandbox import Limits


def test_defaults_match_spec(monkeypatch):
    for k in ("GROQ_API_KEY", "MODEL_STRONG", "MODEL_CHEAP"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert s.groq_api_key is None
    assert s.model_cheap == "llama-3.1-8b-instant"
    assert s.model_strong == "llama-3.3-70b-versatile"
    assert s.sandbox_image == "coding-agent-sandbox:latest"
    assert s.limits == Limits(512, 1.0, 30, 64, 64, False)
    assert (s.max_repairs, s.max_replans, s.step_budget) == (3, 2, 40)
    assert s.workspace_root == Path.home() / ".cache" / "coding-agent" / "workspaces"


def test_env_override(monkeypatch):
    monkeypatch.setenv("MODEL_STRONG", "x")
    assert Settings(_env_file=None).model_strong == "x"
    get_settings.cache_clear()
    assert get_settings().model_strong == "x"
    get_settings.cache_clear()
