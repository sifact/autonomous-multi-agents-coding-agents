from solution import total


def test_total_on_fixture():
    assert abs(total("data.csv") - 1600.0) < 1e-9


def test_total_on_other_file(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("amount,note\n1,a\n2.5,b\n")
    assert abs(total(str(p)) - 3.5) < 1e-9
