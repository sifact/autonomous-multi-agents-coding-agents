from solution import find_outliers

EXPECTED = {'A': [45.0], 'C': [-9.0]}


def write(tmp_path, rows):
    p = tmp_path / "r.csv"
    p.write_text("sensor,value\n" + "".join(f"{s},{v}\n" for s, v in rows))
    return str(p)


def test_fixture():
    result = find_outliers("readings.csv")
    assert list(result) == list(EXPECTED)
    assert result == EXPECTED


def test_value_on_the_bound_is_not_an_outlier(tmp_path):
    # n=6: Q1=2.25, Q3=4.75, IQR=2.5, upper bound exactly 8.5
    on_bound = write(tmp_path, [("s", v) for v in (1, 2, 3, 4, 5, 8.5)])
    assert find_outliers(on_bound) == {}
    above = write(tmp_path, [("s", v) for v in (1, 2, 3, 4, 5, 8.6)])
    assert find_outliers(above) == {"s": [8.6]}


def test_low_outliers_and_file_order(tmp_path):
    rows = [("s", v) for v in (10, -50, 10, 11, 10, 90, 11, 10, -50)]
    assert find_outliers(write(tmp_path, rows)) == {"s": [-50.0, 90.0, -50.0]}


def test_interleaved_sensors_first_row_order(tmp_path):
    rows = []
    for v in (1, 2, 3, 4, 5, 6, 100):
        rows.append(("late", v))
        rows.append(("zeta", v))
    rows.insert(0, ("quiet", 1))
    assert find_outliers(write(tmp_path, rows)) == {"late": [100.0], "zeta": [100.0]}
    assert list(find_outliers(write(tmp_path, rows))) == ["late", "zeta"]


def test_reverse_alphabetical_first_row_order(tmp_path):
    rows = [("zeta", v) for v in (1, 2, 3, 4, 5, 6, 100)]
    rows += [("alpha", v) for v in (1, 2, 3, 4, 5, 6, 100)]
    result = find_outliers(write(tmp_path, rows))
    assert list(result) == ["zeta", "alpha"]


def test_small_groups_and_bad_values_ignored(tmp_path):
    rows = [("a", 1), ("a", 2), ("a", 1000), ("c", "x"), ("c", "")]
    rows += [("b", "x"), ("b", ""), ("b", "nan")]
    rows += [("b", v) for v in (1, 2, 3, 4, 50)] + [("b", "inf")]
    assert find_outliers(write(tmp_path, rows)) == {"b": [50.0]}


def test_values_are_floats_not_rounded(tmp_path):
    rows = [("s", v) for v in (1, 1, 1, 1, 1, 7.123456)]
    result = find_outliers(write(tmp_path, rows))
    assert result == {"s": [7.123456]} and isinstance(result["s"][0], float)
