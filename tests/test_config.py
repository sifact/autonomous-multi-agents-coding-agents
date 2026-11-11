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


def test_api_key_is_secret_in_repr_and_str():
    s = Settings(groq_api_key="gsk_SENTINEL_xyz", _env_file=None)
    assert "gsk_SENTINEL_xyz" not in repr(s) and "gsk_SENTINEL_xyz" not in str(s)
    assert s.groq_api_key.get_secret_value() == "gsk_SENTINEL_xyz"


def test_langfuse_settings_default_off(monkeypatch):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert s.langfuse_public_key is None and s.langfuse_secret_key is None
    assert s.langfuse_host == "https://cloud.langfuse.com"


def test_langfuse_env_names_and_secrecy(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-PUBSENTINEL")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-SECSENTINEL")
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
    s = Settings(_env_file=None)
    assert s.langfuse_host == "http://localhost:3000"
    assert s.langfuse_secret_key.get_secret_value() == "sk-lf-SECSENTINEL"
    shown = repr(s) + str(s)
    assert "PUBSENTINEL" not in shown and "SECSENTINEL" not in shown
