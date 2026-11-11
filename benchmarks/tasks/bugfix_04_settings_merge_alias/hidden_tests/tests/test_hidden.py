import copy

import settings
from settings import DEFAULTS, build_settings, merge

ORIGINAL = copy.deepcopy(DEFAULTS)


def test_build_settings_does_not_change_defaults():
    result = build_settings({"editor": {"tabs": 2}})
    assert result["editor"]["tabs"] == 2
    assert settings.DEFAULTS == ORIGINAL


def test_second_user_gets_clean_defaults():
    build_settings({"editor": {"tabs": 2, "wrap": True}, "paths": {"cache": "/x"}})
    fresh = build_settings()
    assert fresh == ORIGINAL
    assert fresh["editor"] == {"font_size": 12, "tabs": 4, "wrap": False}


def test_merge_does_not_modify_base():
    base = {"a": {"b": 1, "c": {"d": 2}}, "e": [1]}
    snapshot = copy.deepcopy(base)
    result = merge(base, {"a": {"c": {"d": 3}}, "e": [9]})
    assert result == {"a": {"b": 1, "c": {"d": 3}}, "e": [9]}
    assert base == snapshot


def test_merge_does_not_modify_overrides():
    overrides = {"a": {"x": [1, 2]}, "n": 1}
    snapshot = copy.deepcopy(overrides)
    merge({"a": {"y": 1}}, overrides)
    assert overrides == snapshot


def test_result_shares_nothing_with_defaults():
    result = build_settings({"theme": "dark"})
    result["paths"]["logs"].append("/extra")
    result["editor"]["font_size"] = 99
    assert settings.DEFAULTS == ORIGINAL


def test_result_shares_nothing_with_overrides():
    overrides = {"paths": {"logs": ["/mine"]}, "editor": {"extra": {"deep": [1]}}}
    result = build_settings(overrides)
    result["paths"]["logs"].append("/other")
    result["editor"]["extra"]["deep"].append(2)
    assert overrides == {"paths": {"logs": ["/mine"]}, "editor": {"extra": {"deep": [1]}}}


def test_nested_dicts_are_merged_key_by_key():
    result = build_settings({"editor": {"tabs": 2}, "paths": {"logs": ["/a", "/b"]}})
    assert result == {
        "theme": "light",
        "editor": {"font_size": 12, "tabs": 2, "wrap": False},
        "paths": {"cache": "/tmp/cache", "logs": ["/a", "/b"]},
    }


def test_replacement_rules_for_non_dicts():
    assert merge({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}
    assert merge({"a": 1}, {"a": {"b": 2}}) == {"a": {"b": 2}}
    assert merge({"a": {"b": 2}}, {"a": None}) == {"a": None}
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert merge({}, {}) == {}


def test_nothing_to_merge_still_returns_a_new_structure():
    result = build_settings()
    assert result is not settings.DEFAULTS
    assert result == ORIGINAL
    result["paths"]["logs"].append("/x")
    result["editor"]["tabs"] = 9
    assert settings.DEFAULTS == ORIGINAL


def test_merge_with_empty_overrides_copies_nested_containers():
    base = {"a": {"b": [1]}, "c": [2]}
    result = merge(base, {})
    assert result == base
    assert result is not base
    result["a"]["b"].append(9)
    result["c"].append(9)
    assert base == {"a": {"b": [1]}, "c": [2]}
