from leaderboard import format_board, rank, top_names


def test_tied_players_are_ordered_by_name():
    assert rank([("bo", 10), ("al", 10), ("cy", 12)]) == [("cy", 12), ("al", 10), ("bo", 10)]


def test_tie_order_does_not_depend_on_input_order():
    expected = [("al", 5), ("bo", 5), ("cy", 5)]
    assert rank([("al", 5), ("bo", 5), ("cy", 5)]) == expected
    assert rank([("cy", 5), ("bo", 5), ("al", 5)]) == expected
    assert rank([("bo", 5), ("cy", 5), ("al", 5)]) == expected


def test_names_compare_by_code_point_not_case_insensitively():
    result = rank([("al", 3), ("Zed", 3), ("Bea", 3), ("bea", 3)])
    assert result == [("Bea", 3), ("Zed", 3), ("al", 3), ("bea", 3)]


def test_more_points_first_including_negative_points():
    scores = [("a", -5), ("b", 7), ("c", 0), ("d", 100), ("e", -20)]
    assert rank(scores) == [("d", 100), ("b", 7), ("c", 0), ("a", -5), ("e", -20)]


def test_ties_mixed_with_other_scores():
    scores = [("m", 1), ("b", 4), ("a", 4), ("z", 9), ("c", 1), ("x", 4)]
    assert rank(scores) == [("z", 9), ("a", 4), ("b", 4), ("x", 4), ("c", 1), ("m", 1)]


def test_input_is_not_modified_and_result_is_a_new_list():
    scores = [("bo", 1), ("al", 2)]
    result = rank(scores)
    assert scores == [("bo", 1), ("al", 2)]
    assert result is not scores
    assert rank([]) == []
    assert rank([("a", 1), ("a", 1)]) == [("a", 1), ("a", 1)]


def test_top_names_respects_tie_order_at_the_cut():
    scores = [("dan", 8), ("bob", 8), ("amy", 8), ("eve", 9)]
    assert top_names(scores, 2) == ["eve", "amy"]
    assert top_names(scores, 3) == ["eve", "amy", "bob"]
    assert top_names(scores, 10) == ["eve", "amy", "bob", "dan"]
    assert top_names(scores, 0) == []
    assert top_names([], 3) == []


def test_format_board():
    scores = [("bo", 10), ("al", 10), ("cy", 12), ("di", -3)]
    assert format_board(scores) == "1. cy - 12\n2. al - 10\n3. bo - 10\n4. di - -3"
    assert format_board([("solo", 1)]) == "1. solo - 1"
    assert format_board([]) == ""
