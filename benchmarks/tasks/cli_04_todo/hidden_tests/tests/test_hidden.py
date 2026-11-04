import json
import os
import subprocess
import sys
from pathlib import Path

MAIN = Path("main.py").resolve()
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run(cwd, *args):
    return subprocess.run(
        [sys.executable, str(MAIN), *args], cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", env=ENV, timeout=10,
    )


def state(cwd):
    return json.loads((Path(cwd) / "todo.json").read_text(encoding="utf-8"))


def item(i, text, done=False):
    return {"id": i, "text": text, "done": done}


def test_add_prints_ids_and_persists_schema(tmp_path):
    r = run(tmp_path, "add", "buy", "milk")
    assert (r.returncode, r.stdout, r.stderr) == (0, "added 1\n", "")
    assert run(tmp_path, "add", "call Bob").stdout == "added 2\n"
    assert state(tmp_path) == {
        "next_id": 3, "items": [item(1, "buy milk"), item(2, "call Bob")],
    }


def test_add_strips_ends_but_keeps_inner_spacing(tmp_path):
    run(tmp_path, "add", "  two   spaces  ")
    run(tmp_path, "add", " ", "tab", "x ")
    assert [i["text"] for i in state(tmp_path)["items"]] == ["two   spaces", "tab x"]


def test_list_formats_open_and_done_items_in_id_order(tmp_path):
    for text in ("alpha", "bravo", "charlie"):
        run(tmp_path, "add", text)
    run(tmp_path, "done", "2")
    r = run(tmp_path, "list")
    assert (r.returncode, r.stdout) == (0, "[ ] 1 alpha\n[x] 2 bravo\n[ ] 3 charlie\n")
    assert run(tmp_path, "list", "--pending").stdout == "[ ] 1 alpha\n[ ] 3 charlie\n"


def test_empty_list_and_all_done_pending_say_no_items(tmp_path):
    r = run(tmp_path, "list")
    assert (r.returncode, r.stdout) == (0, "no items\n")
    assert not (tmp_path / "todo.json").exists()
    run(tmp_path, "add", "only")
    run(tmp_path, "done", "1")
    assert run(tmp_path, "list", "--pending").stdout == "no items\n"
    assert run(tmp_path, "list").stdout == "[x] 1 only\n"


def test_done_is_idempotent(tmp_path):
    run(tmp_path, "add", "task")
    first = run(tmp_path, "done", "1")
    before = (tmp_path / "todo.json").read_bytes()
    second = run(tmp_path, "done", "1")
    assert (first.returncode, first.stdout) == (0, "done 1\n")
    assert (second.returncode, second.stdout) == (0, "done 1\n")
    assert (tmp_path / "todo.json").read_bytes() == before
    assert state(tmp_path)["items"] == [item(1, "task", True)]


def test_ids_are_never_reused_after_rm(tmp_path):
    for text in ("a", "b", "c"):
        run(tmp_path, "add", text)
    r = run(tmp_path, "rm", "3")
    assert (r.returncode, r.stdout) == (0, "removed 3\n")
    assert run(tmp_path, "add", "d").stdout == "added 4\n"
    run(tmp_path, "rm", "1")
    assert state(tmp_path) == {"next_id": 5, "items": [item(2, "b"), item(4, "d")]}
    assert run(tmp_path, "list").stdout == "[ ] 2 b\n[ ] 4 d\n"


def test_rm_of_the_only_item_keeps_next_id(tmp_path):
    run(tmp_path, "add", "x")
    run(tmp_path, "rm", "1")
    assert state(tmp_path) == {"next_id": 2, "items": []}
    assert run(tmp_path, "list").stdout == "no items\n"


def test_unknown_id_exits_1_and_changes_nothing(tmp_path):
    run(tmp_path, "add", "x")
    before = (tmp_path / "todo.json").read_bytes()
    for cmd in ("done", "rm"):
        r = run(tmp_path, cmd, "7")
        assert (r.returncode, r.stdout) == (1, ""), cmd
        assert r.stderr.strip() == "error: no such id: 7"
    assert (tmp_path / "todo.json").read_bytes() == before
    run(tmp_path, "rm", "1")
    assert run(tmp_path, "rm", "1").returncode == 1


def test_usage_errors_exit_2_and_never_create_the_file(tmp_path):
    cases = [(), ("frobnicate",), ("add",), ("add", "  "), ("add", ""), ("done",),
             ("done", "x"), ("done", "0"), ("rm", "-1"), ("rm", "1.5"), ("rm", "1", "2"),
             ("done", "²"), ("done", "+1"), ("done", " 1"), ("rm", "1.0"), ("rm", "٣"),
             ("list", "extra"), ("list", "--bogus")]
    for args in cases:
        r = run(tmp_path, *args)
        assert r.returncode == 2, args
        assert r.stdout == "", args
        assert r.stderr.strip() != "", args
    assert not (tmp_path / "todo.json").exists()


def test_unicode_text_round_trips(tmp_path):
    run(tmp_path, "add", "café ☕")
    assert run(tmp_path, "list").stdout == "[ ] 1 café ☕\n"
    assert state(tmp_path)["items"][0]["text"] == "café ☕"


def test_corrupt_state_exits_3_for_every_command_and_is_unchanged(tmp_path):
    bad = [b"{oops", b"[]", b'{"next_id": 1}', b'{"next_id": "1", "items": []}',
           b'{"next_id": 2, "items": [{"id": 1, "text": "x"}]}',
           b'{"next_id": 2, "items": [{"id": "1", "text": "x", "done": false}]}',
           b'{"next_id": 2, "items": [{"id": 1, "text": "x", "done": 0}]}', b""]
    for content in bad:
        (tmp_path / "todo.json").write_bytes(content)
        for args in (("list",), ("add", "x"), ("done", "1"), ("rm", "1")):
            r = run(tmp_path, *args)
            assert (r.returncode, r.stdout) == (3, ""), (content, args)
            assert r.stderr.startswith("error:")
            assert (tmp_path / "todo.json").read_bytes() == content


def test_preexisting_state_is_honoured(tmp_path):
    seed = {"next_id": 10, "items": [item(4, "old", True), item(9, "newer")]}
    (tmp_path / "todo.json").write_text(json.dumps(seed), encoding="utf-8")
    assert run(tmp_path, "list").stdout == "[x] 4 old\n[ ] 9 newer\n"
    assert run(tmp_path, "add", "fresh").stdout == "added 10\n"
    assert run(tmp_path, "done", "9").stdout == "done 9\n"
    assert state(tmp_path) == {
        "next_id": 11, "items": [item(4, "old", True), item(9, "newer", True), item(10, "fresh")],
    }


ODD = (b'{ "next_id":3,\n  "items" : [ {"id":1,"text":"caf\xc3\xa9",  "done":false} ,\n'
       b'{"id":2 , "text":"y","done":true}]}\n\n')


def test_hand_formatted_file_is_byte_identical_after_reads_and_failures(tmp_path):
    path = tmp_path / "todo.json"
    path.write_bytes(ODD)
    cases = [("list",), ("list", "--pending"), ("done", "2"), ("done", "9"), ("rm", "9"),
             ("rm", "0"), ("done", "0"), ("rm", "-1"), ("done", "x"), ("rm",), ("add",),
             ("add", " "), ("frob",), (), ("list", "x"), ("rm", "1", "2"), ("done", "+1")]
    for args in cases:
        run(tmp_path, *args)
        assert path.read_bytes() == ODD, args
    assert run(tmp_path, "list").stdout == "[ ] 1 café\n[x] 2 y\n"
    assert run(tmp_path, "add", "z").stdout == "added 3\n"
