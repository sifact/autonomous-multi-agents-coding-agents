import pytest

from solution import moving_average

EXPECTED = [{'date': '2024-04-05', 'ma': 100.62},
 {'date': '2024-04-06', 'ma': 100.41},
 {'date': '2024-04-07', 'ma': 100.3},
 {'date': '2024-04-08', 'ma': 100.39},
 {'date': '2024-04-10', 'ma': 100.1},
 {'date': '2024-04-11', 'ma': 100.36},
 {'date': '2024-04-12', 'ma': 100.57},
 {'date': '2024-04-13', 'ma': 100.71},
 {'date': '2024-04-14', 'ma': 100.41},
 {'date': '2024-04-15', 'ma': 100.27},
 {'date': '2024-04-16', 'ma': 100.31},
 {'date': '2024-04-17', 'ma': 100.04},
 {'date': '2024-04-18', 'ma': 99.88},
 {'date': '2024-04-19', 'ma': 100.06},
 {'date': '2024-04-20', 'ma': 100.37},
 {'date': '2024-04-21', 'ma': 99.96},
 {'date': '2024-04-22', 'ma': 99.87},
 {'date': '2024-04-23', 'ma': 100.14},
 {'date': '2024-04-24', 'ma': 100.01}]


def write(tmp_path, body):
    p = tmp_path / "p.csv"
    p.write_text("date,close\n" + body)
    return str(p)


def test_fixture_window_five():
    assert moving_average("prices.csv", 5) == EXPECTED


def test_basic_values(tmp_path):
    path = write(tmp_path, "d1,1\nd2,2\nd3,6\nd4,7\n")
    assert moving_average(path, 2) == [
        {"date": "d2", "ma": 1.5}, {"date": "d3", "ma": 4.0}, {"date": "d4", "ma": 6.5},
    ]


def test_window_one_returns_every_close(tmp_path):
    path = write(tmp_path, "d1,1.234\nd2,2.5\n")
    assert moving_average(path, 1) == [{"date": "d1", "ma": 1.23}, {"date": "d2", "ma": 2.5}]


def test_empty_close_rows_are_dropped_first(tmp_path):
    path = write(tmp_path, "d1,10\nd2,\nd3,20\nd4,30\n")
    assert moving_average(path, 2) == [{"date": "d3", "ma": 15.0}, {"date": "d4", "ma": 25.0}]


def test_window_larger_than_data(tmp_path):
    assert moving_average(write(tmp_path, "d1,1\nd2,2\n"), 3) == []


def test_bad_window_raises(tmp_path):
    path = write(tmp_path, "d1,1\n")
    with pytest.raises(ValueError):
        moving_average(path, 0)
    with pytest.raises(ValueError):
        moving_average(path, -2)
