"""Tracing tests never reach a network: enabled mode exports into an in-memory exporter."""
import uuid

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from coding_agent.config import Settings
from coding_agent.tracing import langfuse_setup

LOOPBACK = "http://127.0.0.1:9"

PUBLIC, SECRET = "pk-lf-TESTPUBLIC0000", "sk-lf-TESTSECRET0000"


@pytest.fixture(autouse=True)
def _offline(no_external_network):
    """Every tracing test fails if it resolves or connects to a non-loopback host."""


@pytest.fixture
def keyed():
    # Langfuse keeps one client per public key for the whole process, so every test
    # gets its own key; otherwise a later test would reuse an earlier shut-down exporter.
    public = f"{PUBLIC}-{uuid.uuid4().hex[:8]}"
    return Settings(langfuse_public_key=public, langfuse_secret_key=SECRET,
                    langfuse_host=LOOPBACK, _env_file=None)


@pytest.fixture
def unkeyed(monkeypatch):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    return Settings(_env_file=None)


@pytest.fixture
def memory(monkeypatch):
    """Real Langfuse client (real masking, real handler) whose spans go to memory."""
    from langfuse import Langfuse

    exporter = InMemorySpanExporter()
    real = Langfuse

    def new_client(settings):
        return real(**{**langfuse_setup.client_kwargs(settings), "span_exporter": exporter})

    monkeypatch.setattr(langfuse_setup, "_new_client", new_client)
    # create_score posts from a background thread whatever the span exporter is: stub it.
    exporter.scores = []
    monkeypatch.setattr(real, "create_score", lambda self, **kw: exporter.scores.append(kw))
    langfuse_setup.reset()
    yield exporter
    langfuse_setup.reset()
