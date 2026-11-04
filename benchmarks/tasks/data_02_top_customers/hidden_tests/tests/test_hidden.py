from solution import top_customers

EXPECTED = [('carol', 525.7), ('bob', 395.87), ('dave', 393.66)]


def write(tmp_path, body):
    p = tmp_path / "o.csv"
    p.write_text("order_id,customer,amount\n" + body)
    return str(p)


def test_fixture_top_three():
    assert top_customers("orders.csv", 3) == EXPECTED


def test_n_larger_than_customers_returns_all(tmp_path):
    path = write(tmp_path, "1,b,5.00\n2,a,7.50\n3,b,1.00\n")
    assert top_customers(path, 10) == [("a", 7.5), ("b", 6.0)]


def test_tie_break_by_name_on_rounded_total(tmp_path):
    path = write(tmp_path, "1,bob,10.004\n2,Zed,10.001\n3,alice,10.00\n4,top,99\n")
    assert top_customers(path, 4) == [("top", 99.0), ("Zed", 10.0), ("alice", 10.0), ("bob", 10.0)]


def test_missing_amounts_and_zero_n(tmp_path):
    path = write(tmp_path, "1,a,\n2,b,2.50\n3,a,1.25\n")
    assert top_customers(path, 1) == [("b", 2.5)]
    assert top_customers(path, 0) == []


def test_empty_file(tmp_path):
    assert top_customers(write(tmp_path, ""), 5) == []
