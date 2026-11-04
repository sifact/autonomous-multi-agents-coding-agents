from solution import join_employees

EXPECTED = [{'emp_id': 1, 'name': 'Ada', 'dept_name': 'Engineering'},
 {'emp_id': 2, 'name': 'Ben', 'dept_name': None},
 {'emp_id': 3, 'name': 'Cleo', 'dept_name': None},
 {'emp_id': 4, 'name': 'Dev', 'dept_name': None},
 {'emp_id': 5, 'name': 'Eli', 'dept_name': None},
 {'emp_id': 6, 'name': 'Fay', 'dept_name': None},
 {'emp_id': 7, 'name': 'Gil', 'dept_name': None},
 {'emp_id': 8, 'name': 'Hana', 'dept_name': None},
 {'emp_id': 9, 'name': 'Ivo', 'dept_name': 'Support'},
 {'emp_id': 10, 'name': 'Jun', 'dept_name': 'Engineering'}]


def test_fixture():
    assert join_employees("employees.csv", "departments.csv") == EXPECTED


def test_numeric_sort_and_unmatched(tmp_path):
    e = tmp_path / "e.csv"
    e.write_text("emp_id,name,dept_id\n10,Zoe,1\n2,Yan,2\n33,Xi,\n4,Wu,7\n")
    d = tmp_path / "d.csv"
    d.write_text("dept_id,dept_name\n1,Ops\n2,R&D\n")
    assert join_employees(str(e), str(d)) == [
        {"emp_id": 2, "name": "Yan", "dept_name": "R&D"},
        {"emp_id": 4, "name": "Wu", "dept_name": None},
        {"emp_id": 10, "name": "Zoe", "dept_name": "Ops"},
        {"emp_id": 33, "name": "Xi", "dept_name": None},
    ]


def test_emp_id_is_int_and_keys_exact(tmp_path):
    e = tmp_path / "e.csv"
    e.write_text("emp_id,name,dept_id\n5,Al,1\n")
    d = tmp_path / "d.csv"
    d.write_text("dept_id,dept_name\n1,Ops\n")
    (row,) = join_employees(str(e), str(d))
    assert isinstance(row["emp_id"], int) and set(row) == {"emp_id", "name", "dept_name"}


def test_empty_employees(tmp_path):
    e = tmp_path / "e.csv"
    e.write_text("emp_id,name,dept_id\n")
    d = tmp_path / "d.csv"
    d.write_text("dept_id,dept_name\n1,Ops\n")
    assert join_employees(str(e), str(d)) == []


def test_unused_departments_do_not_add_rows(tmp_path):
    e = tmp_path / "e.csv"
    e.write_text("emp_id,name,dept_id\n1,A,1\n2,B,1\n")
    d = tmp_path / "d.csv"
    d.write_text("dept_id,dept_name\n1,Ops\n2,Legal\n3,HR\n")
    assert [r["name"] for r in join_employees(str(e), str(d))] == ["A", "B"]
