import subprocess
import sys
import threading

import pytest
from langfuse.langchain import CallbackHandler

from coding_agent.config import Settings
from coding_agent.tracing import (
    flush,
    get_callbacks,
    langfuse_setup,
    tracing_enabled,
    tracing_status_line,
)

from .conftest import PUBLIC, SECRET


def test_enabled_needs_both_keys(unkeyed):
    assert not tracing_enabled(unkeyed)
    assert not tracing_enabled(Settings(langfuse_public_key=PUBLIC, _env_file=None))
    assert not tracing_enabled(Settings(langfuse_secret_key=SECRET, _env_file=None))
    assert not tracing_enabled(Settings(langfuse_public_key="", langfuse_secret_key="",
                                        _env_file=None))
    assert tracing_enabled(Settings(langfuse_public_key=PUBLIC, langfuse_secret_key=SECRET,
                                    _env_file=None))


def test_disabled_returns_empty_and_builds_no_client(unkeyed, monkeypatch):
    def boom(settings):
        raise AssertionError("no client may be constructed without keys")
    monkeypatch.setattr(langfuse_setup, "_new_client", boom)
    before = threading.active_count()
    assert get_callbacks(unkeyed) == []
    assert threading.active_count() == before


def test_disabled_does_not_even_import_langfuse():
    code = (
        "import sys\n"
        "from coding_agent.config import Settings\n"
        "from coding_agent.tracing import get_callbacks, tracing_status_line, flush\n"
        "s = Settings(_env_file=None)\n"
        "assert get_callbacks(s) == []\n"
        "flush()\n"
        "tracing_status_line(s)\n"
        "assert 'langfuse' not in sys.modules, 'langfuse was imported'\n"
    )
    env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"}
    out = subprocess.run([sys.executable, "-I", "-c", code], env=env, capture_output=True,
                         text=True, check=False)
    assert out.returncode == 0, out.stderr


def test_enabled_returns_exactly_one_handler_and_reuses_the_client(keyed, memory):
    handlers = get_callbacks(keyed)
    assert len(handlers) == 1 and isinstance(handlers[0], CallbackHandler)
    assert len(get_callbacks(keyed)) == 1
    assert len(langfuse_setup._clients) == 1


def test_client_is_configured_from_settings(keyed):
    kwargs = langfuse_setup.client_kwargs(Settings(
        langfuse_public_key=PUBLIC, langfuse_secret_key=SECRET,
        langfuse_host="http://127.0.0.1:9", _env_file=None))
    assert kwargs["public_key"] == PUBLIC and kwargs["secret_key"] == SECRET
    assert kwargs["base_url"] == "http://127.0.0.1:9"
    masked = kwargs["mask"](data=f"leak {SECRET} and {PUBLIC}")
    assert SECRET not in masked and PUBLIC not in masked


def test_handler_creation_failure_is_a_warning_not_an_error(keyed, monkeypatch, caplog):
    def boom(settings):
        raise RuntimeError("dns down")
    monkeypatch.setattr(langfuse_setup, "_new_client", boom)
    langfuse_setup.reset()
    assert get_callbacks(keyed) == []
    assert "Langfuse tracing disabled" in caplog.text and "dns down" in caplog.text
    assert SECRET not in caplog.text


def test_flush_flushes_clients_and_never_raises(keyed, memory):
    get_callbacks(keyed)
    client = next(iter(langfuse_setup._clients.values()))
    calls = []
    client.flush = lambda: calls.append(1)
    flush()
    assert calls == [1]

    def broken():
        raise OSError("offline")
    client.flush = broken
    flush()  # must not raise
    flush(object())  # nothing to flush: no-op


def test_status_line(keyed, unkeyed):
    assert tracing_status_line(unkeyed) == (
        "Langfuse tracing: off (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable)")
    on = tracing_status_line(keyed)
    assert on == "Langfuse tracing: on (http://127.0.0.1:9)"
    assert SECRET not in on and PUBLIC not in on


@pytest.mark.parametrize("host", ["http://localhost:3000/", "http://localhost:3000"])
def test_status_line_shows_the_host(host):
    s = Settings(langfuse_public_key=PUBLIC, langfuse_secret_key=SECRET, langfuse_host=host,
                 _env_file=None)
    assert tracing_status_line(s) == "Langfuse tracing: on (http://localhost:3000)"


def test_the_network_guard_really_blocks_external_hosts():
    import socket

    with pytest.raises(AssertionError, match="non-loopback"):
        socket.getaddrinfo("cloud.langfuse.com", 443)
    with pytest.raises(AssertionError, match="non-loopback"):
        socket.create_connection(("203.0.113.7", 80), timeout=0.1)


def test_default_settings_host_is_cloud_but_keyed_fixture_is_loopback(keyed):
    assert keyed.langfuse_host.startswith("http://127.0.0.1")


def test_client_kwargs_bound_the_exit_delay(keyed):
    kw = langfuse_setup.client_kwargs(keyed)
    assert kw["timeout"] == 2 and kw["flush_interval"] <= 1 and kw["flush_at"] <= 64
    longer = langfuse_setup.client_kwargs(keyed.model_copy(update={"langfuse_timeout": 7}))
    assert longer["timeout"] == 7
    assert "mask_otel_spans" in kw and "tracer_provider" in kw


def test_timeout_env_name(monkeypatch):
    monkeypatch.setenv("LANGFUSE_TIMEOUT", "9")
    assert Settings(_env_file=None).langfuse_timeout == 9


def test_failed_client_creation_warns_once_per_key(keyed, monkeypatch, caplog):
    calls = []

    def boom(settings):
        calls.append(1)
        raise RuntimeError("nope")

    monkeypatch.setattr(langfuse_setup, "_new_client", boom)
    langfuse_setup.reset()
    for _ in range(3):
        assert get_callbacks(keyed) == []
    assert len(calls) == 1
    assert caplog.text.count("Langfuse tracing disabled") == 1
