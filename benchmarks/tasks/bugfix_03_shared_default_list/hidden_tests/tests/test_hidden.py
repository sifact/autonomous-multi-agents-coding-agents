from logscan import collect_problems, count_by_level


def test_second_call_does_not_see_the_first():
    assert collect_problems(["ERROR disk full", "INFO started"]) == ["ERROR disk full"]
    assert collect_problems(["WARN low memory"]) == ["WARN low memory"]


def test_every_call_returns_its_own_list():
    first = collect_problems(["WARN a"])
    second = collect_problems(["WARN b"])
    assert first is not second
    first.append("extra")
    assert collect_problems([]) == []


def test_no_problems_gives_an_empty_list_even_after_earlier_calls():
    collect_problems(["ERROR x", "ERROR y"])
    assert collect_problems(["INFO fine"]) == []
    assert collect_problems([]) == []


def test_explicit_list_is_extended_and_returned():
    mine = ["earlier"]
    result = collect_problems(["WARN one", "INFO two", "ERROR three"], mine)
    assert result is mine
    assert mine == ["earlier", "WARN one", "ERROR three"]
    collect_problems(["ERROR four"], mine)
    assert mine == ["earlier", "WARN one", "ERROR three", "ERROR four"]


def test_explicit_empty_list_is_filled_in_place():
    mine = []
    assert collect_problems(["ERROR boom"], found=mine) is mine
    assert mine == ["ERROR boom"]


def test_level_must_be_the_whole_first_word():
    lines = ["WARNING disk", "ERRORS found", "INFO WARN inside", "  WARN  indented  ", "ERROR"]
    assert collect_problems(lines) == ["WARN  indented", "ERROR"]


def test_works_with_any_iterable_of_lines():
    assert collect_problems(line for line in ["ERROR a", "OK", "WARN b"]) == ["ERROR a", "WARN b"]


def test_count_by_level_is_unchanged():
    lines = ["WARN a", "ERROR b", " ERROR c", "INFO d", "WARNING e", "WARN f"]
    assert count_by_level(lines) == {"WARN": 2, "ERROR": 2}
    assert count_by_level([]) == {"WARN": 0, "ERROR": 0}
