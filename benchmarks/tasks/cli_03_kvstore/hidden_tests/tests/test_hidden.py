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


def state(cwd, name="store.json"):
    return json.loads((Path(cwd) / name).read_text(encoding="utf-8"))


def test_set_then_get_across_invocations(tmp_path):
    r = run(tmp_path, "set", "name", "Ada")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    r = run(tmp_path, "get", "name")
    assert (r.returncode, r.stdout) == (0, "Ada\n")
    assert state(tmp_path) == {"name": "Ada"}


def test_set_keeps_other_keys_and_overwrites_existing(tmp_path):
    run(tmp_path, "set", "a", "1")
    run(tmp_path, "set", "b", "2")
    run(tmp_path, "set", "a", "3")
    assert state(tmp_path) == {"a": "3", "b": "2"}
    assert run(tmp_path, "get", "b").stdout == "2\n"


def test_values_are_always_strings_and_may_be_empty_or_contain_equals(tmp_path):
    run(tmp_path, "set", "port", "8080")
    run(tmp_path, "set", "empty", "")
    run(tmp_path, "set", "eq", "a=b c")
    assert state(tmp_path) == {"port": "8080", "empty": "", "eq": "a=b c"}
    assert run(tmp_path, "get", "empty").stdout == "\n"
    assert run(tmp_path, "get", "eq").stdout == "a=b c\n"


def test_list_is_sorted_by_key_not_insertion_order(tmp_path):
    for key, value in (("pear", "3"), ("Zed", "1"), ("apple", "2"), ("éclair", "4")):
        run(tmp_path, "set", key, value)
    r = run(tmp_path, "list")
    assert r.returncode == 0
    assert r.stdout == "Zed=1\napple=2\npear=3\néclair=4\n"


def test_unicode_round_trip(tmp_path):
    run(tmp_path, "set", "greeting", "héllo wörld ✓")
    assert run(tmp_path, "get", "greeting").stdout == "héllo wörld ✓\n"
    assert state(tmp_path) == {"greeting": "héllo wörld ✓"}


def test_del_removes_only_that_key_and_last_removal_leaves_empty_object(tmp_path):
    run(tmp_path, "set", "a", "1")
    run(tmp_path, "set", "b", "2")
    r = run(tmp_path, "del", "a")
    assert (r.returncode, r.stdout) == (0, "")
    assert state(tmp_path) == {"b": "2"}
    run(tmp_path, "del", "b")
    assert state(tmp_path) == {}
    assert run(tmp_path, "list").stdout == ""


def test_missing_key_errors_exit_1_and_leave_file_untouched(tmp_path):
    run(tmp_path, "set", "a", "1")
    before = (tmp_path / "store.json").read_bytes()
    for cmd in ("get", "del"):
        r = run(tmp_path, cmd, "nokey")
        assert (r.returncode, r.stdout) == (1, ""), cmd
        assert r.stderr.startswith("error:") and "nokey" in r.stderr
    assert (tmp_path / "store.json").read_bytes() == before


def test_read_commands_do_not_create_the_file(tmp_path):
    assert run(tmp_path, "list").stdout == ""
    assert run(tmp_path, "get", "x").returncode == 1
    assert run(tmp_path, "del", "x").returncode == 1
    assert not (tmp_path / "store.json").exists()


def test_custom_file_option(tmp_path):
    r = run(tmp_path, "--file", "other.json", "set", "k", "v")
    assert r.returncode == 0
    assert state(tmp_path, "other.json") == {"k": "v"}
    assert not (tmp_path / "store.json").exists()
    assert run(tmp_path, "--file", "other.json", "get", "k").stdout == "v\n"
    assert run(tmp_path, "get", "k").returncode == 1


def test_usage_errors_exit_2(tmp_path):
    for args in ((), ("frobnicate",), ("set", "a"), ("set", "a", "b", "c"), ("get",),
                 ("del", "a", "b"), ("list", "extra"), ("set", "", "x")):
        r = run(tmp_path, *args)
        assert r.returncode == 2, args
        assert r.stdout == "", args
        assert r.stderr.strip() != "", args
    assert not (tmp_path / "store.json").exists()


ODD = b'{ "zeta":"1",\n\n   "alpha" :   "caf\xc3\xa9",\t"mid":"x" }\n\n'


def test_failures_and_reads_leave_a_hand_formatted_file_byte_identical(tmp_path):
    path = tmp_path / "store.json"
    path.write_bytes(ODD)
    cases = [("get", "zeta"), ("list",), ("get", "nokey"), ("del", "nokey"), (),
             ("frobnicate",), ("set", "a"), ("set", "a", "b", "c"), ("get",),
             ("del", "a", "b"), ("list", "extra"), ("set", "", "x"), ("--file",)]
    for args in cases:
        run(tmp_path, *args)
        assert path.read_bytes() == ODD, args
    assert run(tmp_path, "list").stdout == "alpha=café\nmid=x\nzeta=1\n"


def test_values_and_keys_may_start_with_a_dash(tmp_path):
    assert run(tmp_path, "set", "mode", "-v").returncode == 0
    assert run(tmp_path, "set", "-k", "--file").returncode == 0
    assert run(tmp_path, "set", "n", "-5").returncode == 0
    assert state(tmp_path) == {"mode": "-v", "-k": "--file", "n": "-5"}
    assert run(tmp_path, "get", "-k").stdout == "--file\n"
    assert run(tmp_path, "del", "-k").returncode == 0
    assert run(tmp_path, "--file", "o.json", "set", "x", "-y").returncode == 0
    assert state(tmp_path, "o.json") == {"x": "-y"}


def test_corrupt_files_exit_3_for_every_command_and_stay_unchanged(tmp_path):
    for content in (b"{not json", b'["a", "b"]', b'{"a": 1}', b'{"a": {"b": "c"}}', b""):
        (tmp_path / "store.json").write_bytes(content)
        for args in (("list",), ("get", "a"), ("set", "a", "x"), ("del", "a")):
            r = run(tmp_path, *args)
            assert (r.returncode, r.stdout) == (3, ""), (content, args)
            assert r.stderr.startswith("error:")
            assert (tmp_path / "store.json").read_bytes() == content
