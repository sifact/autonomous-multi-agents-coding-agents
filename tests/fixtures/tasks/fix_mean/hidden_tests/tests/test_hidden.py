from stats import mean


def test_mean():
    assert mean([1, 2, 3]) == 2
    assert mean([5]) == 5
    assert mean([0.5, 1.5]) == 1.0
