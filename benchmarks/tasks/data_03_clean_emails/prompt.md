Write `solution.py` with a function `clean_emails(path: str) -> list[str]`.

`path` is a CSV file with the header `name,email`. The sample file `contacts.csv` is in the
working directory. Other columns, if any, are ignored.

Return the cleaned list of email addresses:

1. Strip surrounding whitespace from each address and convert it to lower case.
2. Keep only valid addresses. An address is valid when all of these hold: it contains no
   whitespace, it contains exactly one `@`, the part before the `@` is not empty, and the
   part after the `@` contains at least one `.` and neither starts nor ends with `.`.
   Empty addresses are invalid.
3. Remove duplicates, keeping the first occurrence of each cleaned address and preserving
   the order of first occurrence in the file.
- A file with only the header row gives `[]`.
- Read the file from the `path` argument, not from a hard-coded name.
