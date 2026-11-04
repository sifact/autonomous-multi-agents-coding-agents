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
    return json.loads((Path(cwd) / "bookmarks.json").read_text(encoding="utf-8"))


def item(i, url, title=None, tags=()):
    return {"id": i, "url": url, "title": title or url, "tags": list(tags)}


def test_add_prints_ids_and_persists_schema(tmp_path):
    r = run(tmp_path, "add", "https://a.example", "--title", "A site", "--tag", "News")
    assert (r.returncode, r.stdout, r.stderr) == (0, "added 1\n", "")
    r = run(tmp_path, "add", "https://b.example")
    assert r.stdout == "added 2\n"
    assert state(tmp_path) == {"next_id": 3, "items": [
        item(1, "https://a.example", "A site", ["news"]),
        item(2, "https://b.example"),
    ]}


def test_options_may_precede_the_url_and_tags_are_normalised(tmp_path):
    run(tmp_path, "add", "--tag", " Tech ", "--tag", "news", "--tag", "TECH", "u.example")
    assert state(tmp_path)["items"] == [item(1, "u.example", None, ["tech", "news"])]
    run(tmp_path, "add", "  spaced.example  ", "--title", "T")
    assert state(tmp_path)["items"][1] == item(2, "spaced.example", "T")


def test_adding_an_existing_url_merges_tags_instead_of_duplicating(tmp_path):
    run(tmp_path, "add", "https://a.example", "--title", "First", "--tag", "x", "--tag", "y")
    before_next = state(tmp_path)["next_id"]
    r = run(tmp_path, "add", "https://a.example", "--title", "Other", "--tag", "z",
            "--tag", "X", "--tag", "w")
    assert (r.returncode, r.stdout) == (0, "exists 1\n")
    assert state(tmp_path) == {"next_id": before_next, "items": [
        item(1, "https://a.example", "First", ["x", "y", "z", "w"]),
    ]}
    # URL comparison is exact: a different case is a different bookmark
    assert run(tmp_path, "add", "HTTPS://A.EXAMPLE").stdout == "added 2\n"


def test_list_format_is_tab_separated_with_empty_tag_field(tmp_path):
    run(tmp_path, "add", "https://a.example", "--title", "Alpha", "--tag", "b", "--tag", "a")
    run(tmp_path, "add", "https://b.example")
    r = run(tmp_path, "list")
    assert r.returncode == 0
    assert r.stdout == "1\tAlpha\thttps://a.example\tb,a\n2\thttps://b.example\thttps://b.example\t\n"


def test_list_filter_by_tag_is_case_insensitive_and_keeps_id_order(tmp_path):
    run(tmp_path, "add", "u1", "--tag", "news")
    run(tmp_path, "add", "u2", "--tag", "tech")
    run(tmp_path, "add", "u3", "--tag", "tech", "--tag", "news")
    assert run(tmp_path, "list", "--tag", " NEWS ").stdout == "1\tu1\tu1\tnews\n3\tu3\tu3\ttech,news\n"
    assert run(tmp_path, "list", "--tag", "nothing").stdout == ""
    assert run(tmp_path, "list", "--tag", "ne").stdout == ""


def test_empty_state_lists_print_nothing_and_do_not_create_the_file(tmp_path):
    for args in (("list",), ("tags",), ("list", "--tag", "x")):
        r = run(tmp_path, *args)
        assert (r.returncode, r.stdout) == (0, ""), args
    assert not (tmp_path / "bookmarks.json").exists()


def test_tags_sorted_by_count_desc_then_name(tmp_path):
    run(tmp_path, "add", "u1", "--tag", "zeta", "--tag", "beta", "--tag", "mid")
    run(tmp_path, "add", "u2", "--tag", "zeta", "--tag", "alpha")
    run(tmp_path, "add", "u3", "--tag", "mid", "--tag", "zeta")
    r = run(tmp_path, "tags")
    assert (r.returncode, r.stdout) == (0, "zeta 3\nmid 2\nalpha 1\nbeta 1\n")


def test_rm_removes_and_ids_are_not_reused(tmp_path):
    for url in ("u1", "u2", "u3"):
        run(tmp_path, "add", url, "--tag", "t")
    r = run(tmp_path, "rm", "3")
    assert (r.returncode, r.stdout) == (0, "removed 3\n")
    assert run(tmp_path, "add", "u4").stdout == "added 4\n"
    run(tmp_path, "rm", "1")
    assert state(tmp_path) == {"next_id": 5, "items": [item(2, "u2", None, ["t"]), item(4, "u4")]}
    assert run(tmp_path, "tags").stdout == "t 1\n"
    # re-adding a removed URL creates a new bookmark with a new id
    assert run(tmp_path, "add", "u1").stdout == "added 5\n"


def test_rm_unknown_id_exits_1_and_changes_nothing(tmp_path):
    run(tmp_path, "add", "u1")
    before = (tmp_path / "bookmarks.json").read_bytes()
    r = run(tmp_path, "rm", "9")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr.strip() == "error: no such id: 9"
    assert (tmp_path / "bookmarks.json").read_bytes() == before


def test_usage_errors_exit_2_and_never_create_the_file(tmp_path):
    cases = [(), ("frob",), ("add",), ("add", "  "), ("add", "u", "--tag", " "),
             ("add", "u", "--tag"), ("add", "u", "extra"), ("rm",), ("rm", "x"),
             ("rm", "0"), ("rm", "-2"), ("rm", "1", "2"), ("tags", "x"), ("list", "x")]
    for args in cases:
        r = run(tmp_path, *args)
        assert r.returncode == 2, args
        assert r.stdout == "", args
        assert r.stderr.strip() != "", args
    assert not (tmp_path / "bookmarks.json").exists()


def test_unicode_titles_and_tags(tmp_path):
    run(tmp_path, "add", "https://ü.example", "--title", "Übersicht ✓", "--tag", "Ärger")
    assert run(tmp_path, "list").stdout == "1\tÜbersicht ✓\thttps://ü.example\tärger\n"
    assert run(tmp_path, "list", "--tag", "ÄRGER").stdout.startswith("1\t")


def test_corrupt_state_exits_3_for_every_command_and_is_unchanged(tmp_path):
    bad = [b"{oops", b"[]", b'{"next_id": 1}', b'{"next_id": 2, "items": [{"id": 1}]}',
           b'{"next_id": 2, "items": [{"id": 1, "url": "u", "title": "t", "tags": [1]}]}']
    for content in bad:
        (tmp_path / "bookmarks.json").write_bytes(content)
        for args in (("list",), ("tags",), ("add", "u"), ("rm", "1")):
            r = run(tmp_path, *args)
            assert (r.returncode, r.stdout) == (3, ""), (content, args)
            assert r.stderr.strip() != ""
            assert (tmp_path / "bookmarks.json").read_bytes() == content
