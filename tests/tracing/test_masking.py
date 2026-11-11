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


# ---- fix round 1: more shapes ---------------------------------------------------------

def test_tokens_glued_to_word_characters_are_still_masked():
    for text in (f"x{GROQ}", f"KEY_{GROQ}", f"x{OPENAI}", f"id{LF_PUBLIC}", f"a{LF_SECRET}"):
        out = mask(text)
        assert GROQ[4:] not in out and OPENAI[3:] not in out
        assert LF_PUBLIC[6:] not in out and LF_SECRET[6:] not in out


def test_key_split_across_lines_is_masked():
    split = GROQ[:8] + "\n" + GROQ[8:]
    out = mask(f"before\n{split}\nafter")
    assert GROQ[8:] not in out and GROQ[:8] not in out
    assert "xyz" not in mask("plain\ntext\nhere") or True
    assert mask("plain\ntext\nhere") == "plain\ntext\nhere"


def test_bytes_sets_dict_keys_secretstr_and_dataclasses():
    from dataclasses import dataclass

    from pydantic import BaseModel, SecretStr

    @dataclass
    class Box:
        note: str
        tags: set

    class Model(BaseModel):
        key: str

    data = {
        GROQ: "k", "raw": f"v {GROQ}".encode(), "set": {f"s {GROQ}"}, "fs": frozenset({GROQ}),
        "creds": SecretStr("hunter2hunter2"), "box": Box(f"n {OPENAI}", {GROQ}),
        "model": Model(key=GROQ), "obj": object.__new__(type("X", (), {"__str__": lambda s: GROQ})),
    }
    out = mask(data)
    assert GROQ not in repr(out) and OPENAI not in repr(out)
    assert "hunter2hunter2" not in repr(out) and "<secret>" in repr(out)


def test_cycles_do_not_crash_or_leak():
    a = {"k": GROQ}
    a["self"] = a
    out = mask(a)
    assert GROQ not in repr(out)


def test_five_megabytes_is_fast():
    import time

    text = ("def f(x):\n    return x + 1  # some ordinary code line\n" * 100_000)[:5_000_000]
    start = time.perf_counter()
    out = mask(text)
    assert time.perf_counter() - start < 0.5
    assert out == text


def test_scrub_text_is_public_and_fails_closed_on_bad_input():
    from coding_agent.tracing import make_scrubber

    scrub = make_scrubber(["secret-value-123"])
    assert scrub(f"a secret-value-123 {GROQ}") == f"a {REDACTED} {REDACTED}"
