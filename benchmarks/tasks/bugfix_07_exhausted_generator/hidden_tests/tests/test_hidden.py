import pytest

from numstats import parse_numbers, summarize


def test_summary_of_a_list():
    result = summarize(["3", "1", "2"])
    assert result == {"count": 3, "min": 1.0, "max": 3.0, "mean": 2.0}


def test_summary_of_a_one_pass_generator():
    result = summarize(line for line in ["10", "-4.5", "7.5", "0"])
    assert result["count"] == 4
    assert result["min"] == -4.5
    assert result["max"] == 10.0
    assert result["mean"] == pytest.approx(3.25)


def test_single_number():
    assert summarize(["42"]) == {"count": 1, "min": 42.0, "max": 42.0, "mean": 42.0}


def test_blank_lines_and_whitespace_are_ignored():
    result = summarize(["  5 \n", "", "   ", "\n", "15\n"])
    assert result == {"count": 2, "min": 5.0, "max": 15.0, "mean": 10.0}


def test_key_types():
    result = summarize(iter(["1", "2", "4"]))
    assert set(result) == {"count", "min", "max", "mean"}
    assert type(result["count"]) is int
    assert result["mean"] == pytest.approx(7 / 3)


def test_no_numbers():
    empty = {"count": 0, "min": None, "max": None, "mean": None}
    assert summarize([]) == empty
    assert summarize(["", "  ", "\n"]) == empty
    assert summarize(iter([])) == empty


def test_a_bad_line_raises_value_error():
    with pytest.raises(ValueError):
        summarize(["1", "two", "3"])


def test_parse_numbers_is_lazy_and_one_pass():
    it = parse_numbers(iter(["1", "", "2.5", "oops"]))
    assert iter(it) is it
    assert next(it) == 1.0
    assert next(it) == 2.5
    with pytest.raises(ValueError):
        next(it)
    assert list(parse_numbers(["4", " ", "5"])) == [4.0, 5.0]


def test_parse_numbers_reads_only_what_is_asked_for():
    consumed = []

    def source():
        for text in ["5", "6", "7", "8"]:
            consumed.append(text)
            yield text

    lazy = parse_numbers(source())
    assert consumed == []
    assert next(lazy) == 5.0
    assert consumed == ["5"]
    assert next(lazy) == 6.0
    assert consumed == ["5", "6"]
