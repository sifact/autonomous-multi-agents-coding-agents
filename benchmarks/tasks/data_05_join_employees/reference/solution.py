import csv


def join_employees(employees_path: str, departments_path: str) -> list[dict]:
    with open(departments_path, newline="") as f:
        names = {row["dept_id"].strip(): row["dept_name"] for row in csv.DictReader(f)}
    with open(employees_path, newline="") as f:
        rows = [
            {
                "emp_id": int(row["emp_id"]),
                "name": row["name"],
                "dept_name": names.get(row["dept_id"].strip()),
            }
            for row in csv.DictReader(f)
        ]
    rows.sort(key=lambda r: r["emp_id"])
    return rows
