Write `solution.py` with a function
`join_employees(employees_path: str, departments_path: str) -> list[dict]`.

Two CSV files are involved. The sample files are in the working directory:

- `employees.csv` with the header `emp_id,name,dept_id`
- `departments.csv` with the header `dept_id,dept_name` (each `dept_id` appears once)

Do a left join of employees onto departments by `dept_id` and return one dict per employee
with exactly these keys:

- `"emp_id"`: the employee id as an `int`
- `"name"`: the name string as it appears in the file
- `"dept_name"`: the matching department name, or `None` when the employee's `dept_id` is
  empty or has no matching department

The list is sorted by `emp_id` ascending (numeric order, so 2 comes before 10). Every
employee appears exactly once. An employees file with only the header row gives `[]`.
Read the files from the two path arguments, not from hard-coded names.
