from ledger import balance, is_balanced, largest_imbalance


def test_tenths_cancel_out():
    assert is_balanced([0.1, 0.2, -0.3]) is True


def test_other_amounts_that_cancel_to_the_cent():
    assert is_balanced([19.99, 5.01, -25.0]) is True
    assert is_balanced([1.1, 2.2, -3.3]) is True
    assert is_balanced([0.07, 0.14, -0.21]) is True


def test_many_small_entries_cancel_out():
    assert is_balanced([0.01] * 100 + [-1.0]) is True
    assert is_balanced([0.1] * 3 + [-0.3]) is True


def test_one_cent_off_is_not_balanced():
    assert is_balanced([10.0, -9.99]) is False
    assert is_balanced([0.1, 0.2, -0.29]) is False
    assert is_balanced([0.01]) is False
    assert is_balanced([-0.01]) is False


def test_a_few_cents_off_is_not_balanced():
    assert is_balanced([10.0, -9.96]) is False
    assert is_balanced([100.0, -99.5]) is False
    assert is_balanced([5.0]) is False


def test_empty_and_trivial_lists():
    assert is_balanced([]) is True
    assert is_balanced([0]) is True
    assert is_balanced([0.0, 0.0]) is True
    assert is_balanced([5, -5]) is True


def test_balance_is_unchanged():
    assert balance([0.1, 0.2, -0.3]) == 0.0
    assert balance([10.25, 1.5, -0.75]) == 11.0
    assert balance([19.99, 5.01]) == 25.0
    assert balance([]) == 0


def test_largest_imbalance_is_unchanged():
    batches = {"a": [1.0, -1.0], "b": [5.0, -2.0], "c": [-3.0], "d": [3.0]}
    assert largest_imbalance(batches) == "b"
    assert largest_imbalance({"x": [0.1, 0.2, -0.3], "y": []}) is None
    assert largest_imbalance({}) is None
