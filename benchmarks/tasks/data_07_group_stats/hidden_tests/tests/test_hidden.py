from solution import group_stats

EXPECTED = {'blue': {'count': 6, 'missing': 0, 'mean': 75.83},
 'green': {'count': 4, 'missing': 0, 'mean': 77.0},
 'red': {'count': 10, 'missing': 3, 'mean': 63.1},
 'silver': {'count': 0, 'missing': 2, 'mean': None},
 'unknown': {'count': 5, 'missing': 2, 'mean': 72.4}}


def write(tmp_path, body):
    p = tmp_path / "s.csv"
    p.write_text("team,score\n" + body)
    return str(p)


def test_fixture():
    result = group_stats("scores.csv")
    assert list(result) == sorted(EXPECTED)
    assert result == EXPECTED


def test_missing_not_zero_and_rounding(tmp_path):
    path = write(tmp_path, "a,1\na,\na,2\na,2\nb,10.5\n")
    assert group_stats(path) == {
        "a": {"count": 3, "missing": 1, "mean": 1.67},
        "b": {"count": 1, "missing": 0, "mean": 10.5},
    }


def test_all_missing_team_has_none_mean(tmp_path):
    path = write(tmp_path, "x,\nx,  \ny,3\n")
    assert group_stats(path) == {
        "x": {"count": 0, "missing": 2, "mean": None},
        "y": {"count": 1, "missing": 0, "mean": 3.0},
    }


def test_blank_team_is_unknown_and_names_stripped(tmp_path):
    path = write(tmp_path, ",4\n  ,6\n red ,1\nred,3\nzeta,2\n")
    result = group_stats(path)
    assert list(result) == ["red", "unknown", "zeta"]
    assert result["unknown"] == {"count": 2, "missing": 0, "mean": 5.0}
    assert result["red"] == {"count": 2, "missing": 0, "mean": 2.0}


def test_header_only(tmp_path):
    assert group_stats(write(tmp_path, "")) == {}
