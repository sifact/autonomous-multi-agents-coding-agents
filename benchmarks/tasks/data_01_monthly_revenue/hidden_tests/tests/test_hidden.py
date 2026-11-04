from solution import monthly_revenue

EXPECTED = {'2024-01': 353.49, '2024-02': 579.94, '2024-03': 362.04}


def test_fixture_values_and_order():
    result = monthly_revenue("sales.csv")
    assert list(result) == sorted(EXPECTED)
    assert result == EXPECTED


def test_header_only_is_empty(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("date,product,quantity,unit_price\n")
    assert monthly_revenue(str(p)) == {}


def test_rounds_once_after_summing(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text(
        "date,product,quantity,unit_price\n"
        "2024-05-01,a,1,3.333\n2024-05-09,b,1,3.333\n"
    )
    assert monthly_revenue(str(p)) == {"2024-05": 6.67}


def test_skips_missing_and_sorts_across_years(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text(
        "date,product,quantity,unit_price\n"
        "2024-01-15,a,2,5.00\n"
        "2023-12-31,b,1,2.50\n"
        "2024-02-01,c,,9.99\n"
        "2024-01-02,d,3,1.10\n"
        "2023-12-01,e,4,\n"
    )
    result = monthly_revenue(str(p))
    assert list(result.items()) == [("2023-12", 2.5), ("2024-01", 13.3)]
