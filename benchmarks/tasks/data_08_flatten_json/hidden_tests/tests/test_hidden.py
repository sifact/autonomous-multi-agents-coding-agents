import json

from solution import flatten_file

EXPECTED = {'name': 'svc',
 'debug': False,
 'port': 8080,
 'owner': None,
 'db.host': 'localhost',
 'db.ports.0': 5432,
 'db.ports.1': 5433,
 'db.opts': {},
 'servers.0.id': 1,
 'servers.0.tags.0': 'a',
 'servers.0.tags.1': 'b',
 'servers.1.id': 2,
 'servers.1.tags': [],
 'limits.cpu.max': 2.5,
 'limits.cpu.min': 0.5}


def write(tmp_path, obj):
    p = tmp_path / "d.json"
    p.write_text(json.dumps(obj))
    return str(p)


def test_fixture_values_and_order():
    result = flatten_file("config.json")
    assert list(result) == list(EXPECTED)
    assert result == EXPECTED


def test_lists_and_nesting(tmp_path):
    path = write(tmp_path, {"a": [5, {"b": [6]}], "c": {"d": {"e": "x"}}})
    assert flatten_file(path) == {"a.0": 5, "a.1.b.0": 6, "c.d.e": "x"}


def test_custom_separator(tmp_path):
    path = write(tmp_path, {"a": {"b": [1]}})
    assert flatten_file(path, sep="/") == {"a/b/0": 1}


def test_empty_containers_are_leaves_and_types_kept(tmp_path):
    path = write(tmp_path, {"e1": {}, "e2": [], "n": None, "t": True, "f": 1.5, "z": 0})
    result = flatten_file(path)
    assert result == {"e1": {}, "e2": [], "n": None, "t": True, "f": 1.5, "z": 0}
    assert result["t"] is True and result["n"] is None


def test_empty_string_keys_are_ordinary_keys(tmp_path):
    path = write(tmp_path, {"": 1, "a": {"": 2, "b": 3}, "c": {"": {}}})
    assert flatten_file(path) == {"": 1, "a.": 2, "a.b": 3, "c.": {}}


def test_top_level_array_and_empty(tmp_path):
    assert flatten_file(write(tmp_path, [{"x": 1}, [2]])) == {"0.x": 1, "1.0": 2}
    assert flatten_file(write(tmp_path, {})) == {}
    assert flatten_file(write(tmp_path, [])) == {}
