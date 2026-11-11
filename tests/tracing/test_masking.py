"""The mask runs on everything sent to Langfuse; nothing key-like may get through."""
from coding_agent.tracing import REDACTED, make_mask

GROQ = "gsk_" + "a1B2c3D4e5F6g7H8i9J0"
OPENAI = "sk-proj-" + "abcDEF123456789xyz"
LF_SECRET = "sk-lf-" + "11111111-2222-3333-4444-555555555555"
LF_PUBLIC = "pk-lf-" + "66666666-7777-8888-9999-000000000000"


def mask(data, *secrets):
    return make_mask(secrets)(data=data)


def test_key_shaped_strings_are_redacted():
    for secret in (GROQ, OPENAI, LF_SECRET, LF_PUBLIC):
        out = mask(f"my key is {secret} ok")
        assert secret not in out and REDACTED in out and out.startswith("my key is")


def test_authorization_headers_are_redacted():
    out = mask("Authorization: Bearer abc.def.ghi\nnext line")
    assert "abc.def.ghi" not in out and "next line" in out
    assert "abc123tokenvalue" not in mask("curl -H 'authorization: Basic abc123tokenvalue'")


def test_configured_secrets_are_redacted_even_when_oddly_shaped():
    out = mask({"a": "value hunter2-weird-secret here"}, "hunter2-weird-secret")
    assert "hunter2-weird-secret" not in str(out)


def test_walks_nested_structures_and_sensitive_keys():
    data = {"messages": [{"content": f"use {GROQ}"}], "headers": {"Authorization": "Basic zzz"},
            "api_key": "whatever", "n": 3, "ok": True, "none": None, "t": (f"x {OPENAI}",)}
    out = mask(data)
    text = repr(out)
    for leak in (GROQ, OPENAI, "Basic zzz", "whatever"):
        assert leak not in text
    assert out["n"] == 3 and out["ok"] is True and out["none"] is None


def test_innocent_text_and_code_are_untouched():
    code = "def mask(x):\n    return x  # sk is short\nprint('task-management-system desk-lamp')"
    assert mask(code) == code
    assert mask({"plan": ["step one", "step two"]}) == {"plan": ["step one", "step two"]}


def test_does_not_mutate_input():
    data = {"k": [GROQ]}
    mask(data)
    assert data == {"k": [GROQ]}
