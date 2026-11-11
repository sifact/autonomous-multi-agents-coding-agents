from ledger import apply_transactions
from summary import daily_closing, final_balances, overdrawn


def test_unseen_accounts_start_at_zero():
    history, balances = apply_transactions([("a", 500), ("b", -200), ("a", -100)])
    assert history == [("a", 500), ("b", -200), ("a", 400)]
    assert balances == {"a": 400, "b": -200}


def test_opening_balances_are_used_and_kept():
    opening = {"a": 100, "idle": 7}
    history, balances = apply_transactions([("a", 50), ("new", 5), ("a", -200)], opening)
    assert history == [("a", 150), ("new", 5), ("a", -50)]
    assert balances == {"a": -50, "idle": 7, "new": 5}


def test_opening_is_not_modified():
    opening = {"a": 100}
    apply_transactions([("a", 50), ("b", 1)], opening)
    assert opening == {"a": 100}


def test_returned_balances_is_a_new_dict():
    opening = {"a": 1}
    _, balances = apply_transactions([], opening)
    assert balances == {"a": 1}
    assert balances is not opening
    _, balances = apply_transactions([("a", 1)], opening)
    assert balances is not opening


def test_calls_without_opening_are_independent():
    apply_transactions([("a", 10)])
    history, balances = apply_transactions([("a", 1)])
    assert history == [("a", 1)]
    assert balances == {"a": 1}
    assert apply_transactions([]) == ([], {})


def test_everything_in_opening_still_works():
    opening = {"a": 10, "b": 20}
    history, balances = apply_transactions([("b", -5), ("a", 5), ("b", -5)], opening)
    assert history == [("b", 15), ("a", 15), ("b", 10)]
    assert balances == {"a": 15, "b": 10}


def test_known_accounts_in_the_reports():
    assert overdrawn([("a", -30)], {"a": 10, "b": 5}) == ["a"]
    assert final_balances([("b", 2)], {"a": 1, "b": 1}) == {"a": 1, "b": 3}
    assert daily_closing([[("a", 5)]], {"a": 1}) == [{"a": 6}]
    assert apply_transactions([], {"a": 1})[0] == []


def test_final_balances_and_overdrawn_with_new_accounts():
    transactions = [("x", 100), ("y", -50), ("z", 10), ("y", 20)]
    assert final_balances(transactions) == {"x": 100, "y": -30, "z": 10}
    assert overdrawn(transactions) == ["y"]
    assert overdrawn(transactions, {"w": -1, "x": -500}) == ["w", "x", "y"]
    assert overdrawn([]) == []


def test_daily_closing_gives_independent_dicts_per_day():
    opening = {"a": 100}
    days = [[("a", -30), ("b", 10)], [("b", 5), ("c", 1)], []]
    closings = daily_closing(days, opening)
    assert closings == [
        {"a": 70, "b": 10},
        {"a": 70, "b": 15, "c": 1},
        {"a": 70, "b": 15, "c": 1},
    ]
    assert closings[0] is not closings[1]
    assert closings[1] is not closings[2]
    assert opening == {"a": 100}


def test_daily_closing_without_opening_or_days():
    assert daily_closing([]) == []
    assert daily_closing([[("a", 3)], [("a", 4)]]) == [{"a": 3}, {"a": 7}]
