from runs import is_constant, longest_run, run_lengths


def test_last_block_is_reported():
    assert run_lengths([1, 1, 2, 2, 2]) == [(1, 2), (2, 3)]
    assert run_lengths([1, 2, 3]) == [(1, 1), (2, 1), (3, 1)]


def test_single_value_and_all_equal():
    assert run_lengths([5]) == [(5, 1)]
    assert run_lengths(["x", "x", "x"]) == [("x", 3)]


def test_empty_input_has_no_runs():
    assert run_lengths([]) == []
    assert run_lengths(iter([])) == []


def test_none_values_and_other_iterables():
    assert run_lengths([None, None, 3, None]) == [(None, 2), (3, 1), (None, 1)]
    assert run_lengths("aabccc") == [("a", 2), ("b", 1), ("c", 3)]
    assert run_lengths(v for v in [0, 0, 1]) == [(0, 2), (1, 1)]


def test_longest_run_at_the_end_and_alone():
    assert longest_run([1, 2, 2, 2]) == 3
    assert longest_run([7]) == 1
    assert longest_run([4, 4, 4, 4]) == 4


def test_longest_run_elsewhere():
    assert longest_run([1, 1, 1, 2, 2]) == 3
    assert longest_run([1, 2, 2, 2, 3]) == 3
    assert longest_run([1, 2, 3]) == 1


def test_longest_run_of_nothing_is_zero_int():
    assert longest_run([]) == 0
    assert type(longest_run([])) is int
    assert longest_run(iter([])) == 0


def test_longest_run_ties_and_generators():
    assert longest_run([1, 1, 2, 2]) == 2
    assert longest_run(c for c in "abbbbc") == 4


def test_is_constant():
    assert is_constant([]) is True
    assert is_constant([3]) is True
    assert is_constant([3, 3, 3]) is True
    assert is_constant([1, 2]) is False
    assert is_constant([1, 1, 2]) is False
    assert is_constant([2, 1, 1]) is False


def test_blocks_of_none_count_like_any_other_block():
    assert longest_run([None, None, None, 1]) == 3
    assert longest_run([None]) == 1
    assert is_constant([None, None]) is True
    assert is_constant([None, 0]) is False


def test_only_consecutive_values_form_a_block():
    assert run_lengths([1, 1, 2, 1]) == [(1, 2), (2, 1), (1, 1)]
    assert longest_run([1, 1, 2, 1, 1, 1]) == 3
    assert longest_run([1, 2, 1, 2, 1]) == 1


def test_blocks_are_compared_with_equality_not_identity():
    values = [float("1.5"), float("1.5"), [1], [1]]
    assert run_lengths(values) == [(1.5, 2), ([1], 2)]
    assert longest_run([float("1000.5"), float("1000.5"), 3]) == 2
